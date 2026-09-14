"""Structured audit evidence.

One record ties a ``tools/call`` to: when, which trace, which MCP request,
which validated user, which tenant, which client, which resource/audience,
which tool, a sanitized argument summary, which policy version and decision,
the upstream outcome, and the final result.

Rules enforced here rather than left to the caller:

* Identity is recorded only when it was validated. A rejected token produces
  ``identity_state="untrusted"`` and no attributed user, because the claims in
  an unverified token are just attacker-supplied strings.
* The user is pseudonymized. A stable salted hash is enough to correlate a
  session on stage without projecting a real-looking UPN.
* Secrets never enter a record. Arguments are summarized through an allowlist,
  and any key that looks credential-shaped is dropped outright.
* Client-side approval is *not* invented. If the server has no trusted signal
  that a human approved, the field says exactly that.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Mapping

from .config import get_settings
from .policy import PolicyDecision
from .tokens import Principal

logger = logging.getLogger("refund_demo")

_WRITE_LOCK = threading.Lock()

_PSEUDONYM_SALT = "mcp-dev-summit-toronto-2026-demo"

_SENSITIVE_KEY_HINTS = (
    "token", "secret", "password", "passwd", "credential", "authorization",
    "code_verifier", "client_secret", "assertion", "apikey", "api_key", "key",
    "cookie", "session", "refresh",
)

_ARGUMENT_ALLOWLIST = ("order_id", "amount_minor", "currency", "idempotency_key", "reason")

APPROVAL_NOT_OBSERVABLE = "not-observable-by-server"


def pseudonymize(value: str) -> str:
    if not value:
        return ""
    digest = hashlib.sha256(f"{_PSEUDONYM_SALT}:{value}".encode("utf-8")).hexdigest()
    return f"user_{digest[:12]}"


def summarize_arguments(arguments: Mapping[str, Any] | None) -> dict[str, Any]:
    """Allowlist-based argument summary. Unknown keys are counted, not copied."""
    if not arguments:
        return {}
    summary: dict[str, Any] = {}
    dropped: list[str] = []
    for key, value in arguments.items():
        lowered = str(key).lower()
        if any(hint in lowered for hint in _SENSITIVE_KEY_HINTS):
            dropped.append(str(key))
            continue
        if key not in _ARGUMENT_ALLOWLIST:
            dropped.append(str(key))
            continue
        if isinstance(value, str) and len(value) > 64:
            summary[key] = f"{value[:61]}..."
        else:
            summary[key] = value
    if dropped:
        summary["_omitted_keys"] = sorted(dropped)
    return summary


@dataclass
class ModelInvocation:
    deployment: str = ""
    endpoint_host: str = ""
    latency_ms: int = 0
    outcome: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    live: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditRecord:
    trace_id: str
    mcp_request_id: str
    tool: str
    resource_audience: str

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="milliseconds"))
    identity_state: str = "untrusted"
    user_pseudonym: str = ""
    tenant_id: str = ""
    client_id: str = ""
    granted_scopes: list[str] = field(default_factory=list)
    issuer: str = ""

    arguments: dict[str, Any] = field(default_factory=dict)

    policy_version: str = ""
    policy_rule_id: str = ""
    decision: str = "deny"
    reason_code: str = ""
    reason: str = ""

    upstream_audience: str = ""
    upstream_outcome: str = ""
    upstream_status: int | None = None

    model: dict[str, Any] | None = None

    result: str = ""
    ledger_changed: bool = False
    client_approval_evidence: str = APPROVAL_NOT_OBSERVABLE

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def new_trace_id() -> str:
    return uuid.uuid4().hex


def start_record(
    *,
    tool: str,
    resource_audience: str,
    principal: Principal | None,
    arguments: Mapping[str, Any] | None = None,
    trace_id: str | None = None,
    mcp_request_id: str = "",
) -> AuditRecord:
    record = AuditRecord(
        trace_id=trace_id or new_trace_id(),
        mcp_request_id=mcp_request_id,
        tool=tool,
        resource_audience=resource_audience,
        arguments=summarize_arguments(arguments),
    )
    if principal is not None:
        record.identity_state = "validated"
        record.user_pseudonym = pseudonymize(principal.subject)
        record.tenant_id = principal.tenant_id
        record.client_id = principal.client_id
        record.granted_scopes = list(principal.scopes)
        record.issuer = principal.issuer
    return record


def record_rejected_token(
    *,
    tool: str,
    resource_audience: str,
    reason_code: str,
    reason: str,
    trace_id: str | None = None,
) -> AuditRecord:
    """Audit for a token that failed validation.

    No user, tenant, or client is attributed: none of those claims were
    verified, so recording them would be recording an assertion by the caller.
    """
    record = AuditRecord(
        trace_id=trace_id or new_trace_id(),
        mcp_request_id="",
        tool=tool,
        resource_audience=resource_audience,
    )
    record.identity_state = "untrusted"
    record.decision = "deny"
    record.reason_code = reason_code
    record.reason = reason
    record.result = "rejected-before-tool-execution"
    return record


def apply_decision(record: AuditRecord, decision: PolicyDecision) -> AuditRecord:
    record.policy_version = decision.policy_version
    record.policy_rule_id = decision.rule_id
    record.decision = "allow" if decision.allowed else "deny"
    record.reason_code = decision.reason_code
    record.reason = decision.reason
    return record


def write(record: AuditRecord) -> AuditRecord:
    settings = get_settings()
    path = settings.audit_log_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = json.dumps(record.to_dict(), separators=(",", ":"), sort_keys=True)
    with _WRITE_LOCK:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    _emit_telemetry(record)
    return record


_NESTED_FIELDS = ("arguments", "granted_scopes", "model")


def _emit_telemetry(record: AuditRecord) -> None:
    """Mirror the audit record onto the structured logger.

    When Application Insights is configured, ``azure-monitor-opentelemetry``
    turns these ``extra`` keys into ``customDimensions``, so the KQL queries in
    ``docs/APPENDIX.md`` resolve against exactly the fields written here.
    Nested values are JSON-encoded because custom dimensions are string-valued.

    Telemetry is best effort. The local JSONL file is the evidence of record,
    and nothing about exporting may break an audit write.
    """
    try:
        from . import telemetry

        dimensions: dict[str, Any] = {"service_name": telemetry.service_name()}
        for key, value in record.to_dict().items():
            dimensions[key] = json.dumps(value, sort_keys=True) if key in _NESTED_FIELDS else value
        logger.info(
            "audit %s %s %s",
            record.tool,
            record.decision,
            record.reason_code,
            extra=dimensions,
        )
    except Exception:  # pragma: no cover - telemetry must never break an audit write
        pass


def read_all(limit: int | None = None) -> list[dict[str, Any]]:
    path = get_settings().audit_log_path
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return rows[-limit:] if limit else rows


def clear() -> None:
    path = get_settings().audit_log_path
    if os.path.exists(path):
        os.remove(path)
