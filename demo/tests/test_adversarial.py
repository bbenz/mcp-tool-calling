"""The three adversarial checks promised in the session proposal.

1. A valid token for the wrong resource (audience binding).
2. Prompt injection inside untrusted tool output (advice is not authorization).
3. Tool-annotation tampering (hints are not permissions).

Plus the confused-deputy case, which is the reason the other three matter.

Every check asserts the ledger fingerprint is unchanged. "Denied" has to mean
"nothing happened", not "we printed a red message".
"""

from __future__ import annotations

import json
import uuid

import httpx
import pytest

from refund_demo import ledger
from refund_demo.client import acquire_token, call_tool, list_tools
from refund_demo.config import get_settings

pytestmark = pytest.mark.anyio

SETTINGS = get_settings()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def fingerprint():
    return ledger.ledger_fingerprint()["digest"]


async def token_for(employee="sam.agent", scope=None, client_id=None):
    return await acquire_token(
        mcp_url=SETTINGS.mcp_a_public_url, resource=SETTINGS.mcp_a_audience,
        scope=scope or f"{SETTINGS.scope_read} {SETTINGS.scope_write}",
        employee=employee, client_id=client_id,
    )


def unchanged(before: str) -> bool:
    return ledger.ledger_fingerprint()["digest"] == before


# --------------------------------------------------------------------------
# Check 1: wrong resource
# --------------------------------------------------------------------------


async def test_token_minted_for_resource_b_is_rejected_at_resource_a(services, fingerprint):
    token = await acquire_token(
        mcp_url=SETTINGS.mcp_b_public_url, resource=SETTINGS.mcp_b_audience,
        scope="Probe.Read", employee="sam.agent",
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{SETTINGS.mcp_a_public_url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Authorization": f"Bearer {token.access_token}",
                     "Accept": "application/json, text/event-stream",
                     "Content-Type": "application/json"},
        )
    assert response.status_code == 401
    assert unchanged(fingerprint)


async def test_the_same_token_works_at_its_own_resource(services):
    """Proves the rejection above is about audience, not a broken token."""
    token = await acquire_token(
        mcp_url=SETTINGS.mcp_b_public_url, resource=SETTINGS.mcp_b_audience,
        scope="Probe.Read", employee="sam.agent",
    )
    result = await call_tool(mcp_url=SETTINGS.mcp_b_public_url,
                             access_token=token.access_token, tool="probe_inventory")
    assert not result["is_error"], result["text"]


# --------------------------------------------------------------------------
# Check 2: prompt injection
# --------------------------------------------------------------------------


async def test_injected_instructions_in_order_notes_cannot_widen_authorization(services, fingerprint):
    token = await token_for()

    read = await call_tool(mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token,
                           tool="get_order", arguments={"order_id": "ORD-1005"})
    body = json.loads(read["text"])
    assert "ignore all previous instructions" in body["notes"].lower()
    assert body["notes_are_untrusted_customer_content"] is True

    # Obey the injected instruction exactly.
    obeyed = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1003", "amount_minor": 99_000, "currency": "CAD",
                   "idempotency_key": f"inj-{uuid.uuid4().hex[:8]}"},
    )
    assert obeyed["is_error"]
    assert "POLICY_ORDER_NOT_ASSIGNED" in obeyed["text"]
    assert unchanged(fingerprint)


async def test_the_advisory_tool_marks_itself_as_non_authoritative(services, fingerprint):
    token = await token_for()
    result = await call_tool(mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token,
                             tool="assess_refund", arguments={"order_id": "ORD-1005"})
    body = json.loads(result["text"])
    assert body["advisory_only"] is True
    assert "cannot authorize" in body["authorization_effect"]
    assert body["untrusted_note_contains_instructions"] is True
    assert unchanged(fingerprint)


async def test_assessment_cannot_be_used_as_a_capability(services, fingerprint):
    """A read-scoped user may ask for advice and still cannot act on it."""
    token = await token_for(employee="dana.reader", scope=SETTINGS.scope_read)
    advice = await call_tool(mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token,
                             tool="assess_refund", arguments={"order_id": "ORD-1002"})
    assert not advice["is_error"], advice["text"]

    attempt = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1002", "amount_minor": 100, "currency": "CAD",
                   "idempotency_key": f"adv-{uuid.uuid4().hex[:8]}"},
    )
    assert attempt["is_error"]
    assert "POLICY_MISSING_SCOPE" in attempt["text"]
    assert unchanged(fingerprint)


# --------------------------------------------------------------------------
# Check 3: annotation tampering
# --------------------------------------------------------------------------


