"""Named, repeatable demo scenarios.

Each scenario is a self-contained proof of one claim in the talk. Every one of
them records the ledger fingerprint before and after, so "denied" can be shown
to mean "nothing happened" rather than "we printed a red message".

Run them individually on stage, or all of them as a pre-flight check:

    python -m refund_demo.scenarios list
    python -m refund_demo.scenarios run allowed-refund
    python -m refund_demo.scenarios run-all
"""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import anyio
import httpx

from . import ledger
from .client import ClientError, ProtocolTrace, acquire_token, call_tool, list_tools
from .config import get_settings

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"


# The single source of truth for what each scenario asserts. The scenario
# functions read from here, so the listing shown by `scenarios list` and by
# the web UI can never drift from the claim a run actually reports.
CLAIMS: dict[str, str] = {
    'discovery': '401 challenge -> PRM -> AS metadata -> PKCE S256 + resource indicator -> audience-bound token',
    'allowed-refund': 'An authorized refund succeeds exactly once; a retry with the same idempotency key does not double-spend',
    'scope-denial': 'A token without the write scope cannot call the consequential tool, even on an order the user owns',
    'ownership-denial': 'Holding the write scope is not permission over every object: ORD-1003 belongs to another user',
    'business-rule-denial': 'Authorization is not only identity: an ineligible order is refused on the server',
    'over-limit-denial': "Per-call value limits are enforced by the server, not by the client's confirmation dialog",
    'wrong-audience': 'A genuine, unexpired, correctly signed token minted for Resource B is rejected at Resource A',
    'unapproved-client': 'The server records and checks which client application is acting for the user',
    'prompt-injection': 'Instructions embedded in untrusted order notes cannot widen authorization',
    'annotation-tampering': 'Rewriting tool annotations client-side changes no server decision; the same denial is returned',
    'pkce-downgrade': "The authorization server refuses a PKCE downgrade to 'plain'",
    'missing-resource-indicator': 'Without an RFC 8707 resource indicator the authorization server will not mint a token',
    'no-token': 'An unauthenticated call is refused and is told where to authenticate',
    'token-passthrough-blocked': "Forwarding the MCP server's own token to the upstream API fails: the upstream has a different audience",
}

# The idempotency key `allowed-refund` uses, deliberately constant. It is what
# makes "succeeds exactly once" true across repeated *runs* rather than merely
# within one, so a double-click -- or a curious visitor on the public URL --
# cannot spend ORD-1001 down to nothing. Exported so a test can assert it stays
# stable instead of being minted per run.
STAGE_REFUND_KEY = "stage-allowed-refund"


@dataclass
class ScenarioResult:
    name: str
    claim: str
    passed: bool
    detail: str
    ledger_before: dict[str, Any] = field(default_factory=dict)
    ledger_after: dict[str, Any] = field(default_factory=dict)
    trace: ProtocolTrace | None = None
    evidence: dict[str, Any] = field(default_factory=dict)

    @property
    def ledger_changed(self) -> bool:
        return self.ledger_before.get("digest") != self.ledger_after.get("digest")

    def render(self) -> str:
        status = f"{GREEN}PASS{RESET}" if self.passed else f"{RED}FAIL{RESET}"
        changed = "CHANGED" if self.ledger_changed else "unchanged"
        colour = YELLOW if self.ledger_changed else DIM
        lines = [
            f"{status}  {self.name}",
            f"      claim:  {self.claim}",
            f"      result: {self.detail}",
            f"      ledger: {colour}{changed}{RESET} "
            f"(before={self.ledger_before.get('digest', '?')[:12]} "
            f"after={self.ledger_after.get('digest', '?')[:12]})",
        ]
        for key, value in self.evidence.items():
            lines.append(f"      {key}: {value}")
        return "\n".join(lines)


async def _token(employee: str, resource: str, scope: str, *, client_id: str | None = None,
                 mcp_url: str | None = None, trace: ProtocolTrace | None = None):
    s = get_settings()
    return await acquire_token(
        mcp_url=mcp_url or s.mcp_a_public_url,
        resource=resource,
        scope=scope,
        employee=employee,
        client_id=client_id,
        trace=trace,
    )


