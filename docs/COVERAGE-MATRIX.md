# Coverage Matrix

Every promise in the published session description, mapped to the code that implements it, the check that proves it, the stage moment that shows it, the expected evidence, and the trust boundary responsible for it.

**Rule this matrix enforces:** nothing is claimed on stage that is not proven here, and nothing proven here is omitted from the talk. Under time pressure, [cut depth, never coverage](RUNBOOK.md#degradation-ladder).

**Tiers:** **A** = always live · **B** = live if on time, else prepared evidence · **C** = compress first.

Run everything: `.\scripts\check.ps1` (or `./scripts/check.sh`) → 207 automated tests + 14 scenarios.

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
| 5.8 | Show a control that lives **outside** the app and outside MCP | Azure content filter on the Foundry deployment; `foundry._filtered` reports it as a result, not an outage | `test_foundry.py::test_the_content_filter_is_reported_as_a_layer_that_acted_not_a_failure`, `::test_a_filtered_result_names_the_layer_outside_the_app`; `scenario prompt-injection` with `FOUNDRY_ENDPOINT` set | 15:00–20:00 **C** | `assessment_was_blocked_by_content_filter: True`, `handled_by: platform content filter` | Azure AI Content Safety |
| 5.9 | Show that the boundary is unchanged by which layer fired | Same policy denial with the filter on, the model answering, or nothing configured | `test_foundry.py::test_every_outcome_points_at_the_same_authorization_boundary`; `scenario prompt-injection` in both modes | 15:00–20:00 **A** | `authorization_still_enforced_by` identical in every outcome; ledger digest unchanged | MCP server |
| 5.10 | Never let a failed model call masquerade as a filtered one, or vice versa | `_is_content_filter` distinguishes them; defect 20 made this concrete | `test_foundry.py::test_a_genuine_failure_is_not_dressed_up_as_a_filter`, `::test_a_model_that_refuses_temperature_is_retried_without_it` | — **C** | Distinct labels and distinct `outcome` prefixes | MCP server |

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

## 7. Operator Safety

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 7.1 | Reset is not reachable from the MCP surface | `refund_demo/reset.py` is an operator module; no tool registers it | `test_discovery.py` lists exactly three tools | Pre-show | `reset` never appears in `tools/list` | Operator |
| 7.2 | Reset refuses to run against a real directory | `guard()` refuses when `AUTH_MODE=entra` unless `ALLOW_RESET=1` | `test_reset.py::test_reset_refuses_in_entra_mode_without_an_explicit_override` | Pre-show | `reset refused: ... AUTH_MODE=entra`, exit 2 | Operator |
| 7.3 | Reset cannot delete outside the demo data directory | Containment check against the audit log's directory | `test_reset.py::test_reset_only_ever_removes_files_inside_the_data_directory` | Pre-show | An out-of-scope file survives | Operator |
| 7.4 | Reset is safe to run between segments with services up | The signing key is preserved; rotation refused while `devidp` listens | `test_reset.py::test_reset_preserves_the_signing_key`, `::test_rotating_the_key_is_refused_while_devidp_is_running` | T-5 and between segments | Ledger returns to `211597d92491`; tokens keep validating | Operator |
| 7.5 | Every operator command works in both shells | `.ps1` + `.sh` twin for all 12 commands; `_common.sh` resolves the venv layout | `check.ps1` and `check.sh` both print `READY` | Pre-show | Identical results from PowerShell and bash | Operator |

---

## 8. Presentation Surface And Deployment

The web UI and the container deployments were added so the demo can be reused beyond one room. They must not become a second place where authorization is decided, and the three deployment descriptions must not drift apart.

| # | Requirement | Implementation | Check | Stage moment | Expected evidence | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| 8.1 | The web UI reports decisions and makes none | `web/app.py` calls `scenarios.run_one` and renders the result; no policy import | `test_web.py::test_run_endpoint_returns_a_real_scenario_result` | Optional | Verdicts match the terminal output exactly | Operator |
| 8.2 | The page fetches nothing from a third party | Single self-contained HTML document, inline CSS and JS | `test_web.py::test_page_has_no_external_resources` | Optional | No CDN, no build step, no external request | Operator |
| 8.3 | The listing cannot drift from what a run claims | Canonical `CLAIMS` dict is the single source for both | `test_web.py::test_claims_cover_every_scenario` | Pre-show | `scenario list` and the UI show identical claims | Operator |
| 8.4 | Reset stays shut over HTTP | `WEB_ALLOW_RESET` defaults off; still refused in `entra` mode | `test_web.py::test_reset_is_refused_by_default`, `::test_reset_still_refused_in_entra_mode` | Optional | `POST /api/reset` → `403` | Operator |
| 8.5 | No secret reaches the browser | Ledger and audit responses are filtered | `test_web.py::test_ledger_contains_no_secrets` | Optional | No token, code, or verifier in any response | Operator |
| 8.6 | The access-key gate covers every data route but not probes | `_gate()` on all routes; `/health` exempt | `test_web.py::test_access_key_gates_every_data_route` | Optional | `401` everywhere, `200` on `/health` | Operator |
| 8.7 | Compose, Kubernetes and the Dockerfile describe the same demo | One `TOPOLOGY` table; 48 assertions against it | `test_deploy_manifests.py` | Pre-show | Same five services, modules, ports and probes in all three | Operator |
| 8.8 | Containers override the loopback bind | `BIND_HOST=0.0.0.0` in the image, Compose, and the ConfigMap | `test_deploy_manifests.py::test_containers_override_the_bind_host` and twins | Pre-show | `devidp` is reachable inside the network | Operator |
| 8.9 | The state directory is shared and writable by a non-root user | One volume at `/app/.local`; `fsGroup: 10001` | `test_deploy_manifests.py::test_every_container_mounts_the_shared_state_directory`, `::test_pod_runs_as_a_non_root_user` | Pre-show | One ledger, one audit log, one key across five containers | Operator |
| 8.10 | The development issuer never gets a public address | Service exposes `8080` only | `test_deploy_manifests.py::test_only_the_web_container_is_exposed` | Pre-show | `devidp`, `mcp-a`, `mcp-b`, `upstream` stay internal | Operator |
| 8.11 | Containers are hardened | Non-root, read-only root filesystem, all capabilities dropped, no service-account token | `test_deploy_manifests.py::test_containers_are_hardened` | Pre-show | Every container passes | Operator |
| 8.12 | The signing key never enters an image layer | `.dockerignore` excludes `.local/`, `.venv/`, `*.pem`, `*.key` | `test_deploy_manifests.py::test_dockerignore_keeps_local_state_out_of_the_image`, plus a real image build | Pre-show | `.venv` and `tests` absent from the image; `.local` empty and writable | Operator |
| 8.13 | The image can be built on Linux from a Windows-frozen lockfile | Windows-only pins carry `; sys_platform == "win32"` | `test_deploy_manifests.py::test_requirements_mark_windows_only_pins` | Pre-show | `docker compose build` completes | Operator |
| 8.14 | DNS rebinding protection stays on, and still works behind a service name | Explicit `TransportSecuritySettings`; `MCP_ALLOWED_HOSTS` extends the loopback allowlist | `test_deploy_manifests.py::test_dns_rebinding_protection_stays_on_and_always_allows_loopback`, `::test_extra_allowed_hosts_extend_rather_than_replace_loopback`, `::test_both_mcp_servers_apply_the_transport_security_settings`, `::test_compose_allows_the_service_names_as_mcp_hosts` | Pre-show | Tool calls succeed in Compose; no `421` | Operator |
| 8.15 | The deploy script survives PowerShell parameter binding | `Invoke-Az` takes one `[string[]]` array, not `ValueFromRemainingArguments` | `test_deploy_manifests.py::test_deploy_helper_does_not_use_remaining_arguments` | Pre-show | `az ... -o none` no longer fails as "ambiguous" before the call is made | Operator |
| 8.16 | The image build survives a Windows console | `az acr build --no-logs`, with the `az acr task logs` command printed | `test_deploy_manifests.py::test_acr_build_does_not_stream_logs` | Pre-show | No `UnicodeEncodeError` after a successful push | Operator |
| 8.17 | The demo runs on a real cluster | `aks-up.ps1` end to end, then `run-all` against the public IP | Deployment runs, 2026-09-15 (twice) | Rehearsal | 5/5 containers ready, 0 restarts, 14/14 scenarios, ledger digest identical to the laptop | Operator |
| 8.18 | A missing access-key Secret fails closed, not open | `WEB_REQUIRE_ACCESS_KEY=1` on the public deployment | `test_web.py::test_a_public_deployment_without_a_key_refuses_to_serve` and twins; proven live by deleting the Secret | Pre-show | Every route `503`; `/health` still `200` so probes survive | Operator |
| 8.19 | The dev issuer is not reachable from the rest of the cluster | Per-container `BIND_HOST`; loopback for the four internal services | `test_deploy_manifests.py::test_internal_containers_bind_loopback_only`; proven live | Pre-show | `podIP:8800` refuses; `localhost:8800` answers | Operator |
| 8.20 | `/authorize` cannot be turned into an XSS or code-exfiltration primitive | `html.escape()` on interpolated params; loopback-only `redirect_uri` per RFC 8252 | `test_devidp_authorize.py` (10 tests) | Pre-show | Hostile `redirect_uri` refused; `<script>` escaped | Operator |

---

## Not proven — say so if asked

| Item | Status | Why |
| --- | --- | --- |
| Entra ID mode (`AUTH_MODE=entra`) | **Untested** | No tenant access was authorized. Code written and reviewed; never executed. |
| Azure deployment (`demo/infra`) | **Never deployed** | Bicep compiles (`az bicep build`); nothing was applied. |
| Live Foundry inference | **Verified** | Ran live against `gpt-5.6-sol`; benign order returned model text, injected order was refused by the content filter. Offline path still labelled `live: false`. |
| Client OAuth redirect URIs | **Unconfirmed** | Requires a live client; see `demo/identity/README.md`. |
| Least-privilege Foundry RBAC role | **Assumed** | Documented in `infra/modules/foundry.bicep`; not validated against live role definitions. |
| Client approval UI (4.3, 4.4) | **Manual only** | No automated test can prove a dialog appeared. |
| Container image build (8.x) | **Verified** | Builds clean; all 14 scenarios pass inside Compose; clean-ledger digest matches the laptop. |
| `readOnlyRootFilesystem` on AKS | **Verified** | Ran on a live pod with zero container restarts. |
| AKS deployment | **Verified** | Real cluster created; 5/5 containers ready, 0 restarts, 14/14 scenarios passed against the public IP, ledger digest matched the laptop. |
| `aks-up.sh` (bash deploy) | **Untested end to end** | The verified deployments ran `aks-up.ps1`. The bash twin is syntax-checked and equivalent command for command. |
| TLS on the cloud mode | **Absent by design** | The Service is plain HTTP and the access key travels in the URL. Anyone on the network path can read it. See [DEPLOYMENT.md §8](DEPLOYMENT.md#8-security-posture-of-the-cloud-mode). |
| Rate limiting | **None** | A visitor can grow the audit log on the pod's `emptyDir` until the container restarts. Costs the ledger, not a compromise. |
