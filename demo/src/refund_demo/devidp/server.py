"""Local development authorization server.

A real, standards-based OAuth 2.0 authorization server that runs on localhost:

* RFC 8414 authorization-server metadata at
  ``/.well-known/oauth-authorization-server``
* RFC 7636 PKCE, **S256 only** -- ``plain`` is rejected
* RFC 8707 ``resource`` indicators, honoured in BOTH the authorization request
  and the token request, and reflected into the issued token's ``aud``
* RFC 7523 ``jwt-bearer`` grant, used to model Entra's on-behalf-of exchange
* Real RS256 signatures over a real published JWKS

Why this exists: the talk needs the complete protocol trace to be inspectable
and repeatable on stage without depending on a tenant, a browser profile, or
conference Wi-Fi. Tokens minted here are validated by exactly the same
:class:`refund_demo.tokens.TokenValidator` used for Entra, so the security
boundaries being demonstrated are real.

What this is NOT: it is not a production identity provider, it does not
authenticate anybody (the "login" page simply lets the presenter pick which
synthetic employee to act as), and it never runs in the cloud deployment.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import anyio.to_thread
import jwt
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from ..config import get_settings
from ..fixtures import CLIENTS, EMPLOYEES
from ..telemetry import configure
from .keys import ALGORITHM, load_or_create

AUTH_CODE_TTL_SECONDS = 120
ACCESS_TOKEN_TTL_SECONDS = 3600
JWT_BEARER_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"


@dataclass
class AuthorizationCode:
    code: str
    client_id: str
    redirect_uri: str
    scope: str
    resource: str
    employee_key: str
    code_challenge: str
    issued_at: float = field(default_factory=time.time)

    def expired(self) -> bool:
        return time.time() - self.issued_at > AUTH_CODE_TTL_SECONDS


_CODES: dict[str, AuthorizationCode] = {}


def _pkce_s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _error(code: str, description: str, status: int = 400) -> JSONResponse:
    return JSONResponse({"error": code, "error_description": description}, status_code=status)


def issue_access_token(
    *,
    employee_key: str,
    client_id: str,
    resource: str,
    scope: str,
    ttl_seconds: int = ACCESS_TOKEN_TTL_SECONDS,
    actor_client_id: str | None = None,
) -> tuple[str, int]:
    """Mint an RS256 access token bound to ``resource`` as its audience."""
    settings = get_settings()
    key = load_or_create()
    employee = EMPLOYEES[employee_key]
    now = int(time.time())
    expires_at = now + ttl_seconds

    claims: dict[str, Any] = {
        "iss": settings.issuer,
        "aud": resource,
        "sub": employee.subject,
        "oid": employee.subject,
        "tid": settings.entra_tenant_id or "devidp-tenant",
        "preferred_username": employee.upn,
        "name": employee.display_name,
        "scp": scope,
        "azp": client_id,
        "appid": client_id,
        "idtyp": "user",
        "ver": "2.0",
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "uti": secrets.token_urlsafe(12),
    }
    if actor_client_id:
        # RFC 8693 style actor claim: records that a delegate performed the
        # exchange, while `sub` still identifies the human user.
        claims["act"] = {"sub": actor_client_id}

    token = jwt.encode(
        claims,
        key.private_pem,
        algorithm=ALGORITHM,
        headers={"kid": key.kid, "typ": "at+jwt"},
    )
    return token, expires_at


async def metadata(request: Request) -> Response:
    settings = get_settings()
    issuer = settings.issuer
    return JSONResponse(
        {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "jwks_uri": f"{issuer}/jwks",
            "response_types_supported": ["code"],
            "response_modes_supported": ["query"],
            "grant_types_supported": ["authorization_code", JWT_BEARER_GRANT],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
            "scopes_supported": [settings.scope_read, settings.scope_write, "Ledger.Refund", "Probe.Read"],
            "authorization_response_iss_parameter_supported": True,
            "resource_parameter_supported": True,
            "service_documentation": "local demo authorization server - not for production use",
        }
    )


async def jwks(request: Request) -> Response:
    return JSONResponse(load_or_create().jwks())


async def openid_configuration(request: Request) -> Response:
    return await metadata(request)


_LOGIN_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Demo sign-in</title>
<style>
 body {{ font-family: Segoe UI, system-ui, sans-serif; max-width: 42rem; margin: 3rem auto; font-size: 18px; }}
 .warn {{ background:#fff4ce; border-left:4px solid #f2c811; padding:.75rem 1rem; }}
 li {{ margin:.75rem 0; }} code {{ background:#f3f3f3; padding:.1rem .3rem; }}
 a.btn {{ display:inline-block; padding:.5rem .9rem; background:#0b5cad; color:#fff;
          text-decoration:none; border-radius:4px; }}
</style></head><body>
<h1>Local demo authorization server</h1>
<p class="warn"><strong>Local demo only.</strong> This server does not authenticate anyone.
Pick the synthetic employee to act as. In the cloud path this screen is replaced by
Microsoft Entra ID.</p>
<p>Client <code>{client_id}</code> is requesting scope <code>{scope}</code>
for resource <code>{resource}</code>.</p>
<ul>{choices}</ul>
</body></html>
"""