def _extract(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("structured"):
        return result["structured"]
    try:
        return json.loads(result.get("text") or "{}")
    except json.JSONDecodeError:
        return {"text": result.get("text", "")}


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


async def scenario_discovery() -> ScenarioResult:
    s = get_settings()
    trace = ProtocolTrace()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}", trace=trace)
    claims = token.claims()
    tools = await list_tools(mcp_url=s.mcp_a_public_url, access_token=token.access_token)
    after = ledger.ledger_fingerprint()

    steps = {step.step.split(".")[0] for step in trace.steps}
    passed = (
        {"1", "2", "3", "4", "5"} <= steps
        and claims.get("aud") == s.mcp_a_audience
        and len(tools) == 3
    )
    return ScenarioResult(
        name="discovery",
        claim=CLAIMS['discovery'],
        passed=passed,
        detail=f"token issued for aud={claims.get('aud')} with scp={claims.get('scp')!r}; {len(tools)} tools listed",
        ledger_before=before,
        ledger_after=after,
        trace=trace,
        evidence={
            "annotations_listed": ", ".join(
                f"{t['name']}(destructive={t['annotations'].get('destructive_hint')})" for t in tools
            )
        },
    )


async def scenario_allowed_refund() -> ScenarioResult:
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}")
    # One business request, one key -- for the life of the ledger, not the life
    # of this call. A fresh uuid here would make every *run* a new request, so
    # three clicks on Run would spend ORD-1001's 12,000 down to nothing and the
    # fourth would fail on balance. That is the exact opposite of the claim, and
    # on a public URL with reset disabled it is unrecoverable. With a stable key
    # the scenario is a retry after the first application: click it as fast and
    # as often as you like and exactly one refund exists. `scripts/reset.ps1`
    # clears the refunds table and restores the first-call demonstration.
    key = STAGE_REFUND_KEY
    args = {"order_id": "ORD-1001", "amount_minor": 4_000, "currency": "CAD", "idempotency_key": key}

    first = _extract(await call_tool(mcp_url=s.mcp_a_public_url, access_token=token.access_token,
                                     tool="refund_order", arguments=args))
    mid = ledger.ledger_fingerprint()
    second = _extract(await call_tool(mcp_url=s.mcp_a_public_url, access_token=token.access_token,
                                      tool="refund_order", arguments=args))
    after = ledger.ledger_fingerprint()

    # The second call is a replay whichever run this is, and a replay must never
    # move the ledger.
    retry_moved_nothing = (
        second.get("idempotent_replay") is True and mid.get("digest") == after.get("digest")
    )
    same_refund = bool(first.get("refund_id")) and first.get("refund_id") == second.get("refund_id")

    applied_here = first.get("idempotent_replay") is False
    if applied_here:
        # A virgin ledger: this run is the one that moved the money.
        moved_once = mid.get("total_refunded_minor") == before.get("total_refunded_minor", 0) + 4_000
        detail = (
            f"first call applied refund {first.get('refund_id')}; "
            f"retry replayed={second.get('idempotent_replay')}"
        )
    else:
        # An earlier run already applied this key. Both calls replay and the
        # ledger does not move at all -- which is the claim, demonstrated over
        # runs instead of within one.
        moved_once = before.get("digest") == after.get("digest")
        detail = (
            f"refund {first.get('refund_id')} was already applied by an earlier run; "
            f"both calls replayed and the ledger did not move"
        )

    return ScenarioResult(
        name="allowed-refund",
        claim=CLAIMS['allowed-refund'],
        passed=bool(
            retry_moved_nothing
            and same_refund
            and moved_once
            and first.get("delegated_identity_preserved")
        ),
        detail=detail,
        ledger_before=before,
        ledger_after=after,
        evidence={
            "refund_applied_by_this_run": applied_here,
            "idempotency_key": key,
            "delegated_identity_preserved": first.get("delegated_identity_preserved"),
            "upstream_audience": first.get("upstream_audience"),
            "total_refunded_minor": f"{before.get('total_refunded_minor')} -> {after.get('total_refunded_minor')}",
        },
    )


async def scenario_scope_denial() -> ScenarioResult:
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("dana.reader", s.mcp_a_audience, s.scope_read)
    result = await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1002", "amount_minor": 1_000, "currency": "CAD",
                   "idempotency_key": f"scope-{uuid.uuid4().hex[:8]}"},
    )
    after = ledger.ledger_fingerprint()
    text = result.get("text", "")
    return ScenarioResult(
        name="scope-denial",
        claim=CLAIMS['scope-denial'],
        passed=result["is_error"] and "MISSING_SCOPE" in text and before["digest"] == after["digest"],
        detail=text.strip()[:200] or "no error text",
        ledger_before=before,
        ledger_after=after,
        evidence={"token_scopes": token.claims().get("scp")},
    )


