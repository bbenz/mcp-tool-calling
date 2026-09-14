"""The policy engine decides; these tests pin its decisions.

Policy is tested directly, with no network and no server, because the rules are
the part of the demo an audience is asked to trust. Each test names the control
it protects.
"""

from __future__ import annotations

import pytest

from refund_demo.config import get_settings
from refund_demo.policy import (
    TOOL_ASSESS_REFUND,
    TOOL_GET_ORDER,
    TOOL_REFUND_ORDER,
    OrderFacts,
    evaluate,
)
from refund_demo.tokens import Principal

SETTINGS = get_settings()


def principal(**overrides) -> Principal:
    base = dict(
        subject="sub-sam-0002",
        object_id="sub-sam-0002",
        upn="sam.agent@contoso-demo.example",
        tenant_id="devidp-tenant",
        client_id="copilot-demo-client",
        scopes=("Refunds.Read", "Refunds.Write"),
        audience=SETTINGS.mcp_a_audience,
        issuer=SETTINGS.issuer,
        expires_at=2 **31,
    )
    base.update(overrides)
    return Principal(**base)


def order(**overrides) -> OrderFacts:
    base = dict(
        order_id="ORD-1001",
        assigned_to="sam.agent",
        currency="CAD",
        refundable=True,
        restricted=False,
        refundable_balance_minor=12_000,
    )
    base.update(overrides)
    return OrderFacts(**base)


def refund_args(**overrides):
    base = {"order_id": "ORD-1001", "amount_minor": 1_000, "currency": "CAD",
            "idempotency_key": "k-1"}
    base.update(overrides)
    return base


def test_happy_path_is_allowed():
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER,
                        arguments=refund_args(), order=order(), settings=SETTINGS)
    assert decision.allowed
    assert decision.rule_id == "R299"


def test_unknown_client_is_denied_before_anything_else():
    decision = evaluate(principal=principal(client_id="unapproved-demo-client"),
                        tool_name=TOOL_REFUND_ORDER, arguments=refund_args(),
                        order=order(), settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_CLIENT_NOT_ALLOWED"


def test_unknown_tool_is_denied():
    decision = evaluate(principal=principal(), tool_name="delete_everything",
                        arguments={}, order=None, settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_UNKNOWN_TOOL"


def test_write_tool_requires_write_scope():
    decision = evaluate(principal=principal(scopes=("Refunds.Read",)),
                        tool_name=TOOL_REFUND_ORDER, arguments=refund_args(),
                        order=order(), settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_MISSING_SCOPE"
    assert decision.rule_id == "R003"


def test_read_tools_require_read_scope():
    for tool in (TOOL_GET_ORDER, TOOL_ASSESS_REFUND):
        decision = evaluate(principal=principal(scopes=("Refunds.Write",)),
                            tool_name=tool, arguments={"order_id": "ORD-1001"},
                            order=order(), settings=SETTINGS)
        assert not decision.allowed, tool
        assert decision.reason_code == "POLICY_MISSING_SCOPE"


def test_unknown_principal_is_denied():
    decision = evaluate(principal=principal(subject="sub-nobody"), tool_name=TOOL_GET_ORDER,
                        arguments={"order_id": "ORD-1001"}, order=order(), settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_UNKNOWN_PRINCIPAL"


def test_missing_order_is_denied():
    decision = evaluate(principal=principal(), tool_name=TOOL_GET_ORDER,
                        arguments={"order_id": "ORD-9999"}, order=None, settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_ORDER_NOT_FOUND"


def test_cross_owner_access_is_denied_even_with_full_scopes():
    """The confused-deputy boundary: scope is not object-level permission."""
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER,
                        arguments=refund_args(order_id="ORD-1003"),
                        order=order(order_id="ORD-1003", assigned_to="riley.lead", restricted=True),
                        settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_ORDER_NOT_ASSIGNED"
    assert decision.rule_id == "R006"


def test_cross_owner_read_is_also_denied():
    decision = evaluate(principal=principal(), tool_name=TOOL_GET_ORDER,
                        arguments={"order_id": "ORD-1003"},
                        order=order(order_id="ORD-1003", assigned_to="riley.lead"),
                        settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_ORDER_NOT_ASSIGNED"


def test_ineligible_order_is_denied():
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER,
                        arguments=refund_args(order_id="ORD-1004"),
                        order=order(order_id="ORD-1004", refundable=False), settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_ORDER_NOT_REFUNDABLE"


@pytest.mark.parametrize("amount", [0, -1, "1000", None, 10.5])
def test_non_positive_or_non_integer_amounts_are_denied(amount):
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER,
                        arguments=refund_args(amount_minor=amount), order=order(),
                        settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_AMOUNT_INVALID"


def test_currency_mismatch_is_denied():
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER,
                        arguments=refund_args(currency="USD"), order=order(), settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_CURRENCY_MISMATCH"


def test_per_call_limit_is_enforced():
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER,
                        arguments=refund_args(amount_minor=SETTINGS.refund_per_call_limit_minor + 1),
                        order=order(refundable_balance_minor=10 ** 9), settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_AMOUNT_EXCEEDS_PER_CALL_LIMIT"


def test_refund_cannot_exceed_remaining_balance():
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER,
                        arguments=refund_args(amount_minor=5_000),
                        order=order(refundable_balance_minor=4_999), settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_AMOUNT_EXCEEDS_BALANCE"


def test_every_decision_carries_a_rule_id_and_policy_version():
    cases = [
        (principal(client_id="nope"), TOOL_REFUND_ORDER, refund_args(), order()),
        (principal(scopes=("Refunds.Read",)), TOOL_REFUND_ORDER, refund_args(), order()),
        (principal(), TOOL_REFUND_ORDER, refund_args(), order()),
    ]
    for p, tool, args, facts in cases:
        decision = evaluate(principal=p, tool_name=tool, arguments=args,
                            order=facts, settings=SETTINGS)
        assert decision.rule_id
        assert decision.reason_code
        assert decision.policy_version == SETTINGS.policy_version


def test_identity_in_arguments_is_ignored():
    """Arguments are attacker-controlled; only validated claims decide."""
    hostile = refund_args(order_id="ORD-1003")
    hostile.update({
        "assigned_to": "sam.agent",
        "sub": "sub-sam-0002",
        "scopes": ["Refunds.Write"],
        "authorized": True,
        "policy_override": "allow",
    })
    decision = evaluate(principal=principal(), tool_name=TOOL_REFUND_ORDER, arguments=hostile,
                        order=order(order_id="ORD-1003", assigned_to="riley.lead"),
                        settings=SETTINGS)
    assert not decision.allowed
    assert decision.reason_code == "POLICY_ORDER_NOT_ASSIGNED"