async def test_annotations_are_hints_and_never_reach_the_server(services, fingerprint):
    token = await token_for(employee="dana.reader", scope=SETTINGS.scope_read)
    listed = {t["name"]: t["annotations"] for t in
              await list_tools(mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token)}
    assert listed["refund_order"]["destructive_hint"] is True

    # The client rewrites the hints locally, then makes the identical call.
    # Nothing on the wire changes: annotations are not part of tools/call.
    result = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1002", "amount_minor": 100, "currency": "CAD",
                   "idempotency_key": f"ann-{uuid.uuid4().hex[:8]}",
                   "readOnlyHint": True, "destructiveHint": False},
    )
    assert result["is_error"]
    assert "POLICY_MISSING_SCOPE" in result["text"]
    assert unchanged(fingerprint)


async def test_extra_arguments_cannot_smuggle_permissions(services, fingerprint):
    token = await token_for()
    result = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1003", "amount_minor": 1_000, "currency": "CAD",
                   "idempotency_key": f"sm-{uuid.uuid4().hex[:8]}",
                   "assigned_to": "sam.agent", "policy_override": "allow",
                   "scopes": ["Refunds.Write"], "sub": "sub-riley-0003"},
    )
    assert result["is_error"]
    assert "POLICY_ORDER_NOT_ASSIGNED" in result["text"]
    assert unchanged(fingerprint)


# --------------------------------------------------------------------------
# Confused deputy
# --------------------------------------------------------------------------


async def test_a_fully_authorized_user_cannot_reach_another_users_order(services, fingerprint):
    token = await token_for()
    assert "Refunds.Write" in token.claims()["scp"]

    result = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1003", "amount_minor": 1_000, "currency": "CAD",
                   "idempotency_key": f"cd-{uuid.uuid4().hex[:8]}"},
    )
    assert result["is_error"]
    assert "POLICY_ORDER_NOT_ASSIGNED" in result["text"]
    assert unchanged(fingerprint)


async def test_the_owner_can_act_on_the_same_order(services):
    """Proves the denial above is about ownership, not a broken order."""
    token = await token_for(employee="riley.lead")
    result = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1003", "amount_minor": 1_000, "currency": "CAD",
                   "idempotency_key": f"ok-{uuid.uuid4().hex[:8]}"},
    )
    assert not result["is_error"], result["text"]


async def test_an_unapproved_client_application_is_refused(services, fingerprint):
    token = await token_for(client_id="unapproved-demo-client")
    result = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1001", "amount_minor": 100, "currency": "CAD",
                   "idempotency_key": f"cl-{uuid.uuid4().hex[:8]}"},
    )
    assert result["is_error"]
    assert "POLICY_CLIENT_NOT_ALLOWED" in result["text"]
    assert unchanged(fingerprint)


# --------------------------------------------------------------------------
# Audit evidence
# --------------------------------------------------------------------------


async def test_every_denial_is_audited_with_a_reason_code_and_no_raw_identifiers(services):
    from refund_demo import audit

    token = await token_for()
    await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1003", "amount_minor": 1_000, "currency": "CAD",
                   "idempotency_key": f"au-{uuid.uuid4().hex[:8]}"},
    )
    records = audit.read_all()
    latest = next(r for r in reversed(records)
                  if r.get("tool") == "refund_order" and r.get("decision") == "deny")

    assert latest["reason_code"] == "POLICY_ORDER_NOT_ASSIGNED"
    assert latest["policy_rule_id"] == "R006"
    assert latest["policy_version"] == SETTINGS.policy_version
    assert latest["ledger_changed"] is False
    assert latest["identity_state"] == "validated"
    assert latest["user_pseudonym"].startswith("user_")

    blob = json.dumps(latest)
    assert "sub-sam-0002" not in blob
    assert "sam.agent@contoso-demo.example" not in blob
    assert "idempotency_key" in latest["arguments"]["_omitted_keys"]


async def test_a_rejected_token_is_audited_without_attributing_an_identity(services):
    """Claims in an unverified token are attacker-supplied and must not be recorded as fact."""
    from refund_demo import audit

    token = await acquire_token(
        mcp_url=SETTINGS.mcp_b_public_url, resource=SETTINGS.mcp_b_audience,
        scope="Probe.Read", employee="sam.agent",
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            f"{SETTINGS.mcp_a_public_url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Authorization": f"Bearer {token.access_token}",
                     "Accept": "application/json, text/event-stream",
                     "Content-Type": "application/json"},
        )

    records = audit.read_all()
    latest = next(r for r in reversed(records) if r.get("identity_state") == "untrusted")
    assert latest["reason_code"] == "AUTH_WRONG_AUDIENCE"
    assert latest["decision"] == "deny"
    assert not latest.get("user_pseudonym")
    assert not latest.get("tenant_id")

