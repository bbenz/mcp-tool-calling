"""Delegated identity to the upstream refund API.

The MCP server holds a token whose audience is the MCP server itself. That
token is useless at the refund API, and forwarding it would be a token
passthrough vulnerability. Instead the server performs an on-behalf-of
exchange: it presents its own confidential-client credential plus the user's
token, and receives a *new* token whose audience is the refund API and whose
subject is still the human user.

Two hard rules are enforced here:

1. The incoming token is never forwarded to the upstream API.
2. There is no application-only fallback. If the delegated exchange fails, the
   refund fails. Substituting broad app authority would silently turn "this
   user may refund this order" into "this service may refund anything".
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from .config import Settings, get_settings
from .devidp.server import JWT_BEARER_GRANT


class DelegationError(Exception):
    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


@dataclass(frozen=True)
class DelegatedToken:
    access_token: str
    audience: str
    expires_in: int
    scope: str


async def exchange_for_upstream(incoming_token: str, settings: Settings | None = None) -> DelegatedToken:
    s = settings or get_settings()
    if s.auth_mode == "entra":
        return _exchange_entra(incoming_token, s)
    return await _exchange_devidp(incoming_token, s)


async def _exchange_devidp(incoming_token: str, s: Settings) -> DelegatedToken:
    data = {
        "grant_type": JWT_BEARER_GRANT,
        "assertion": incoming_token,
        "client_id": s.mcp_a_client_id or "refund-mcp-server",
        "client_secret": s.mcp_a_client_secret or "devidp-local-secret",
        "resource": s.upstream_api_audience,
        "scope": "Ledger.Refund",
        "requested_token_use": "on_behalf_of",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(f"{s.issuer}/token", data=data)
        except httpx.HTTPError as exc:
            raise DelegationError("DELEGATION_TRANSPORT_ERROR", f"token endpoint unreachable: {exc}") from exc

    if response.status_code != 200:
        detail = response.json().get("error_description", response.text) if response.content else response.text
        raise DelegationError("DELEGATION_REJECTED", f"on-behalf-of exchange refused: {detail}")

    payload = response.json()
    return DelegatedToken(
        access_token=payload["access_token"],
        audience=s.upstream_api_audience,
        expires_in=int(payload.get("expires_in", 0)),
        scope=str(payload.get("scope", "")),
    )


def _exchange_entra(incoming_token: str, s: Settings) -> DelegatedToken:
    try:
        import msal
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise DelegationError("DELEGATION_LIBRARY_MISSING", "msal is required for Entra on-behalf-of") from exc

    if not s.mcp_a_client_id or not s.mcp_a_client_secret:
        raise DelegationError(
            "DELEGATION_NO_CLIENT_CREDENTIAL",
            "on-behalf-of requires a confidential client credential for the MCP server",
        )

    app = msal.ConfidentialClientApplication(
        client_id=s.mcp_a_client_id,
        client_credential=s.mcp_a_client_secret,
        authority=f"https://login.microsoftonline.com/{s.entra_tenant_id}",
    )
    result = app.acquire_token_on_behalf_of(
        user_assertion=incoming_token,
        scopes=[s.upstream_api_scope],
    )
    if "access_token" not in result:
        raise DelegationError(
            "DELEGATION_REJECTED",
            f"on-behalf-of exchange refused: {result.get('error')}: {result.get('error_description')}",
        )
    return DelegatedToken(
        access_token=result["access_token"],
        audience=s.upstream_api_audience,
        expires_in=int(result.get("expires_in", 0)),
        scope=str(result.get("scope", "")),
    )
