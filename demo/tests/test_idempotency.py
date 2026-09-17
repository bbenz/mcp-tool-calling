"""Money moves exactly once.

An agent retries. A model loops. A user double-clicks. These tests pin the
ledger's behaviour under all three, and under concurrency.
"""

from __future__ import annotations

import threading
import uuid

import pytest

from refund_demo import ledger


@pytest.fixture(autouse=True)
def clean_ledger():
    ledger.initialize(reset=True)
    yield
    ledger.initialize(reset=True)


def apply(order_id="ORD-1001", amount=1_000, key=None, subject="sub-sam-0002"):
    return ledger.apply_refund(
        order_id=order_id, amount_minor=amount, currency="CAD",
        idempotency_key=key or f"k-{uuid.uuid4().hex[:8]}",
        actor_subject=subject, actor_upn="sam.agent@contoso-demo.example",
        client_id="copilot-demo-client", trace_id="t-1",
    )


def test_a_refund_reduces_the_remaining_balance():
    before = ledger.get_order("ORD-1001").refundable_balance_minor
    apply(amount=3_000)
    assert ledger.get_order("ORD-1001").refundable_balance_minor == before - 3_000


def test_same_idempotency_key_applies_once():
    key = "retry-key"
    first = apply(amount=2_000, key=key)
    second = apply(amount=2_000, key=key)
    assert first.refund_id == second.refund_id
    assert first.replayed is False
    assert second.replayed is True
    assert ledger.ledger_fingerprint()["total_refunded_minor"] == 2_000


def test_replay_with_a_different_amount_is_rejected():
    key = "mismatch-key"
    apply(amount=2_000, key=key)
    with pytest.raises(ledger.LedgerError) as exc:
        apply(amount=9_999, key=key)
    assert "IDEMPOTENCY" in exc.value.reason_code
    assert ledger.ledger_fingerprint()["total_refunded_minor"] == 2_000


def test_cannot_refund_more_than_the_remaining_balance():
    apply(amount=11_000)
    with pytest.raises(ledger.LedgerError) as exc:
        apply(amount=2_000)
    assert exc.value.reason_code == "AMOUNT_EXCEEDS_BALANCE"
    assert ledger.ledger_fingerprint()["total_refunded_minor"] == 11_000


def test_ineligible_order_is_refused_at_the_ledger_too():
    with pytest.raises(ledger.LedgerError) as exc:
        apply(order_id="ORD-1004", amount=100)
    assert exc.value.reason_code == "ORDER_NOT_REFUNDABLE"


def test_concurrent_identical_retries_apply_exactly_once():
    """Two threads, one idempotency key: the second must observe a replay."""
    key = "race-key"
    results: list[object] = []
    errors: list[Exception] = []

    def worker():
        try:
            results.append(apply(amount=1_500, key=key))
        except Exception as exc:  # noqa: BLE001 - recorded and asserted below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len({r.refund_id for r in results}) == 1
    assert sum(1 for r in results if not r.replayed) == 1
    assert ledger.ledger_fingerprint()["total_refunded_minor"] == 1_500


def test_concurrent_distinct_refunds_cannot_overdraw():
    """Eight racing refunds against a 12,000 balance must not exceed it."""
    errors: list[Exception] = []
    applied: list[object] = []

    def worker(n: int):
        try:
            applied.append(apply(amount=2_000, key=f"race-{n}"))
        except ledger.LedgerError as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total = ledger.ledger_fingerprint()["total_refunded_minor"]
    assert total <= 12_000
    assert total == 2_000 * len(applied)
    assert all(e.reason_code == "AMOUNT_EXCEEDS_BALANCE" for e in errors)


def test_fingerprint_changes_only_when_state_changes():
    before = ledger.ledger_fingerprint()["digest"]
    assert ledger.ledger_fingerprint()["digest"] == before
    apply(amount=1_000)
    assert ledger.ledger_fingerprint()["digest"] != before


def test_the_stage_scenario_does_not_mint_a_fresh_idempotency_key():
    """The regression guard for a double-click issuing a second refund.

    The ledger was never the problem -- it has always applied one key once. The
    gap was above it: `allowed-refund` used to mint a uuid per run, so every
    click was a genuinely *new* request, three of them spent ORD-1001's 12,000
    down to nothing, and the fourth failed on balance. Asserted over the parsed
    call graph rather than the raw text so the explanatory comments, which say
    "uuid" in prose, cannot satisfy it.
    """
    import ast
    import inspect
    import textwrap

    from refund_demo import scenarios

    tree = ast.parse(textwrap.dedent(inspect.getsource(scenarios.scenario_allowed_refund)))
    called = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert not [c for c in called if "uuid" in c], (
        "allowed-refund must reuse a stable idempotency key: a fresh one turns every "
        "run into a new refund and lets a few clicks drain the order"
    )
    assert scenarios.STAGE_REFUND_KEY


async def test_running_the_stage_scenario_twice_applies_exactly_one_refund(services):
    """What the user sees when they click Run twice, end to end."""
    from refund_demo.scenarios import scenario_allowed_refund

    first = await scenario_allowed_refund()
    assert first.passed, first.detail
    assert first.evidence["refund_applied_by_this_run"] is True
    assert first.ledger_changed

    second = await scenario_allowed_refund()
    assert second.passed, second.detail
    assert second.evidence["refund_applied_by_this_run"] is False
    assert not second.ledger_changed
    assert second.ledger_before["digest"] == second.ledger_after["digest"]

    assert len(ledger.list_refunds("ORD-1001")) == 1
    assert ledger.ledger_fingerprint()["total_refunded_minor"] == 4_000


async def test_the_stage_scenario_survives_being_run_until_the_order_would_be_empty(services):
    """Four runs used to exhaust a 12,000 order and fail the fifth on balance."""
    from refund_demo.scenarios import scenario_allowed_refund

    for _ in range(5):
        result = await scenario_allowed_refund()
        assert result.passed, result.detail

    assert len(ledger.list_refunds("ORD-1001")) == 1
    assert ledger.get_order("ORD-1001").refundable_balance_minor == 8_000
