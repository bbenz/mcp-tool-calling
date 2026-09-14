"""Deny-by-default runtime tool policy.

This is the decision point the talk is about. It runs at ``tools/call``, after
the token has been validated, and it maps

    validated identity + tenant + calling client + delegated scopes
    + tool name + validated arguments + authoritative order facts

to an allow/deny result with a stable reason code and a policy version.

Three properties matter:

1. Deny-by-default. Every path that is not explicitly allowed returns a denial.
2. Authoritative facts only. Order ownership, eligibility, currency, and
   balance come from the ledger, never from tool arguments or model output.
3. No side effects. Evaluating policy never mutates anything, so it is safe to
   call from a test harness with an arbitrary candidate call.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping

from .config import Settings, get_settings
from .fixtures import employee_by_subject
from .tokens import Principal

TOOL_GET_ORDER = "get_order"
TOOL_ASSESS_REFUND = "assess_refund"
TOOL_REFUND_ORDER = "refund_order"

KNOWN_TOOLS = (TOOL_GET_ORDER, TOOL_ASSESS_REFUND, TOOL_REFUND_ORDER)


@dataclass(frozen=True)
class OrderFacts:
    """Authoritative order state, read from the ledger."""

    order_id: str
    assigned_to: str
    currency: str
    refundable: bool
    restricted: bool
    refundable_balance_minor: int


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: str
    reason: str
    rule_id: str
    policy_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _deny(reason_code: str, reason: str, rule_id: str, version: str) -> PolicyDecision:
    return PolicyDecision(
        allowed=False, reason_code=reason_code, reason=reason, rule_id=rule_id, policy_version=version
    )


def _allow(rule_id: str, version: str, reason: str = "request satisfies all policy rules") -> PolicyDecision:
    return PolicyDecision(allowed=True, reason_code="ALLOW", reason=reason, rule_id=rule_id, policy_version=version)


def _required_scope(tool_name: str, settings: Settings) -> str:
    return {
        TOOL_GET_ORDER: settings.scope_read,
        TOOL_ASSESS_REFUND: settings.scope_read,
        TOOL_REFUND_ORDER: settings.scope_write,
    }[tool_name]


def evaluate(
    *,
    principal: Principal,
    tool_name: str,
    arguments: Mapping[str, Any],
    order: OrderFacts | None,
    settings: Settings | None = None,
) -> PolicyDecision:
    """Return an allow/deny decision. Never raises for a policy failure."""
    s = settings or get_settings()
    version = s.policy_version

    # R001 - the calling client application must be approved for this server.
    if principal.client_id not in s.allowed_client_id_list:
        return _deny(
            "POLICY_CLIENT_NOT_ALLOWED",
            f"client application {principal.client_id!r} is not approved to call this MCP server",
            "R001", version,
        )

    # R002 - deny-by-default on unknown tools.
    if tool_name not in KNOWN_TOOLS:
        return _deny("POLICY_UNKNOWN_TOOL", f"tool {tool_name!r} is not governed by this policy", "R002", version)

    # R003 - the delegated scope required for this specific tool.
    required = _required_scope(tool_name, s)
    if not principal.has_scope(required):
        return _deny(
            "POLICY_MISSING_SCOPE",
            f"tool {tool_name!r} requires delegated scope {required!r}; token granted {list(principal.scopes)}",
            "R003", version,
        )

    # R004 - the validated subject must map to a known employee. Identity comes
    # from the token, never from an argument.
    employee = employee_by_subject(principal.subject)
    if employee is None:
        return _deny(
            "POLICY_UNKNOWN_PRINCIPAL",
            "validated subject does not map to a known employee fixture",
            "R004", version,
        )

    # R005 - the order must exist in the authoritative ledger.
    if order is None:
        order_id = arguments.get("order_id", "<missing>")
        return _deny("POLICY_ORDER_NOT_FOUND", f"order {order_id!r} does not exist", "R005", version)

    # R006 - object-level authorization: employees act only on their own book.
    # This is the boundary the confused-deputy attempt runs into. The upstream
    # refund API enforces the same ownership rule independently, so a bypass
    # here would still not produce a ledger change.
    if order.assigned_to != employee.key:
        return _deny(
            "POLICY_ORDER_NOT_ASSIGNED",
            f"order {order.order_id} is assigned to another employee; {employee.key} may not act on it",
            "R006", version,
        )

    if tool_name in (TOOL_GET_ORDER, TOOL_ASSESS_REFUND):
        return _allow("R100", version, f"{tool_name} permitted for the assigned employee")

    # ---- refund_order only, from here down ------------------------------

    # R200 - eligibility, checked against the ledger and not the model.
    if not order.refundable:
        return _deny(
            "POLICY_ORDER_NOT_REFUNDABLE",
            f"order {order.order_id} is not eligible for refund",
            "R200", version,
        )

    amount = arguments.get("amount_minor")

    # R201 - arguments must be well-formed before they mean anything.
    if isinstance(amount, bool) or not isinstance(amount, int):
        return _deny(
            "POLICY_AMOUNT_INVALID",
            "amount_minor must be an integer number of minor units",
            "R201", version,
        )
    if amount <= 0:
        return _deny("POLICY_AMOUNT_INVALID", "amount_minor must be greater than zero", "R201", version)

    # R202 - currency must match the order's own currency.
    currency = arguments.get("currency", order.currency)
    if currency != order.currency:
        return _deny(
            "POLICY_CURRENCY_MISMATCH",
            f"currency {currency!r} does not match order currency {order.currency!r}",
            "R202", version,
        )

    # R203 - configurable per-call ceiling.
    if amount > s.refund_per_call_limit_minor:
        return _deny(
            "POLICY_AMOUNT_EXCEEDS_PER_CALL_LIMIT",
            f"amount_minor {amount} exceeds the per-call limit {s.refund_per_call_limit_minor}",
            "R203", version,
        )

    # R204 - never refund more than remains.
    if amount > order.refundable_balance_minor:
        return _deny(
            "POLICY_AMOUNT_EXCEEDS_BALANCE",
            f"amount_minor {amount} exceeds remaining refundable balance {order.refundable_balance_minor}",
            "R204", version,
        )

    return _allow("R299", version, "refund permitted: identity, client, scope, ownership and arguments all check out")