async def authorize(request: Request) -> Response:
    params = request.query_params
    settings = get_settings()

    client_id = params.get("client_id", "")
    redirect_uri = params.get("redirect_uri", "")
    response_type = params.get("response_type", "")
    scope = params.get("scope", settings.scope_read)
    state = params.get("state", "")
    challenge = params.get("code_challenge", "")
    challenge_method = params.get("code_challenge_method", "")
    resource = params.get("resource", "")

    if response_type != "code":
        return _error("unsupported_response_type", "only response_type=code is supported")
    if not client_id:
        return _error("invalid_request", "client_id is required")
    if not redirect_uri:
        return _error("invalid_request", "redirect_uri is required")
    if not challenge:
        return _error("invalid_request", "PKCE code_challenge is required")
    if challenge_method != "S256":
        return _error("invalid_request", "code_challenge_method must be S256; 'plain' is not accepted")
    if not resource:
        # RFC 8707. Without it the server would not know which audience to mint,
        # which is exactly the failure the talk is about.
        return _error("invalid_target", "an RFC 8707 'resource' indicator is required")

    selected = params.get("employee")
    if not selected:
        choices = "".join(
            f'<li><a class="btn" href="?{urlencode({**dict(params), "employee": key})}">'
            f"Sign in as {emp.display_name}</a> &mdash; scopes <code>{' '.join(emp.scopes)}</code></li>"
            for key, emp in EMPLOYEES.items()
        )
        return HTMLResponse(
            _LOGIN_PAGE.format(client_id=client_id, scope=scope, resource=resource, choices=choices)
        )

    if selected not in EMPLOYEES:
        return _error("access_denied", f"unknown demo employee {selected!r}")

    code = secrets.token_urlsafe(24)
    _CODES[code] = AuthorizationCode(
        code=code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        resource=resource,
        employee_key=selected,
        code_challenge=challenge,
    )
    query = {"code": code, "iss": settings.issuer}
    if state:
        query["state"] = state
    return RedirectResponse(f"{redirect_uri}?{urlencode(query)}", status_code=302)


async def token(request: Request) -> Response:
    form = await request.form()
    grant_type = str(form.get("grant_type", ""))

    if grant_type == "authorization_code":
        return _token_authorization_code(form)
    if grant_type == JWT_BEARER_GRANT:
        return await _token_jwt_bearer(form)
    return _error("unsupported_grant_type", f"grant_type {grant_type!r} is not supported")


