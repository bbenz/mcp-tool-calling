"""The protected MCP server (Resource A).

This is where the talk's question is answered: *may this user, through this
client, refund this order with these arguments?*

Layering, outermost first:

1. **Transport authentication.** The SDK's bearer middleware rejects requests
   without a valid token and answers with a 401 whose ``WWW-Authenticate``
   header points at this server's Protected Resource Metadata.
2. **Token validation.** :mod:`refund_demo.mcp_server.verifier` runs full
   signature/issuer/audience/expiry/tenant validation. Audience binding here is
   what makes a token minted for Resource B useless at Resource A.
3. **Runtime tool policy.** Every tool re-checks authorization at
   ``tools/call`` against validated identity and authoritative order facts.
   Listing a tool is not permission to call it.
4. **Upstream enforcement.** The refund API independently validates its own
   audience-bound delegated token and re-applies its own rules.

Tool annotations are declared honestly, but they are hints for the client's
risk presentation. They are not consulted by the policy, and editing them
cannot change a decision.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .. import audit, foundry, ledger
from ..config import get_settings
from ..delegation import DelegationError, exchange_for_upstream
from ..policy import (
    TOOL_ASSESS_REFUND,
    TOOL_GET_ORDER,
    TOOL_REFUND_ORDER,
    OrderFacts,
    PolicyDecision,
    evaluate,
)
from ..telemetry import configure, span
from ..tokens import Principal
from .verifier import ValidatingTokenVerifier, principal_from_access_token

logger = logging.getLogger("refund_demo.mcp")

SERVER_NAME = "refund-assistant"


class ToolDenied(ToolError):
    """A deliberate policy denial.

    It subclasses the SDK's :class:`ToolError` so the stable reason code
    reaches the caller instead of being replaced with a generic crash message.
    The audience sees the real reason; nothing sensitive is in it.
    """

    def __init__(self, decision: PolicyDecision):
        super().__init__(f"{decision.reason_code}: {decision.reason} [rule {decision.rule_id}]")
        self.decision = decision


def _resource_audiences() -> list[str]:
    s = get_settings()
    return [s.mcp_a_audience, s.mcp_a_public_url.rstrip("/")]


def _require_principal() -> Principal:
    access_token = get_access_token()
    if access_token is None:
        raise RuntimeError("no authenticated context; bearer middleware should have rejected this request")
    return principal_from_access_token(access_token)


def _raw_token() -> str:
    access_token = get_access_token()
    return access_token.token if access_token else ""


def _order_facts(order_id: str) -> tuple[OrderFacts | None, ledger.OrderRecord | None]:
    record = ledger.get_order(order_id)
    if record is None:
        return None, None
    facts = OrderFacts(
        order_id=record.order_id,
        assigned_to=record.assigned_to,
        currency=record.currency,
        refundable=record.refundable,
        restricted=record.restricted,
        refundable_balance_minor=record.refundable_balance_minor,
    )
    return facts, record


def _authorize(
    tool_name: str,
    arguments: dict[str, Any],
    ctx: Context | None = None,
) -> tuple[Principal, ledger.OrderRecord, audit.AuditRecord]:
    """Validate, decide, audit. Raises :class:`ToolDenied` on denial."""
    settings = get_settings()
    principal = _require_principal()
    order_id = str(arguments.get("order_id", ""))
    facts, record = _order_facts(order_id)

    audit_record = audit.start_record(
        tool=tool_name,
        resource_audience=principal.audience or settings.mcp_a_audience,
        principal=principal,
        arguments=arguments,
    )
    if ctx is not None:
        audit_record.mcp_request_id = str(ctx.request_id)

    decision = evaluate(
        principal=principal,
        tool_name=tool_name,
        arguments=arguments,
        order=facts,
        settings=settings,
    )
    audit.apply_decision(audit_record, decision)

    if not decision.allowed or record is None:
        audit_record.result = "denied"
        audit_record.ledger_changed = False
        audit.write(audit_record)
        raise ToolDenied(decision)

    return principal, record, audit_record


mcp = MCPServer(
    name=SERVER_NAME,
    title="Refund assistant",
    version="1.0.0",
    instructions=(
        "Synthetic refund desk. Read an order, ask for an advisory assessment, and "
        "request a refund. Every call is authorized on the server against the "
        "signed-in user's delegated permissions; advisory text never grants permission."
    ),
    token_verifier=ValidatingTokenVerifier(_resource_audiences(), get_settings().mcp_a_audience),
    auth=AuthSettings(
        issuer_url=get_settings().issuer,  # type: ignore[arg-type]
        resource_server_url=get_settings().mcp_a_public_url,  # type: ignore[arg-type]
        required_scopes=[get_settings().scope_read],
        # Our TokenValidator checks the token's audience itself against this
        # resource's accepted identifiers, which is the configuration the SDK
        # documents for this flag. See docs/COMPATIBILITY-RECORD.md for why the
        # RFC 8707 resource indicator and the Entra audience are not the same
        # string.
        validate_token_resource=False,
    ),
)


@mcp.tool(
    name=TOOL_GET_ORDER,
    title="Get order",
    description=(
        "Return the authoritative facts for one synthetic order: totals, currency, "
        "remaining refundable balance, eligibility, and untrusted customer notes."
    ),
    annotations=ToolAnnotations(
        title="Get order",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def get_order(order_id: str, ctx: Context) -> dict[str, Any]:
    with span("tool.get_order", tool=TOOL_GET_ORDER, order_id=order_id):
        _, record, audit_record = _authorize(TOOL_GET_ORDER, {"order_id": order_id}, ctx)
        audit_record.result = "ok"
        audit.write(audit_record)
        data = record.to_dict()
        data["notes_are_untrusted_customer_content"] = True
        return data


@mcp.tool(
    name=TOOL_ASSESS_REFUND,
    title="Assess refund (advisory)",
    description=(
        "Ask a Microsoft Foundry model to summarize one order and suggest a disposition. "
        "The result is advisory only: this tool cannot issue a refund, cannot see tokens, "
        "and its output never grants permission."
    ),
    annotations=ToolAnnotations(
        title="Assess refund (advisory)",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def assess_refund(order_id: str, ctx: Context) -> dict[str, Any]:
    with span("tool.assess_refund", tool=TOOL_ASSESS_REFUND, order_id=order_id):
        _, record, audit_record = _authorize(TOOL_ASSESS_REFUND, {"order_id": order_id}, ctx)

        assessment = foundry.assess(record.to_dict())
        audit_record.model = audit.ModelInvocation(
            deployment=assessment.deployment,
            endpoint_host=assessment.endpoint_host,
            latency_ms=assessment.latency_ms,
            outcome=assessment.outcome,
            prompt_tokens=assessment.prompt_tokens,
            completion_tokens=assessment.completion_tokens,
            live=assessment.live,
        ).to_dict()
        audit_record.result = "ok"
        audit.write(audit_record)
        return assessment.to_dict()


@mcp.tool(
    name=TOOL_REFUND_ORDER,
    title="Refund order",
    description=(
        "Refund a synthetic order against the demo ledger. Consequential: this mutates state. "
        "The server authorizes this call independently of any client-side confirmation."
    ),
    annotations=ToolAnnotations(
        title="Refund order",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
async def refund_order(
    order_id: str,
    amount_minor: int,
    ctx: Context,
    currency: str | None = None,
    idempotency_key: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    arguments: dict[str, Any] = {
        "order_id": order_id,
        "amount_minor": amount_minor,
        "currency": currency or settings.refund_currency,
        "idempotency_key": idempotency_key or f"idem-{uuid.uuid4().hex[:16]}",
        "reason": reason,
    }

    with span("tool.refund_order", tool=TOOL_REFUND_ORDER, order_id=order_id):
        principal, record, audit_record = _authorize(TOOL_REFUND_ORDER, arguments, ctx)

        # Delegated identity to the upstream API. The incoming token is never
        # forwarded and there is no application-only fallback.
        try:
            delegated = await exchange_for_upstream(_raw_token(), settings)
        except DelegationError as exc:
            audit_record.upstream_audience = settings.upstream_api_audience
            audit_record.upstream_outcome = exc.reason_code
            audit_record.result = "delegation-failed"
            audit_record.decision = "deny"
            audit_record.reason_code = exc.reason_code
            audit_record.reason = exc.message
            audit.write(audit_record)
            raise ToolDenied(
                PolicyDecision(
                    allowed=False,
                    reason_code=exc.reason_code,
                    reason=exc.message,
                    rule_id="R300",
                    policy_version=settings.policy_version,
                )
            ) from exc

        audit_record.upstream_audience = delegated.audience

        payload = {
            "order_id": order_id,
            "amount_minor": amount_minor,
            "currency": arguments["currency"],
        }
        headers = {
            "Authorization": f"Bearer {delegated.access_token}",
            "Idempotency-Key": str(arguments["idempotency_key"]),
            "X-Trace-Id": audit_record.trace_id,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.upstream_api_url}/refunds", json=payload, headers=headers
            )

        audit_record.upstream_status = response.status_code
        body = response.json() if response.content else {}

        if response.status_code not in (200, 201):
            reason_code = str(body.get("reason_code", "UPSTREAM_REJECTED"))
            audit_record.upstream_outcome = reason_code
            audit_record.result = "denied-upstream"
            audit_record.decision = "deny"
            audit_record.reason_code = reason_code
            audit_record.reason = str(body.get("message", "upstream refused the refund"))
            audit.write(audit_record)
            raise ToolDenied(
                PolicyDecision(
                    allowed=False,
                    reason_code=reason_code,
                    reason=audit_record.reason,
                    rule_id="R301",
                    policy_version=settings.policy_version,
                )
            )

        refund = body.get("refund", {})
        replayed = bool(body.get("replayed"))
        audit_record.upstream_outcome = "replayed" if replayed else "applied"
        audit_record.result = "ok"
        audit_record.ledger_changed = not replayed
        audit.write(audit_record)

        return {
            "refund_id": refund.get("refund_id"),
            "order_id": refund.get("order_id"),
            "amount_minor": refund.get("amount_minor"),
            "currency": refund.get("currency"),
            "idempotent_replay": replayed,
            "delegated_identity_preserved": body.get("delegated_subject") == principal.subject,
            "upstream_audience": body.get("audience_that_authorized_this_call"),
            "trace_id": audit_record.trace_id,
            "policy_version": audit_record.policy_version,
        }


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    settings = get_settings()
    return JSONResponse(
        {
            "status": "ok",
            "service": SERVER_NAME,
            "auth_mode": settings.auth_mode,
            "issuer": settings.issuer,
            "resource": settings.mcp_a_public_url,
            "accepted_audiences": _resource_audiences(),
        }
    )


def build_app():
    configure("mcp-server")
    ledger.initialize()
    return mcp.streamable_http_app()


app = build_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host=settings.bind("0.0.0.0"), port=settings.mcp_a_port, log_level="warning")


if __name__ == "__main__":
    main()