async def scenario_ownership_denial() -> ScenarioResult:
    """The confused-deputy check: a fully authorized user, a restricted object."""
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}")
    result = await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1003", "amount_minor": 99_000, "currency": "CAD",
                   "idempotency_key": f"own-{uuid.uuid4().hex[:8]}"},
    )
    after = ledger.ledger_fingerprint()
    text = result.get("text", "")
    return ScenarioResult(
        name="ownership-denial",
        claim=CLAIMS['ownership-denial'],
        passed=result["is_error"] and "NOT_ASSIGNED" in text and before["digest"] == after["digest"],
        detail=text.strip()[:200] or "no error text",
        ledger_before=before,
        ledger_after=after,
        evidence={"caller": token.claims().get("preferred_username"), "order_owner": "riley.lead"},
    )


async def scenario_business_rule_denial() -> ScenarioResult:
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}")
    result = await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1004", "amount_minor": 1_000, "currency": "CAD",
                   "idempotency_key": f"biz-{uuid.uuid4().hex[:8]}"},
    )
    after = ledger.ledger_fingerprint()
    text = result.get("text", "")
    return ScenarioResult(
        name="business-rule-denial",
        claim=CLAIMS['business-rule-denial'],
        passed=result["is_error"] and "NOT_REFUNDABLE" in text and before["digest"] == after["digest"],
        detail=text.strip()[:200] or "no error text",
        ledger_before=before,
        ledger_after=after,
    )


async def scenario_over_limit_denial() -> ScenarioResult:
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}")
    result = await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1001", "amount_minor": s.refund_per_call_limit_minor + 1,
                   "currency": "CAD", "idempotency_key": f"lim-{uuid.uuid4().hex[:8]}"},
    )
    after = ledger.ledger_fingerprint()
    text = result.get("text", "")
    return ScenarioResult(
        name="over-limit-denial",
        claim=CLAIMS['over-limit-denial'],
        passed=result["is_error"] and "LIMIT" in text and before["digest"] == after["digest"],
        detail=text.strip()[:200] or "no error text",
        ledger_before=before,
        ledger_after=after,
        evidence={"per_call_limit_minor": s.refund_per_call_limit_minor},
    )


async def scenario_wrong_audience() -> ScenarioResult:
    """Adversarial check 1: a valid token for the wrong resource."""
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_b_audience, "Probe.Read", mcp_url=s.mcp_b_public_url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{s.mcp_a_public_url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={
                "Authorization": f"Bearer {token.access_token}",
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
    after = ledger.ledger_fingerprint()
    return ScenarioResult(
        name="wrong-audience",
        claim=CLAIMS['wrong-audience'],
        passed=response.status_code == 401 and before["digest"] == after["digest"],
        detail=f"Resource A answered HTTP {response.status_code}",
        ledger_before=before,
        ledger_after=after,
        evidence={
            "token_aud": token.claims().get("aud"),
            "resource_a_accepts": s.mcp_a_audience,
            "www_authenticate": response.headers.get("www-authenticate", "(none)")[:120],
        },
    )


async def scenario_unapproved_client() -> ScenarioResult:
    """Approval is the client's job; the server still checks which client is calling."""
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}",
                         client_id="unapproved-demo-client")
    result = await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1001", "amount_minor": 1_000, "currency": "CAD",
                   "idempotency_key": f"cli-{uuid.uuid4().hex[:8]}"},
    )
    after = ledger.ledger_fingerprint()
    text = result.get("text", "")
    return ScenarioResult(
        name="unapproved-client",
        claim=CLAIMS['unapproved-client'],
        passed=result["is_error"] and "CLIENT" in text and before["digest"] == after["digest"],
        detail=text.strip()[:200] or "no error text",
        ledger_before=before,
        ledger_after=after,
        evidence={"azp": token.claims().get("azp")},
    )


