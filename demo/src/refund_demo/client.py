"""The demo OAuth client and MCP caller.

This is the piece that makes the protocol trace visible on stage. It performs
the discovery and authorization sequence exactly as an MCP client must:

1. Call the MCP server with no token, and read the ``401`` challenge.
2. Follow ``WWW-Authenticate: resource_metadata=...`` to the server's
   Protected Resource Metadata (RFC 9728).
3. Read ``authorization_servers`` from the PRM and fetch the authorization
   server's metadata (RFC 8414).
4. Start an authorization-code flow with PKCE S256 (RFC 7636) **and** an
   RFC 8707 ``resource`` indicator naming the MCP server it intends to call.
5. Redeem the code, repeating the ``resource`` indicator.
6. Call the MCP server with the resulting audience-bound access token.

Every step is recorded in a :class:`ProtocolTrace` so the run can be narrated
and replayed rather than described.

The redirect is captured directly from the ``Location`` header instead of
opening a browser. That is a stage-reliability choice, not a shortcut: PKCE,
the resource indicator, and code redemption are all still performed for real,
and the authorization server enforces them.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .config import Settings, get_settings

REDIRECT_URI = "http://localhost:7777/callback"


@dataclass
class TraceStep:
    step: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)

    def render(self) -> str:
        extra = f"\n      {json.dumps(self.data, indent=6)[6:]}" if self.data else ""
        return f"  [{self.step}] {self.detail}{extra}"


@dataclass
class ProtocolTrace:
    steps: list[TraceStep] = field(default_factory=list)

    def add(self, step: str, detail: str, **data: Any) -> None:
        self.steps.append(TraceStep(step=step, detail=detail, data=data))

    def render(self) -> str:
        return "\n".join(s.render() for s in self.steps)


@dataclass
class TokenResult:
    access_token: str
    scope: str
    resource: str
    expires_in: int
    trace: ProtocolTrace

    def claims(self) -> dict[str, Any]:
        payload = self.access_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))


class ClientError(RuntimeError):
    pass


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode("ascii")).digest()
    ).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def unauthenticated_probe(mcp_url: str, trace: ProtocolTrace) -> str:
    """Call the MCP endpoint with no token and return the PRM URL from the challenge."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{mcp_url.rstrip('/')}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
        )

    challenge = response.headers.get("www-authenticate", "")
    trace.add(
        "1. unauthenticated call",
        f"HTTP {response.status_code} from {mcp_url}/mcp",
        www_authenticate=challenge or "(none)",
    )
    if response.status_code != 401:
        raise ClientError(
            f"expected 401 from an unauthenticated MCP call, got {response.status_code}. "
            "The server is not enforcing authentication."
        )

    prm_url = ""
    for part in challenge.split(","):
        part = part.strip()
        if part.startswith("resource_metadata="):
            prm_url = part.split("=", 1)[1].strip('"')
    if not prm_url:
        raise ClientError("401 did not advertise resource_metadata; discovery cannot proceed")
    return prm_url


async def discover(mcp_url: str, trace: ProtocolTrace) -> dict[str, Any]:
    """Full RFC 9728 -> RFC 8414 discovery chain."""
    prm_url = await unauthenticated_probe(mcp_url, trace)

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        prm_response = await client.get(prm_url)
        prm_response.raise_for_status()
        prm = prm_response.json()
        trace.add(
            "2. protected resource metadata",
            f"GET {prm_url}",
            resource=prm.get("resource"),
            authorization_servers=prm.get("authorization_servers"),
            scopes_supported=prm.get("scopes_supported"),
        )

        servers = prm.get("authorization_servers") or []
        if not servers:
            raise ClientError("PRM did not name an authorization server")
        issuer = str(servers[0]).rstrip("/")

        as_url = f"{issuer}/.well-known/oauth-authorization-server"
        as_response = await client.get(as_url)
        if as_response.status_code == 404:
            as_url = f"{issuer}/.well-known/openid-configuration"
            as_response = await client.get(as_url)
        as_response.raise_for_status()
        as_metadata = as_response.json()

    trace.add(
        "3. authorization server metadata",
        f"GET {as_url}",
        issuer=as_metadata.get("issuer"),
        authorization_endpoint=as_metadata.get("authorization_endpoint"),
        token_endpoint=as_metadata.get("token_endpoint"),
        code_challenge_methods_supported=as_metadata.get("code_challenge_methods_supported"),
    )
    return {"prm": prm, "as": as_metadata, "prm_url": prm_url}