def _token_authorization_code(form: Any) -> Response:
    code = str(form.get("code", ""))
    verifier = str(form.get("code_verifier", ""))
    redirect_uri = str(form.get("redirect_uri", ""))
    client_id = str(form.get("client_id", ""))
    requested_resource = str(form.get("resource", ""))

    entry = _CODES.pop(code, None)
    if entry is None:
        return _error("invalid_grant", "authorization code is unknown or already redeemed")
    if entry.expired():
        return _error("invalid_grant", "authorization code has expired")
    if entry.client_id != client_id:
        return _error("invalid_grant", "authorization code was issued to a different client")
    if entry.redirect_uri != redirect_uri:
        return _error("invalid_grant", "redirect_uri does not match the authorization request")
    if not verifier:
        return _error("invalid_request", "code_verifier is required")
    if _pkce_s256(verifier) != entry.code_challenge:
        return _error("invalid_grant", "PKCE verification failed")
    if requested_resource and requested_resource != entry.resource:
        return _error("invalid_target", "resource in the token request does not match the authorization request")

    access_token, expires_at = issue_access_token(
        employee_key=entry.employee_key,
        client_id=entry.client_id,
        resource=entry.resource,
        scope=entry.scope,
    )
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_at - int(time.time()),
            "scope": entry.scope,
            "resource": entry.resource,
        }
    )


async def _token_jwt_bearer(form: Any) -> Response:
    """Model Entra's on-behalf-of exchange.

    A confidential client presents (a) its own credential and (b) the token it
    received, and asks for a *new* token for a different resource. The user's
    identity is preserved; the audience changes. The incoming token is never
    forwarded.

    The assertion is verified with the same validator every resource uses. That
    validation fetches this server's own JWKS over HTTP, so it must run on a
    worker thread: doing it inline would block the event loop on a request this
    same process has to serve, and the exchange would deadlock.
    """
    settings = get_settings()
    assertion = str(form.get("assertion", ""))
    client_id = str(form.get("client_id", ""))
    client_secret = str(form.get("client_secret", ""))
    resource = str(form.get("resource", ""))
    scope = str(form.get("scope", "Ledger.Refund"))

    if not assertion:
        return _error("invalid_request", "assertion is required")
    if not resource:
        return _error("invalid_target", "an RFC 8707 'resource' indicator is required")
    if not client_id or not client_secret:
        return _error(
            "invalid_client",
            "on-behalf-of requires a confidential client credential; a public client cannot perform this exchange",
        )
    if client_secret != (settings.mcp_a_client_secret or "devidp-local-secret"):
        return _error("invalid_client", "client authentication failed", status=401)

    from ..tokens import TokenValidator, TokenValidationError

    validator = TokenValidator.for_resource(settings.mcp_a_audience, settings)
    try:
        principal = await anyio.to_thread.run_sync(validator.validate, assertion)
    except TokenValidationError as exc:
        return _error("invalid_grant", f"assertion rejected: {exc.reason_code}")

    employee_key = next((k for k, e in EMPLOYEES.items() if e.subject == principal.subject), None)
    if employee_key is None:
        return _error("invalid_grant", "assertion subject is not a known demo employee")

    access_token, expires_at = issue_access_token(
        employee_key=employee_key,
        client_id=client_id,
        resource=resource,
        scope=scope,
        actor_client_id=client_id,
    )
    return JSONResponse(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_at - int(time.time()),
            "scope": scope,
            "resource": resource,
        }
    )


async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok", "service": "devidp", "issuer": get_settings().issuer})


def create_app() -> Starlette:
    configure("devidp")
    return Starlette(
        routes=[
            Route("/.well-known/oauth-authorization-server", metadata),
            Route("/.well-known/openid-configuration", openid_configuration),
            Route("/jwks", jwks),
            Route("/authorize", authorize),
            Route("/token", token, methods=["POST"]),
            Route("/health", health),
        ]
    )


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="127.0.0.1", port=settings.devidp_port, log_level="warning")


if __name__ == "__main__":
    main()
