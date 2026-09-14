# Coverage Matrix

Every promise in the published session description, mapped to the code that implements it, the check that proves it, the stage moment that shows it, the expected evidence, and the trust boundary responsible for it.

**Rule this matrix enforces:** nothing is claimed on stage that is not proven here, and nothing proven here is omitted from the talk. Under time pressure, [cut depth, never coverage](RUNBOOK.md#degradation-ladder).

**Tiers:** **A** = always live · **B** = live if on time, else prepared evidence · **C** = compress first.

Run everything: `.\scripts\check.ps1` → 78 automated tests + 14 scenarios.

---

## 1. MCP Authorization And Resource Binding

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | Unauthenticated request gets 401 with `WWW-Authenticate` metadata reference | SDK `AuthSettings` + `mcp_server/verifier.py` returning `None` | `test_discovery.py::test_unauthenticated_call_returns_401_with_resource_metadata`; `scenario no-token` | 02:00–07:00 **A** | HTTP 401; header names Protected Resource Metadata | MCP server |
| 1.2 | Fetch and display Protected Resource Metadata, then AS metadata | `client.py::discover` | `test_discovery.py::test_protected_resource_metadata_names_the_authorization_server` | 02:00–07:00 **A** | PRM names the AS; AS metadata advertises endpoints | MCP server / AS |
| 1.3 | Authorization-code flow with PKCE **S256** and a resource indicator in **both** requests | `client.py::acquire_token`; `devidp/server.py` | `test_discovery.py::test_authorization_server_advertises_s256_and_resource_indicators`, `::test_full_flow_yields_a_token_bound_to_one_audience`; `scenario discovery` | 02:00–07:00 **A** | Trace shows `code_challenge_method=S256`, `resource=api://refund-mcp-a` | Client / AS |
| 1.4 | Show only safe field names and redacted values — never verifier, code, or token | `client.py::ProtocolTrace` redacts by construction | `test_adversarial.py::test_every_denial_is_audited_with_a_reason_code_and_no_raw_identifiers` | every segment **A** | No secret appears in any trace or log | Presenter |
| 1.5 | Requested vs granted scopes; sanitized claims: iss, aud, sub, tid, client, exp | `client.py` trace + `tokens.py::Principal` | `scenario discovery` output | 02:00–07:00 **A** | Claim names and pseudonymized values only | AS / MCP server |
| 1.6 | Validate signature via trusted JWKS; allowed algorithms; iss, tenant, aud, exp | `tokens.py::TokenValidator` | `test_tokens.py` — `test_unsigned_token_is_rejected`, `test_hmac_signed_token_is_rejected`, `test_token_signed_by_an_untrusted_key_is_rejected`, `test_wrong_issuer_is_rejected`, `test_wrong_tenant_is_rejected`, `test_expired_token_is_rejected`, `test_not_yet_valid_token_is_rejected` | 15:00–20:00 **A** | `alg: none` and HS256 both rejected; **decoding is not validating** | MCP server |
| 1.7 | Reject ID tokens and app-only tokens where delegated access is required | `tokens.py` app-only + `typ` checks | `test_tokens.py::test_app_only_token_is_rejected`, `::test_id_token_shaped_token_is_rejected` | 15:00–20:00 **B** | `AUTH_APP_ONLY_TOKEN`, `AUTH_WRONG_TOKEN_TYPE` | MCP server |
| 1.8 | Identity from validated claims, never tool arguments or headers | `mcp_server/app.py::_authorize` reads `get_access_token()` only | `test_policy.py::test_identity_in_arguments_is_ignored`; `test_adversarial.py::test_extra_arguments_cannot_smuggle_permissions` | 11:00–15:00 **A** | A `user_id` argument changes nothing | MCP server |
| 1.9 | Resource binding stops cross-resource reuse — **not** replay at the intended resource | Distinct audiences per resource | `test_tokens.py::test_token_for_resource_b_is_rejected_at_resource_a` **plus control** `::test_a_resource_may_accept_several_identifiers_for_itself`; `scenario wrong-audience` | 15:00–20:00 **A** | B-token fails at A; A-token succeeds at A | MCP server |
| 1.10 | Honest scope of the claim — state the limitation aloud | `docs/CONTROL-MAP.md` Layer 2 | Narration | 15:00–20:00 **A** | Spoken: *"this stops cross-resource reuse, not a stolen token at its own resource"* | Presenter |

## 2. Runtime Tool Policy And Business Arguments

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 2.1 | Authenticate at transport **and** authorize again at `tools/call` | `verifier.py` then `_authorize()` in every tool | `scenario scope-denial` (token valid, call denied) | 07:00–11:00 **A** | Valid token, denied call | MCP server |
| 2.2 | Listing / hiding / schema validation are **not** authorization boundaries | All three tools visible to every principal | `test_discovery.py::test_tools_are_listed_with_honest_annotations` | 07:00–11:00 **A** | `tools/list` identical for reader and refunder | MCP server |
| 2.3 | Deterministic deny-by-default policy → allow/deny + stable reason code + policy version | `policy.py::decide`, version `refund-policy/2026-10-06.1` | `test_policy.py::test_every_decision_carries_a_rule_id_and_policy_version`; all 20 policy tests | 07:00–11:00 **A** | Every decision carries rule ID + version | MCP server |
| 2.4 | Named fixtures: employee↔order, allowed clients, eligibility, currency, positive integer minor units, remaining balance, per-call limit | `fixtures.py` (3 employees, 2 clients, 5 orders) | `test_policy.py` R001–R204 rows | 07:00–11:00 **C** | Deterministic across runs | MCP server |
| 2.5 | A reader, a refund-capable employee, and an unapproved client | `dana.reader`, `riley.lead`, `sam.agent`; `unapproved-client-app` | `test_adversarial.py::test_an_unapproved_client_application_is_refused`; `scenario unapproved-client` | 07:00–11:00 **B** | `POLICY_CLIENT_NOT_ALLOWED` (R001) | MCP server |
| 2.6 | Avoid redundant live sign-ins — prepare sessions in advance | Scenario harness pre-acquires tokens | `scenario run-all` pre-flight | pre-talk **A** | No repeated interactive sign-in on stage | Presenter |
| 2.7 | Allowed read, missing-scope denial, business-rule denial, allowed refund | `get_order`, `assess_refund`, `refund_order` | `scenario allowed-refund`, `scope-denial`, `business-rule-denial` | 07:00–15:00 **A** | R100 allow; R003 deny; R200 deny; R299 allow | MCP server |
| 2.8 | Authoritative order data, never model-supplied identifiers | `ledger.py` is the only source of order truth | `test_policy.py::test_identity_in_arguments_is_ignored` | 11:00–15:00 **A** | Ownership read from the ledger | MCP server |
| 2.9 | Idempotency + atomic update; retries and concurrency cannot double-refund | `ledger.py::apply_refund` with `BEGIN IMMEDIATE` | `test_idempotency.py::test_same_idempotency_key_applies_once`, `::test_concurrent_identical_retries_apply_exactly_once`, `::test_concurrent_distinct_refunds_cannot_overdraw`, `::test_replay_with_a_different_amount_is_rejected` | 11:00–15:00 **A** | Ledger total rises **once**; mismatched replay → `IDEMPOTENCY_KEY_REUSED` | Upstream API |
| 2.10 | Recheck critical rules in the upstream API at mutation time | `upstream_api/app.py` re-checks ownership, eligibility, balance | `test_delegation.py::test_upstream_reenforces_ownership_with_its_own_token`, `::test_upstream_requires_its_own_scope`; `test_idempotency.py::test_ineligible_order_is_refused_at_the_ledger_too` | 11:00–15:00 **B** | Upstream denies independently | Upstream API |
| 2.11 | Distinguish transport auth failure, insufficient scope, and tool/business error | 401 vs `ToolError` with reason code | `scenario no-token` vs `scope-denial` vs `business-rule-denial` | 15:00–20:00 **A** | Three visibly different failures | MCP server |
| 2.12 | **Never report a rejected call as a successful refund** | `ToolDenied(ToolError)`; `is_error=True`; ledger digest printed | Every denial scenario prints `ledger: UNCHANGED` | 15:00–20:00 **A** | Reason code reaches the client; digest identical | MCP server |

## 3. Delegation To The Upstream API

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 3.1 | Preserve the human identity via a documented delegated flow (OBO) | `delegation.py`; RFC 7523 jwt-bearer at `devidp`, MSAL OBO in `entra` mode | `test_delegation.py::test_exchange_changes_the_audience_but_keeps_the_subject` | 11:00–15:00 **A** | `sub` identical, `aud` different | MCP server |
| 3.2 | Acquire a **new** token for the upstream audience | `delegation.py::exchange_for_upstream` | `test_delegation.py::test_the_exchanged_token_is_accepted_by_the_upstream_api` | 11:00–15:00 **A** | `aud = api://refund-upstream` | MCP server / AS |
| 3.3 | Never pass through the incoming token; no silent app-only fallback; no header-carried user ID | No passthrough path exists; failure raises `DelegationError` | `test_delegation.py::test_the_incoming_token_is_rejected_by_the_upstream_api`; `scenario token-passthrough-blocked` | 11:00–15:00 **A** | Forwarded MCP token → 401 at upstream | Upstream API |
| 3.4 | Sanitized evidence: audience differs, user preserved; upstream enforces its own rules | Scenario prints `upstream_audience` + `delegated_identity_preserved` | `test_delegation.py::test_a_successful_refund_reports_the_delegated_subject`, `::test_the_exchanged_token_records_the_acting_service` | 11:00–15:00 **A** | Both printed on one line | Upstream API |
| 3.5 | The exchange requires a confidential-client credential | `devidp` verifies the client assertion | `test_delegation.py::test_the_exchange_requires_a_confidential_client_credential`, `::test_a_wrong_client_secret_is_refused`, `::test_a_junk_assertion_is_refused` | 11:00–15:00 **C** | Exchange refused without a valid credential | AS |
| 3.6 | Managed identity for app-to-Azure access, distinguished from delegated user identity | `foundry.py` uses `DefaultAzureCredential`; `infra/modules/identity-rbac.bicep` | ⚠️ **Not deployed** — code + Bicep reviewed only | 07:00–11:00 **C** | Narration + code bookmark; say it is not deployed | Workload identity |

## 4. Annotations And Human Approval

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 4.1 | Accurate annotations incl. read-only/destructive/idempotent hints | `mcp_server/app.py` — `get_order` read-only; `refund_order` destructive, idempotent | `test_discovery.py::test_tools_are_listed_with_honest_annotations` | 11:00–15:00 **A** | Annotations visible in `tools/list` | MCP server |
| 4.2 | Altering an annotation cannot turn a denial into an allow | Server never reads client-supplied annotations | `test_adversarial.py::test_annotations_are_hints_and_never_reach_the_server`; `scenario annotation-tampering` | 11:00–15:00 **A** | Same denial, same rule ID | MCP server |
| 4.3 | Client configured for explicit approval with exact arguments; no broad auto-approval | `demo/client-config/mcp.json.example` | **Manual** — `CLIENT-APPROVAL-CHECKLIST.md` B1–B2 | 11:00–15:00 **B** | Approval prompt shows the real arguments | Client |
| 4.4 | Cancel → no mutation; approve → normal server checks | — | **Manual** — checklist B3–B4 | 11:00–15:00 **B** | Cancel: ledger digest unchanged, no audit record | Client |
| 4.5 | **User approval must not override a server denial** | Policy runs after approval, always | **Manual** — checklist C1–C3; automated equivalent `scenario over-limit-denial` | 11:00–15:00 **A** | Approved by the human, denied by the server | MCP server |
| 4.6 | The client owns this interaction; `approved=true` is not proof; no signed receipt in MCP | `policy.py` ignores unknown arguments | `test_adversarial.py::test_extra_arguments_cannot_smuggle_permissions` | 11:00–15:00 **A** | Narration + passing test | Client / MCP server |
| 4.7 | Do not claim the server observes a cancelled request; mark client-only evidence | Checklist labels B3 **client-only** | Documented | 11:00–15:00 **A** | Absence of a record is the only server-side signal | Presenter |

## 5. Three Distinct Adversarial Checks

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 5.1 | **Prompt injection** in untrusted order notes attempting an unauthorized refund | `fixtures.INJECTION_NOTE` on `ORD-1004`; `foundry.py` | `test_adversarial.py::test_injected_instructions_in_order_notes_cannot_widen_authorization`, `::test_assessment_cannot_be_used_as_a_capability`, `::test_the_advisory_tool_marks_itself_as_non_authoritative`; `scenario prompt-injection` | 15:00–20:00 **B** | Record what the model did, **then** force the candidate call: denied, ledger unchanged | Foundry (none) → MCP server |
| 5.2 | Do not present model refusal as the boundary | Harness forces the call regardless of model output | Same as 5.1 | 15:00–20:00 **A** | Spoken: *"it doesn't matter what the model said"* | Presenter |
| 5.3 | **Confused deputy** — valid token, broader authority attempted | R006 object-level check | `test_adversarial.py::test_a_fully_authorized_user_cannot_reach_another_users_order` + control `::test_the_owner_can_act_on_the_same_order`; `scenario ownership-denial` | 15:00–20:00 **A** | `POLICY_ORDER_NOT_ASSIGNED`; deputy + authority mismatch named aloud | MCP server |
| 5.4 | Prove no broad service credential or passthrough bypass exists | No app-only fallback anywhere | `scenario token-passthrough-blocked` | 15:00–20:00 **A** | Forwarded token fails at the upstream audience | Upstream API |
| 5.5 | **Token reuse at the wrong MCP server**, with a valid B-token control | Resource B on :8802, distinct audience | `test_adversarial.py::test_token_minted_for_resource_b_is_rejected_at_resource_a` + `::test_the_same_token_works_at_its_own_resource`; `scenario wrong-audience` | 15:00–20:00 **A** | A succeeds; B rejected **before tool execution**; control proves B is not simply broken | MCP server |
| 5.6 | Keep adversarial fixtures synthetic and presenter-owned | All fixtures local; `devidp` never runs in cloud | `fixtures.py` | — **A** | No real customer data anywhere | Presenter |
| 5.7 | Label a harness replay as a harness replay | Scenario output says so explicitly | `scenario prompt-injection` | 15:00–20:00 **A** | Never presented as a fresh model attack | Presenter |

## 6. Audit Evidence And Attendee Control Map

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 6.1 | One record tying call → timestamp, trace ID, MCP request ID, pseudonymous user, tenant, client, audience, tool, argument summary, policy version, decision/reason, upstream outcome, result | `audit.py` | `test_adversarial.py::test_every_denial_is_audited_with_a_reason_code_and_no_raw_identifiers` | 20:00–23:00 **A** | `scripts\audit.ps1` renders every field | MCP server |
| 6.2 | Link Foundry invocation metadata to the same trace; no full prompts or customer content | `foundry.py` records deployment, latency, outcome only | `scenario prompt-injection` audit record | 20:00–23:00 **C** | Model metadata, same trace ID, no prompt text | MCP server |
| 6.3 | Record only **validated** claims; rejected tokens marked untrusted | `audit.py::record_rejected_token` | `test_adversarial.py::test_a_rejected_token_is_audited_without_attributing_an_identity` | 20:00–23:00 **A** | `identity_state: untrusted`, no user/tenant attributed | MCP server |
| 6.4 | Never log credentials, codes, verifiers, tokens, or full claims | Allowlisted argument summary; `_omitted_keys` | Same as 6.1 | 20:00–23:00 **A** | `idempotency_key` appears only in `_omitted_keys` | MCP server |
| 6.5 | Keep client approval evidence separate; do not fabricate an approval field | No `approved` field exists in the record | Inspect `audit.py` | 20:00–23:00 **A** | Server record is silent about approval | MCP server / Client |
| 6.6 | Working Application Insights/Log Analytics query **plus** a local JSON view for stage reliability | `telemetry.py` schema; query in `docs/APPENDIX.md`; `audit_view.py` | `scripts\audit.ps1` | 20:00–23:00 **C** (KQL) / **A** (local) | Local view always works offline | Observability |
| 6.7 | `docs/CONTROL-MAP.md` with owner, inputs, enforcement point, denial behavior, evidence, limitations for all five layers | `docs/CONTROL-MAP.md` | Present | 20:00–25:00 **A** | On screen through Q&A | — |
| 6.8 | **Do not claim ordinary logs are immutable or tamper-proof** | Stated in `CONTROL-MAP.md` and `audit.py` | Documented | 20:00–23:00 **A** | Spoken: *"this is a JSONL file, not tamper-evident storage"* | Presenter |

---

## Not proven — say so if asked

| Item | Status | Why |
| --- | --- | --- |
| Entra ID mode (`AUTH_MODE=entra`) | **Untested** | No tenant access was authorized. Code written and reviewed; never executed. |
| Azure deployment (`demo/infra`) | **Never deployed** | Bicep compiles (`az bicep build`); nothing was applied. |
| Live Foundry inference | **Not configured** | Offline path is explicitly labelled `live: false`. |
| Client OAuth redirect URIs | **Unconfirmed** | Requires a live client; see `demo/identity/README.md`. |
| Least-privilege Foundry RBAC role | **Assumed** | Documented in `infra/modules/foundry.bicep`; not validated against live role definitions. |
| Client approval UI (4.3, 4.4) | **Manual only** | No automated test can prove a dialog appeared. |