async def acquire_token(
    *,
    mcp_url: str,
    resource: str,
    scope: str,
    employee: str,
    client_id: str | None = None,
    settings: Settings | None = None,
    trace: ProtocolTrace | None = None,
    code_challenge_method: str = "S256",
) -> TokenResult:
    """Run discovery, then a real PKCE authorization-code flow for ``resource``."""
    settings = settings or get_settings()
    trace = trace or ProtocolTrace()
    client_id = client_id or settings.demo_client_id

    metadata = await discover(mcp_url, trace)
    as_metadata = metadata["as"]

    verifier, challenge = pkce_pair()
    if code_challenge_method == "plain":
        challenge = verifier

    state = secrets.token_urlsafe(16)
    authorize_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": code_challenge_method,
        "resource": resource,
        "employee": employee,
    }
    authorize_url = f"{as_metadata['authorization_endpoint']}?{urlencode(authorize_params)}"

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        auth_response = await client.get(authorize_url)

        if auth_response.status_code >= 400:
            body = auth_response.json()
            trace.add(
                "4. authorization request REJECTED",
                f"HTTP {auth_response.status_code}",
                error=body.get("error"),
                error_description=body.get("error_description"),
            )
            raise ClientError(f"{body.get('error')}: {body.get('error_description')}")

        location = auth_response.headers.get("location", "")
        returned = parse_qs(urlparse(location).query)
        code = returned.get("code", [""])[0]
        trace.add(
            "4. authorization request",
            "PKCE S256 + RFC 8707 resource indicator",
            resource_requested=resource,
            scope_requested=scope,
            code_challenge_method=code_challenge_method,
            state_echoed=returned.get("state", [""])[0] == state,
            issuer_echoed=returned.get("iss", [""])[0],
        )
        if not code:
            raise ClientError(f"authorization server did not return a code: {location}")

        token_response = await client.post(
            as_metadata["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": client_id,
                "code_verifier": verifier,
                "resource": resource,
            },
        )

    if token_response.status_code != 200:
        body = token_response.json()
        trace.add(
            "5. token request REJECTED",
            f"HTTP {token_response.status_code}",
            error=body.get("error"),
            error_description=body.get("error_description"),
        )
        raise ClientError(f"{body.get('error')}: {body.get('error_description')}")

    payload = token_response.json()
    result = TokenResult(
        access_token=payload["access_token"],
        scope=payload.get("scope", scope),
        resource=payload.get("resource", resource),
        expires_in=int(payload.get("expires_in", 0)),
        trace=trace,
    )
    claims = result.claims()
    trace.add(
        "5. token issued",
        "access token is bound to one audience",
        aud=claims.get("aud"),
        sub=claims.get("sub"),
        scp=claims.get("scp"),
        azp=claims.get("azp"),
        idtyp=claims.get("idtyp"),
        expires_in=result.expires_in,
    )
    return result


async def call_tool(
    *,
    mcp_url: str,
    access_token: str,
    tool: str,
    arguments: dict[str, Any] | None = None,
    trace: ProtocolTrace | None = None,
) -> dict[str, Any]:
    """Call one MCP tool over streamable HTTP with a bearer token."""
    from mcp import ClientSession
    from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

    endpoint = f"{mcp_url.rstrip('/')}/mcp"
    http_client = create_mcp_http_client(headers={"Authorization": f"Bearer {access_token}"})
    async with http_client:
        async with streamable_http_client(endpoint, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool, arguments or {})

    text = "\n".join(
        block.text for block in getattr(result, "content", []) if getattr(block, "type", "") == "text"
    )
    payload: dict[str, Any] = {
        "is_error": bool(getattr(result, "is_error", False)),
        "text": text,
        "structured": getattr(result, "structured_content", None),
    }
    if trace is not None:
        trace.add(
            "6. tools/call",
            f"{tool} -> {'ERROR' if payload['is_error'] else 'ok'}",
            **({"error": text} if payload["is_error"] else {}),
        )
    return payload


async def list_tools(*, mcp_url: str, access_token: str) -> list[dict[str, Any]]:
    from mcp import ClientSession
    from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

    endpoint = f"{mcp_url.rstrip('/')}/mcp"
    http_client = create_mcp_http_client(headers={"Authorization": f"Bearer {access_token}"})
    async with http_client:
        async with streamable_http_client(endpoint, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()

    return [
        {
            "name": t.name,
            "title": t.title,
            "annotations": t.annotations.model_dump(exclude_none=True) if t.annotations else {},
        }
        for t in listed.tools
    ]
