"""Delegated identity to the upstream API.

The claim under test: the user's identity reaches the upstream service, the
MCP server's own token does not, and there is no application-only fallback that
would quietly widen authority when delegation fails.
"""

from __future__ import annotations

import uuid

import httpx
import pytest

from refund_demo.client import acquire_token, call_tool
from refund_demo.config import get_settings
from refund_demo.delegation import DelegationError, exchange_for_upstream

pytestmark = pytest.mark.anyio

SETTINGS = get_settings()


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def user_token(employee="sam.agent", scope=None):
    return await acquire_token(
        mcp_url=SETTINGS.mcp_a_public_url, resource=SETTINGS.mcp_a_audience,
        scope=scope or f"{SETTINGS.scope_read} {SETTINGS.scope_write}", employee=employee,
    )


async def test_exchange_changes_the_audience_but_keeps_the_subject(services):
    incoming = await user_token()
    delegated = await exchange_for_upstream(incoming.access_token, SETTINGS)

    assert delegated.audience == SETTINGS.upstream_api_audience
    assert delegated.access_token != incoming.access_token

    import jwt
    before = jwt.decode(incoming.access_token, options={"verify_signature": False})
    after = jwt.decode(delegated.access_token, options={"verify_signature": False})
    assert after["aud"] == SETTINGS.upstream_api_audience
    assert after["sub"] == before["sub"]
    assert after["aud"] != before["aud"]
    assert "Ledger.Refund" in after["scp"]


async def test_the_exchanged_token_records_the_acting_service(services):
    import jwt

    incoming = await user_token()
    delegated = await exchange_for_upstream(incoming.access_token, SETTINGS)
    claims = jwt.decode(delegated.access_token, options={"verify_signature": False})
    assert claims.get("act", {}).get("sub")


async def test_the_incoming_token_is_rejected_by_the_upstream_api(services):
    """Token passthrough must not work."""
    incoming = await user_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{SETTINGS.upstream_api_url}/refunds",
            json={"order_id": "ORD-1001", "amount_minor": 100, "currency": "CAD"},
            headers={"Authorization": f"Bearer {incoming.access_token}",
                     "Idempotency-Key": f"pt-{uuid.uuid4().hex[:8]}"},
        )
    assert response.status_code == 401
    assert response.json()["reason_code"] == "AUTH_WRONG_AUDIENCE"


async def test_the_exchanged_token_is_accepted_by_the_upstream_api(services):
    incoming = await user_token()
    delegated = await exchange_for_upstream(incoming.access_token, SETTINGS)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{SETTINGS.upstream_api_url}/orders/ORD-1001",
            headers={"Authorization": f"Bearer {delegated.access_token}"},
        )
    assert response.status_code == 200


async def test_the_exchange_requires_a_confidential_client_credential(services):
    """A public client cannot mint a delegated token for another resource."""
    incoming = await user_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{SETTINGS.issuer}/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                  "assertion": incoming.access_token,
                  "client_id": "copilot-demo-client",
                  "resource": SETTINGS.upstream_api_audience,
                  "scope": "Ledger.Refund"},
        )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client"


async def test_a_wrong_client_secret_is_refused(services):
    incoming = await user_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{SETTINGS.issuer}/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                  "assertion": incoming.access_token,
                  "client_id": "refund-mcp-server", "client_secret": "not-the-secret",
                  "resource": SETTINGS.upstream_api_audience, "scope": "Ledger.Refund"},
        )
    assert response.status_code == 401


async def test_a_junk_assertion_is_refused(services):
    with pytest.raises(DelegationError) as exc:
        await exchange_for_upstream("not.a.token", SETTINGS)
    assert exc.value.reason_code == "DELEGATION_REJECTED"


async def test_upstream_reenforces_ownership_with_its_own_token(services):
    """Even holding a valid delegated token, the upstream re-checks the object."""
    incoming = await user_token()
    delegated = await exchange_for_upstream(incoming.access_token, SETTINGS)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{SETTINGS.upstream_api_url}/refunds",
            json={"order_id": "ORD-1003", "amount_minor": 1_000, "currency": "CAD"},
            headers={"Authorization": f"Bearer {delegated.access_token}",
                     "Idempotency-Key": f"own-{uuid.uuid4().hex[:8]}"},
        )
    assert response.status_code == 403
    assert response.json()["reason_code"] == "UPSTREAM_ORDER_NOT_ASSIGNED"


async def test_upstream_requires_its_own_scope(services):
    """A delegated token without Ledger.Refund cannot write, whatever the MCP server thinks."""
    import jwt

    incoming = await user_token()
    async with httpx.AsyncClient(timeout=10.0) as client:
        exchanged = await client.post(
            f"{SETTINGS.issuer}/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                  "assertion": incoming.access_token,
                  "client_id": "refund-mcp-server", "client_secret": "devidp-local-secret",
                  "resource": SETTINGS.upstream_api_audience, "scope": "Ledger.Read"},
        )
        token = exchanged.json()["access_token"]
        assert "Ledger.Refund" not in jwt.decode(token, options={"verify_signature": False})["scp"]

        response = await client.post(
            f"{SETTINGS.upstream_api_url}/refunds",
            json={"order_id": "ORD-1001", "amount_minor": 100, "currency": "CAD"},
            headers={"Authorization": f"Bearer {token}",
                     "Idempotency-Key": f"sc-{uuid.uuid4().hex[:8]}"},
        )
    assert response.status_code == 403
    assert response.json()["reason_code"] == "UPSTREAM_MISSING_SCOPE"


async def test_a_successful_refund_reports_the_delegated_subject(services):
    token = await user_token()
    result = await call_tool(
        mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token,
        tool="refund_order",
        arguments={"order_id": "ORD-1001", "amount_minor": 100, "currency": "CAD",
                   "idempotency_key": f"del-{uuid.uuid4().hex[:8]}"},
    )
    assert not result["is_error"], result["text"]
    import json
    body = json.loads(result["text"])
    assert body["delegated_identity_preserved"] is True
    assert body["upstream_audience"] == SETTINGS.upstream_api_audience
