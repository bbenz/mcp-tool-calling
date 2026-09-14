"""Resource B: a second protected MCP resource with a different audience.

Its only job is to prove that audience binding is real. It trusts the *same
issuer* as Resource A, so the signature verifies and the issuer check passes.
What differs is the audience it accepts. A token minted for Resource A is
therefore rejected here, before any tool runs.

A different hostname would prove nothing on its own, which is why this server
has its own token audience rather than just its own URL.
"""

from __future__ import annotations

from typing import Any

from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import get_settings
from ..mcp_server.verifier import ValidatingTokenVerifier
from ..telemetry import configure

SERVER_NAME = "inventory-probe"


def _resource_audiences() -> list[str]:
    s = get_settings()
    return [s.mcp_b_audience, s.mcp_b_public_url.rstrip("/")]


mcp = MCPServer(
    name=SERVER_NAME,
    title="Inventory probe (Resource B)",
    version="1.0.0",
    instructions="A second protected MCP resource used to demonstrate audience-bound tokens.",
    token_verifier=ValidatingTokenVerifier(_resource_audiences(), get_settings().mcp_b_audience),
    auth=AuthSettings(
        issuer_url=get_settings().issuer,  # type: ignore[arg-type]
        resource_server_url=get_settings().mcp_b_public_url,  # type: ignore[arg-type]
        required_scopes=None,
        validate_token_resource=False,
    ),
)


@mcp.tool(
    name="probe_inventory",
    title="Probe inventory",
    description="Return a trivial synthetic inventory reading. Exists only to be called with a token.",
    annotations=ToolAnnotations(
        title="Probe inventory",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def probe_inventory(sku: str = "SKU-DEMO-1") -> dict[str, Any]:
    return {
        "sku": sku,
        "on_hand": 42,
        "resource": get_settings().mcp_b_audience,
        "note": "reaching this output means the token's audience matched Resource B",
    }


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    settings = get_settings()
    return JSONResponse(
        {
            "status": "ok",
            "service": SERVER_NAME,
            "issuer": settings.issuer,
            "resource": settings.mcp_b_public_url,
            "accepted_audiences": _resource_audiences(),
        }
    )


def build_app():
    configure("resource-b")
    return mcp.streamable_http_app()


app = build_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.bind("0.0.0.0"), port=settings.mcp_b_port, log_level="warning")


if __name__ == "__main__":
    main()