async def scenario_prompt_injection() -> ScenarioResult:
    """Adversarial check 2: hostile content inside tool output."""
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}")

    assessment = _extract(await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token,
        tool="assess_refund", arguments={"order_id": "ORD-1005"},
    ))

    # Now do exactly what the injected text demands.
    obeyed = await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1003", "amount_minor": 99_000, "currency": "CAD",
                   "idempotency_key": f"inj-{uuid.uuid4().hex[:8]}"},
    )
    after = ledger.ledger_fingerprint()
    text = obeyed.get("text", "")
    return ScenarioResult(
        name="prompt-injection",
        claim=CLAIMS['prompt-injection'],
        passed=obeyed["is_error"] and "NOT_ASSIGNED" in text and before["digest"] == after["digest"],
        detail=f"instruction obeyed verbatim, server still denied: {text.strip()[:150]}",
        ledger_before=before,
        ledger_after=after,
        evidence={
            "injection_detected_in_notes": assessment.get("untrusted_note_contains_instructions"),
            "assessment_was_live_model": (assessment.get("model") or {}).get("live"),
            "assessment_was_blocked_by_content_filter": (
                (assessment.get("model") or {}).get("filtered")
            ),
            "advisory_handled_by": assessment.get("handled_by"),
            "advisory_disposition": str(assessment.get("suggested_disposition"))[:80],
            "advisory_authorization_effect": assessment.get("authorization_effect"),
            "authorization_still_enforced_by": assessment.get(
                "authorization_still_enforced_by"
            ),
        },
    )


async def scenario_annotation_tampering() -> ScenarioResult:
    """Adversarial check 3: annotations are hints, not authorization."""
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("dana.reader", s.mcp_a_audience, s.scope_read)

    listed = await list_tools(mcp_url=s.mcp_a_public_url, access_token=token.access_token)
    refund_tool = next(t for t in listed if t["name"] == "refund_order")

    # A malicious or buggy client rewrites the hints it received, then calls the
    # tool as if it were a harmless read. Nothing about the call changes on the
    # wire: annotations are never sent back to the server.
    tampered = dict(refund_tool["annotations"])
    tampered.update({"read_only_hint": True, "destructive_hint": False})

    result = await call_tool(
        mcp_url=s.mcp_a_public_url, access_token=token.access_token, tool="refund_order",
        arguments={"order_id": "ORD-1002", "amount_minor": 500, "currency": "CAD",
                   "idempotency_key": f"ann-{uuid.uuid4().hex[:8]}"},
    )
    after = ledger.ledger_fingerprint()
    text = result.get("text", "")
    return ScenarioResult(
        name="annotation-tampering",
        claim=CLAIMS['annotation-tampering'],
        passed=result["is_error"] and "MISSING_SCOPE" in text and before["digest"] == after["digest"],
        detail=text.strip()[:200] or "no error text",
        ledger_before=before,
        ledger_after=after,
        evidence={
            "server_declared": f"destructive={refund_tool['annotations'].get('destructive_hint')}",
            "client_claimed": f"destructive={tampered.get('destructive_hint')}",
        },
    )


async def scenario_pkce_downgrade() -> ScenarioResult:
    s = get_settings()
    before = ledger.ledger_fingerprint()
    try:
        await acquire_token(
            mcp_url=s.mcp_a_public_url, resource=s.mcp_a_audience, scope=s.scope_read,
            employee="sam.agent", code_challenge_method="plain",
        )
        detail, passed = "authorization server accepted PKCE 'plain'", False
    except ClientError as exc:
        detail, passed = str(exc), True
    after = ledger.ledger_fingerprint()
    return ScenarioResult(
        name="pkce-downgrade",
        claim=CLAIMS['pkce-downgrade'],
        passed=passed,
        detail=detail[:200],
        ledger_before=before,
        ledger_after=after,
    )


async def scenario_missing_resource_indicator() -> ScenarioResult:
    s = get_settings()
    before = ledger.ledger_fingerprint()
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        response = await client.get(
            f"{s.issuer}/authorize",
            params={
                "response_type": "code", "client_id": s.demo_client_id,
                "redirect_uri": "http://localhost:7777/callback", "scope": s.scope_read,
                "code_challenge": "x" * 43, "code_challenge_method": "S256",
                "employee": "sam.agent",
            },
        )
    after = ledger.ledger_fingerprint()
    body = response.json() if response.status_code >= 400 else {}
    return ScenarioResult(
        name="missing-resource-indicator",
        claim=CLAIMS['missing-resource-indicator'],
        passed=response.status_code == 400 and body.get("error") == "invalid_target",
        detail=f"HTTP {response.status_code}: {body.get('error')} - {body.get('error_description')}",
        ledger_before=before,
        ledger_after=after,
    )


