"""Bridge between the MCP SDK's bearer-auth machinery and this demo's validator.

The SDK calls :meth:`verify_token` for every request that carries a bearer
token. We run the full :class:`refund_demo.tokens.TokenValidator` there, and
hand back the validated claims so the tool layer can rebuild a trusted
:class:`~refund_demo.tokens.Principal` without re-parsing anything.

Returning ``None`` makes the SDK emit the 401 challenge that points at this
server's Protected Resource Metadata.
"""

from __future__ import annotations

import logging

import anyio.to_thread
from mcp.server.auth.provider import AccessToken

from ..audit import record_rejected_token, write
from ..config import get_settings
from ..tokens import Principal, TokenValidationError, TokenValidator

logger = logging.getLogger("refund_demo.mcp.auth")


class ValidatingTokenVerifier:
    def __init__(self, audiences: list[str], resource_label: str) -> None:
        self._audiences = audiences
        self._resource_label = resource_label
        self._validator = TokenValidator.for_resource(audiences, get_settings())

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            # Validation fetches JWKS over HTTP with a blocking client, so it
            # runs on a worker thread rather than stalling the event loop.
            principal = await anyio.to_thread.run_sync(self._validator.validate, token)
        except TokenValidationError as exc:
            logger.info("rejected token at %s: %s", self._resource_label, exc.reason_code)
            write(
                record_rejected_token(
                    tool="<transport>",
                    resource_audience=self._resource_label,
                    reason_code=exc.reason_code,
                    reason=exc.message,
                )
            )
            return None

        return AccessToken(
            token=token,
            client_id=principal.client_id,
            scopes=list(principal.scopes),
            expires_at=principal.expires_at,
            resource=principal.audience,
            subject=principal.subject,
            claims=principal.raw_claims,
        )


def principal_from_access_token(access_token: AccessToken) -> Principal:
    """Rebuild the trusted principal from claims that already passed validation."""
    claims = access_token.claims or {}
    return Principal(
        subject=str(claims.get("sub", access_token.subject or "")),
        object_id=str(claims.get("oid", claims.get("sub", ""))),
        upn=str(claims.get("preferred_username") or claims.get("upn") or claims.get("email") or ""),
        tenant_id=str(claims.get("tid", "")),
        client_id=access_token.client_id,
        scopes=tuple(access_token.scopes),
        audience=access_token.resource or "",
        issuer=str(claims.get("iss", "")),
        expires_at=int(access_token.expires_at or claims.get("exp", 0)),
        token_id=str(claims.get("uti") or claims.get("jti") or ""),
        raw_claims=claims,
    )
