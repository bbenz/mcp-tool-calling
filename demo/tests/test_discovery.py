"""End-to-end discovery and authorization-request behaviour.

These tests drive the real services over HTTP. They exist so the sequence shown
on stage is verified rather than asserted verbally.
"""

from __future__ import annotations

import httpx
import pytest

from refund_demo.client import ClientError, ProtocolTrace, acquire_token, discover, list_tools
from refund_demo.config import get_settings

pytestmark = pytest.mark.anyio

SETTINGS = get_settings()


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_unauthenticated_call_returns_401_with_resource_metadata(services):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{SETTINGS.mcp_a_public_url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream",
                     "Content-Type": "application/json"},
        )
    assert response.status_code == 401
    challenge = response.headers.get("www-authenticate", "")
    assert "resource_metadata=" in challenge


async def test_protected_resource_metadata_names_the_authorization_server(services):
    trace = ProtocolTrace()
    metadata = await discover(SETTINGS.mcp_a_public_url, trace)
    prm = metadata["prm"]
    assert prm["resource"].rstrip("/") == SETTINGS.mcp_a_public_url.rstrip("/")
    assert SETTINGS.issuer in [s.rstrip("/") for s in prm["authorization_servers"]]
    assert metadata["as"]["issuer"].rstrip("/") == SETTINGS.issuer


async def test_authorization_server_advertises_s256_and_resource_indicators(services):
    trace = ProtocolTrace()
    as_metadata = (await discover(SETTINGS.mcp_a_public_url, trace))["as"]
    assert as_metadata["code_challenge_methods_supported"] == ["S256"]
    assert as_metadata.get("resource_parameter_supported") is True


async def test_full_flow_yields_a_token_bound_to_one_audience(services):
    token = await acquire_token(
        mcp_url=SETTINGS.mcp_a_public_url, resource=SETTINGS.mcp_a_audience,
        scope=f"{SETTINGS.scope_read} {SETTINGS.scope_write}", employee="sam.agent",
    )
    claims = token.claims()
    assert claims["aud"] == SETTINGS.mcp_a_audience
    assert claims["sub"] == "sub-sam-0002"
    assert claims["idtyp"] == "user"
    assert "Refunds.Write" in claims["scp"]


async def test_resource_b_issues_a_different_audience(services):
    token = await acquire_token(
        mcp_url=SETTINGS.mcp_b_public_url, resource=SETTINGS.mcp_b_audience,
        scope="Probe.Read", employee="sam.agent",
    )
    assert token.claims()["aud"] == SETTINGS.mcp_b_audience


async def test_pkce_plain_is_refused(services):
    with pytest.raises(ClientError, match="S256"):
        await acquire_token(
            mcp_url=SETTINGS.mcp_a_public_url, resource=SETTINGS.mcp_a_audience,
            scope=SETTINGS.scope_read, employee="sam.agent", code_challenge_method="plain",
        )


async def test_authorization_without_a_resource_indicator_is_refused(services):
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        response = await client.get(
            f"{SETTINGS.issuer}/authorize",
            params={"response_type": "code", "client_id": SETTINGS.demo_client_id,
                    "redirect_uri": "http://localhost:7777/callback",
                    "scope": SETTINGS.scope_read, "code_challenge": "x" * 43,
                    "code_challenge_method": "S256", "employee": "sam.agent"},
        )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_target"


async def test_authorization_code_cannot_be_redeemed_twice(services):
    """Replaying a code must fail even with the correct verifier."""
    import secrets
    from urllib.parse import parse_qs, urlparse

    from refund_demo.client import REDIRECT_URI, pkce_pair

    verifier, challenge = pkce_pair()
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        auth = await client.get(
            f"{SETTINGS.issuer}/authorize",
            params={"response_type": "code", "client_id": SETTINGS.demo_client_id,
                    "redirect_uri": REDIRECT_URI, "scope": SETTINGS.scope_read,
                    "state": secrets.token_urlsafe(8), "code_challenge": challenge,
                    "code_challenge_method": "S256", "resource": SETTINGS.mcp_a_audience,
                    "employee": "sam.agent"},
        )
        code = parse_qs(urlparse(auth.headers["location"]).query)["code"][0]
        body = {"grant_type": "authorization_code", "code": code,
                "redirect_uri": REDIRECT_URI, "client_id": SETTINGS.demo_client_id,
                "code_verifier": verifier, "resource": SETTINGS.mcp_a_audience}
        first = await client.post(f"{SETTINGS.issuer}/token", data=body)
        second = await client.post(f"{SETTINGS.issuer}/token", data=body)

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["error"] == "invalid_grant"


async def test_wrong_pkce_verifier_is_refused(services):
    import secrets
    from urllib.parse import parse_qs, urlparse

    from refund_demo.client import REDIRECT_URI, pkce_pair

    _, challenge = pkce_pair()
    other_verifier, _ = pkce_pair()
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        auth = await client.get(
            f"{SETTINGS.issuer}/authorize",
            params={"response_type": "code", "client_id": SETTINGS.demo_client_id,
                    "redirect_uri": REDIRECT_URI, "scope": SETTINGS.scope_read,
                    "state": secrets.token_urlsafe(8), "code_challenge": challenge,
                    "code_challenge_method": "S256", "resource": SETTINGS.mcp_a_audience,
                    "employee": "sam.agent"},
        )
        code = parse_qs(urlparse(auth.headers["location"]).query)["code"][0]
        response = await client.post(
            f"{SETTINGS.issuer}/token",
            data={"grant_type": "authorization_code", "code": code,
                  "redirect_uri": REDIRECT_URI, "client_id": SETTINGS.demo_client_id,
                  "code_verifier": other_verifier, "resource": SETTINGS.mcp_a_audience},
        )
    assert response.status_code == 400
    assert "PKCE" in response.json()["error_description"]


async def test_tools_are_listed_with_honest_annotations(services):
    token = await acquire_token(
        mcp_url=SETTINGS.mcp_a_public_url, resource=SETTINGS.mcp_a_audience,
        scope=SETTINGS.scope_read, employee="dana.reader",
    )
    tools = {t["name"]: t["annotations"] for t in
             await list_tools(mcp_url=SETTINGS.mcp_a_public_url, access_token=token.access_token)}

    assert set(tools) == {"get_order", "assess_refund", "refund_order"}
    assert tools["get_order"]["read_only_hint"] is True
    assert tools["refund_order"]["destructive_hint"] is True
    assert tools["refund_order"]["read_only_hint"] is False
    # A read-scoped user still sees the consequential tool. Listing is not
    # permission; the denial happens at tools/call.