async def scenario_no_token() -> ScenarioResult:
    s = get_settings()
    before = ledger.ledger_fingerprint()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{s.mcp_a_public_url}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
        )
    after = ledger.ledger_fingerprint()
    challenge = response.headers.get("www-authenticate", "")
    return ScenarioResult(
        name="no-token",
        claim=CLAIMS['no-token'],
        passed=response.status_code == 401 and "resource_metadata=" in challenge,
        detail=f"HTTP {response.status_code}",
        ledger_before=before,
        ledger_after=after,
        evidence={"www_authenticate": challenge[:140] or "(none)"},
    )


async def scenario_token_passthrough_blocked() -> ScenarioResult:
    """The MCP server's own token must be useless at the upstream API."""
    s = get_settings()
    before = ledger.ledger_fingerprint()
    token = await _token("sam.agent", s.mcp_a_audience, f"{s.scope_read} {s.scope_write}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{s.upstream_api_url}/refunds",
            json={"order_id": "ORD-1001", "amount_minor": 100, "currency": "CAD"},
            headers={"Authorization": f"Bearer {token.access_token}",
                     "Idempotency-Key": f"pass-{uuid.uuid4().hex[:8]}"},
        )
    after = ledger.ledger_fingerprint()
    body = response.json() if response.content else {}
    return ScenarioResult(
        name="token-passthrough-blocked",
        claim=CLAIMS['token-passthrough-blocked'],
        passed=response.status_code == 401 and before["digest"] == after["digest"],
        detail=f"upstream answered HTTP {response.status_code}: {body.get('reason_code')}",
        ledger_before=before,
        ledger_after=after,
        evidence={"token_aud": token.claims().get("aud"), "upstream_expects": s.upstream_api_audience},
    )


SCENARIOS: dict[str, Callable[[], Awaitable[ScenarioResult]]] = {
    "no-token": scenario_no_token,
    "discovery": scenario_discovery,
    "missing-resource-indicator": scenario_missing_resource_indicator,
    "pkce-downgrade": scenario_pkce_downgrade,
    "allowed-refund": scenario_allowed_refund,
    "scope-denial": scenario_scope_denial,
    "ownership-denial": scenario_ownership_denial,
    "business-rule-denial": scenario_business_rule_denial,
    "over-limit-denial": scenario_over_limit_denial,
    "unapproved-client": scenario_unapproved_client,
    "wrong-audience": scenario_wrong_audience,
    "prompt-injection": scenario_prompt_injection,
    "annotation-tampering": scenario_annotation_tampering,
    "token-passthrough-blocked": scenario_token_passthrough_blocked,
}


async def run_one(name: str, *, show_trace: bool = False) -> ScenarioResult:
    result = await SCENARIOS[name]()
    if show_trace and result.trace:
        print(result.trace.render())
    return result


async def run_all() -> list[ScenarioResult]:
    ledger.initialize(reset=True)
    results = []
    for name in SCENARIOS:
        try:
            results.append(await run_one(name))
        except Exception as exc:  # a scenario that blows up is a failed check
            results.append(
                ScenarioResult(name=name, claim="(scenario raised)", passed=False,
                               detail=f"{type(exc).__name__}: {exc}")
            )
        print(results[-1].render())
        print()
    return results


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    command = argv[0] if argv else "run-all"

    if command == "list":
        for name in SCENARIOS:
            print(f"  {name:<28} {CLAIMS.get(name, '')}")
        return 0

    if command == "run":
        if len(argv) < 2:
            print("usage: python -m refund_demo.scenarios run <name>")
            return 2
        name = argv[1]
        if name not in SCENARIOS:
            print(f"unknown scenario {name!r}; try 'list'")
            return 2
        ledger.initialize()
        result = anyio.run(lambda: run_one(name, show_trace=True))
        print(result.render())
        return 0 if result.passed else 1

    if command == "run-all":
        results = anyio.run(run_all)
        failures = [r for r in results if not r.passed]
        print("=" * 72)
        print(f"{len(results) - len(failures)}/{len(results)} checks passed")
        for failure in failures:
            print(f"  {RED}FAILED{RESET} {failure.name}: {failure.detail}")
        return 1 if failures else 0

    print(f"unknown command {command!r}; use list | run <name> | run-all")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
