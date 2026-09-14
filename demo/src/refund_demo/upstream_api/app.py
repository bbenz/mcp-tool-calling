"""The upstream refund API.

A separate service, with its own audience and its own delegated permission. It
owns the synthetic ledger. It is deployed with internal ingress, but network
placement is not a security control: it validates its own token and re-applies
its own object-level authorization on every call, exactly as if it were public.

It does not trust the MCP server to have checked anything.
"""

from __future__ import annotations

import logging

import anyio.to_thread
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .. import ledger
from ..config import get_settings
from ..fixtures import employee_by_subject
from ..telemetry import configure
from ..tokens import Principal, TokenValidationError, TokenValidator

logger = logging.getLogger("refund_demo.upstream")

REQUIRED_SCOPE = "Ledger.Refund"


def _validator() -> TokenValidator:
    settings = get_settings()
    return TokenValidator.for_resource(settings.upstream_api_audience, settings)


def _challenge(reason_code: str, message: str, status: int = 401) -> JSONResponse:
    settings = get_settings()
    headers = {
        "WWW-Authenticate": (
            f'Bearer realm="{settings.upstream_api_audience}", '
            f'error="invalid_token", error_description="{reason_code}"'
        )
    }
    return JSONResponse(
        {"error": "unauthorized", "reason_code": reason_code, "message": message},
        status_code=status,
        headers=headers,
    )


async def _authenticate(request: Request) -> Principal | JSONResponse:
    header = request.headers.get("authorization", "")
    if not header:
        return _challenge("AUTH_NO_TOKEN", "no bearer token was presented")
    try:
        # Blocking JWKS fetch: keep it off the event loop.
        return await anyio.to_thread.run_sync(_validator().validate, header)
    except TokenValidationError as exc:
        logger.info("upstream rejected token: %s", exc.reason_code)
        return _challenge(exc.reason_code, exc.message)


async def health(request: Request) -> Response:
    settings = get_settings()
    return JSONResponse(
        {
            "status": "ok",
            "service": "upstream-refund-api",
            "audience": settings.upstream_api_audience,
            "issuer": settings.issuer,
        }
    )


async def get_order(request: Request) -> Response:
    principal = await _authenticate(request)
    if isinstance(principal, JSONResponse):
        return principal

    order = ledger.get_order(request.path_params["order_id"])
    if order is None:
        return JSONResponse({"error": "not_found"}, status_code=404)
    return JSONResponse(order.to_dict())


async def fingerprint(request: Request) -> Response:
    return JSONResponse(ledger.ledger_fingerprint())


async def create_refund(request: Request) -> Response:
    """Apply a refund for the delegated user identity in the presented token."""
    principal = await _authenticate(request)
    if isinstance(principal, JSONResponse):
        return principal

    settings = get_settings()

    # Independent scope check. The MCP server's scope check does not count here.
    if not principal.has_scope(REQUIRED_SCOPE):
        return JSONResponse(
            {
                "error": "insufficient_scope",
                "reason_code": "UPSTREAM_MISSING_SCOPE",
                "message": f"delegated scope {REQUIRED_SCOPE} is required",
            },
            status_code=403,
            headers={
                "WWW-Authenticate": (
                    f'Bearer error="insufficient_scope", scope="{REQUIRED_SCOPE}"'
                )
            },
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_request", "reason_code": "UPSTREAM_BAD_BODY"}, status_code=400)

    order_id = body.get("order_id")
    amount_minor = body.get("amount_minor")
    currency = body.get("currency", settings.refund_currency)
    idempotency_key = request.headers.get("idempotency-key") or body.get("idempotency_key", "")
    trace_id = request.headers.get("x-trace-id", "")

    # Independent object-level authorization, re-derived from this token's
    # subject and the authoritative order record.
    employee = employee_by_subject(principal.subject)
    if employee is None:
        return JSONResponse(
            {"error": "forbidden", "reason_code": "UPSTREAM_UNKNOWN_PRINCIPAL"},
            status_code=403,
        )

    order = ledger.get_order(str(order_id))
    if order is None:
        return JSONResponse({"error": "not_found", "reason_code": "UPSTREAM_ORDER_NOT_FOUND"}, status_code=404)
    if order.assigned_to != employee.key:
        logger.info(
            "upstream denied cross-owner refund: subject=%s order=%s owner=%s",
            principal.subject, order.order_id, order.assigned_to,
        )
        return JSONResponse(
            {
                "error": "forbidden",
                "reason_code": "UPSTREAM_ORDER_NOT_ASSIGNED",
                "message": "the delegated user is not the assigned owner of this order",
            },
            status_code=403,
        )

    try:
        record = ledger.apply_refund(
            order_id=str(order_id),
            amount_minor=amount_minor,
            currency=str(currency),
            idempotency_key=str(idempotency_key),
            actor_subject=principal.subject,
            actor_upn=principal.upn,
            client_id=principal.client_id,
            trace_id=trace_id,
        )
    except ledger.LedgerError as exc:
        return JSONResponse(
            {"error": "rejected", "reason_code": f"UPSTREAM_{exc.reason_code}", "message": str(exc)},
            status_code=409,
        )

    return JSONResponse(
        {
            "refund": record.to_dict(),
            "audience_that_authorized_this_call": principal.audience,
            "delegated_subject": principal.subject,
            "replayed": record.replayed,
        },
        status_code=200 if record.replayed else 201,
    )


def create_app() -> Starlette:
    configure("upstream-refund-api")
    ledger.initialize()
    return Starlette(
        routes=[
            Route("/health", health),
            Route("/orders/{order_id}", get_order),
            Route("/refunds", create_refund, methods=["POST"]),
            Route("/ledger/fingerprint", fingerprint),
        ]
    )


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.upstream_api_port, log_level="warning")


if __name__ == "__main__":
    main()
