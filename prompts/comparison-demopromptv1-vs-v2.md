# Prompt Comparison: `demopromptv1.md` vs `demopromptv2.md`

Record of the review of `prompts/demopromptv1.md` and the changes made in `prompts/demopromptv2.md`.

- **Reviewed:** September 14, 2026
- **Files:** `prompts/demopromptv1.md` (baseline), `prompts/demopromptv2.md` (revision)
- **Target session:** *Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy*, MCP Dev Summit Toronto, October 6, 2026, 15:40-16:05

## Verdict

v1 was already strong: accurate against the accepted proposal in `Events/MCP-Dev-Summit-Toronto-2026-Approved-Proposals.md`, correctly scoped, and unusually precise about security boundaries. No requirement was wrong, no promise from the published description was missing, and the 25-minute run-of-show arithmetic was correct.

The weaknesses were in **executability**, not correctness. v1 read as a comprehensive specification rather than an executable work order: no build sequence, no concrete output location, an assumption about the repository that is not true, no plan for the two most likely live-demo failure modes, and no guidance for what to sacrifice when the 25-minute budget slips.

v2 is therefore an **additive revision, not a rewrite**. The requirement language was preserved as closely as possible so that nothing hard-won in v1 was lost.

## Change Statistics

| Metric | v1 | v2 |
| --- | --- | --- |
| Lines | 199 | 306 |
| Words | 3,727 | 5,262 |
| Bytes | 26,710 | 37,159 |
| Top-level sections (`##`) | 10 | 13 |
| Subsections (`###`) | 6 | 14 |
| Headings (all levels) | 17 | 28 |

Line-level comparison:

| Category | Count |
| --- | --- |
| v1 lines carried into v2 **verbatim** | 176 of 199 (88%) |
| v1 lines reworded, relocated, or absorbed | 23 |
| v1 lines deleted with no replacement | 0 |
| New lines in v2 | 130 |

No requirement, constraint, prohibition, or acceptance criterion from v1 was dropped. The 23 changed lines were all rewritten or split across sections; each is itemized below.

## Structural Map

| v1 section | v2 section | Change |
| --- | --- | --- |
| — | **Non-Negotiables** | New |
| Mission And Source Of Truth | Mission And Source Of Truth | Minor edits |
| — | **Repository Starting State And Output Contract** | New |
| Confirmed Constraints | Confirmed Constraints | 1 constraint added (8 → 9), 1 extended |
| First Actions And Compatibility Gate | **Phase Plan And Gates** (Phases 0-5) | Expanded and re-framed |
| One Story | One Story | 1 clause removed |
| Required Behavior And Evidence §1-§6 | Required Behavior And Evidence §1-§6 | Verbatim, 2 artifact names added |
| Mandatory 25-Minute Run Of Show | Mandatory 25-Minute Run Of Show | Table unchanged |
| — | **Time Discipline: Cut Depth, Never Coverage** | New |
| Implementation And Setup Deliverables (1-8) | Implementation And Setup Deliverables (1-9) | Deliverable 9 added; 4, 5, 7 extended |
| Reliability And Safety | Reliability And Safety | 1 bullet added (8 → 9), 1 extended |
| — | **Stage And Screen Hygiene** | New |
| — | **Preparation Timeline** | New |
| Verification And Completion Contract | Verification And Completion Contract | 4 clauses tightened |
| Authoritative Starting References | Authoritative Starting References | Unchanged |

## Substantive Improvements

### 1. Phase plan with gates (new)

**Problem:** v1 delivered roughly 3,700 words of unordered requirements for a multi-service, multi-tenant, cloud-deployed build. An agent had to invent its own sequence, and there was no defined point at which it should surface findings before committing to an architecture.

**Change:** v1's `First Actions And Compatibility Gate` became `Phase Plan And Gates`, with Phase 0 absorbing all eight original first-action items, followed by five build phases, each with a stated exit gate:

| Phase | Scope | Gate |
| --- | --- | --- |
| 0 | Ground truth, compatibility, tenant capability, model selection | Compatibility record + architecture + blockers; stop and report |
| 1 | Local vertical slice: protected server, `get_order`, real token validation | 401 challenge, authorized read, written audit record |
| 2 | Foundry `assess_refund`, `refund_order`, upstream API, delegation, idempotency | One refund exactly once, scope denial, business-rule denial, audience evidence |
| 3 | Second resource, three adversarial checks, annotations, approval, telemetry | All three checks automated; ledger unchanged on every denial |
| 4 | Cloud deployment | **Approval gate** before touching any tenant or subscription |
| 5 | Presenter materials and timed rehearsal | Handoff report |

Added rule: do not start a later phase to work around an unresolved earlier gate; report the blocker instead.

### 2. Repository starting state and output contract (new)

**Problem:** v1's first instruction was to "inspect repository instructions and nearby existing work... reuse suitable project conventions." The repository contains only `Events/` and `prompts/` — no README, no agent instructions, no manifest, no source, and **no initialized git repository**. The instruction was a near no-op that invited invented "conventions", and v1's only placement guidance was "one clearly named subtree."

**Change:** v2 states the actual starting state, tells the agent to re-verify it, and then fixes the ambiguity:

- Code and infrastructure under `demo/`; presenter and attendee materials under `docs/`; `Events/` and `prompts/` untouched.
- Initialize git and commit `.gitignore` **before** generating code, covering `.env*`, `*.pem`, `*.pfx`, `*.key`, token/trace caches, `.azure/`, `__pycache__/`, `.venv/`, and local ledger/audit output.
- Committed `.env.example` with names and descriptions only.
- Seven named deliverable files so the presenter can find them under pressure: `RUNBOOK.md`, `ONSTAGE-SCRIPT.md`, `COVERAGE-MATRIX.md`, `CONTROL-MAP.md`, `COMPATIBILITY-RECORD.md`, `SETUP.md`, `RISKS-AND-FALLBACKS.md`.

The `.gitignore`-first rule matters disproportionately here: this project handles tokens, client secrets, certificates, and audit traces, and v1 already forbade committing secrets without saying how to make that structurally likely.

### 3. Tenant capability gate (new — highest-value addition)

**Problem:** v1 verified MCP and Entra *protocol* interoperability thoroughly but assumed the target directory would permit the setup. Registering applications, exposing delegated scopes, adding authorized client applications, and granting consent are frequently blocked by policy in a corporate tenant, and conditional access or device-compliance policy can break an interactive browser sign-in performed on conference network. Discovering this late invalidates the identity design, which is the spine of the talk.

**Change:** Phase 0 step 7 requires confirming, before designing around a tenant, that it actually permits registration, scope exposure, authorized-client configuration, and the required consent, and that no policy blocks the planned interactive sign-in. If blocked, recommend a dedicated demo tenant and treat the choice as a blocking question for the presenter.

### 4. Time-discipline ladder (new)

**Problem:** v1 correctly enforced a 25-minute budget and required a fallback per segment, but gave no priority ordering. Under time pressure a presenter cuts whatever is next, which risks dropping something the published description promised attendees.

**Change:** a `Cut Depth, Never Coverage` section built on one principle — everything the published description promises must appear on screen at least as a stated result with visible evidence; only the *method* of producing it degrades.

- **Tier A, always live:** 401 challenge and Protected Resource Metadata fetch; one allowed refund with the ledger changing exactly once; one `tools/call` policy denial; the wrong-audience rejection; the audit record tying request to user, client, resource, policy, and result.
- **Tier B, live if on time, otherwise prepared evidence:** interactive sign-in, live Foundry `assess_refund`, cancel-then-approve cycle, annotation tampering, live prompt-injection model run.
- **Tier C, compress first:** narration depth, code walkthroughs, the Application Insights query, appendix topics.

Plus a mechanical rule: if a segment runs more than 45 seconds over, switch to its prepared evidence artifact and move on. Each runbook step is tagged with its tier and stop-time so the presenter does no arithmetic on stage.

### 5. Client version pinning (new constraint)

**Problem:** v1 asked the agent to *record* presenter client versions. It did not prevent the client from changing after rehearsal. An auto-update to the GitHub Copilot app or VS Code between rehearsal and stage can silently alter MCP authorization, discovery, or approval-prompt behavior — the exact surfaces this talk depends on.

**Change:** a constraint to pin the rehearsed build, disable or defer auto-update for the demo window, and re-verify the demo if the client updates. The completion contract now also requires the approval behavior to be verified **on the pinned build**.

### 6. Token lifetime and stage-time validity (new)

**Problem:** v1 told the presenter to prepare sessions in advance to avoid redundant live sign-ins, and separately to warm services. It never addressed the consequence: pre-warmed sessions and cached tokens expire, and the failure appears mid-demo as an opaque 401.

**Change:** document each credential's expected lifetime, implement refresh where supported, add a 30-second preflight that proves the session is still valid immediately before the talk, and keep a rehearsed re-authentication path that fits inside a segment.

### 7. Stage and screen hygiene (new)

**Problem:** v1's only presentation guidance was "keep screen switching minimal and project well at conference font sizes." For a security talk projected in a ballroom, the screen itself is a disclosure surface.

**Change:** a presenter machine checklist covering notifications and focus assist off; mail, chat, and calendar closed; a demo-only browser profile with no corporate autofill, saved passwords, or personal bookmarks; legible terminal and editor fonts; a projector-appropriate high-contrast theme; a fixed window layout; shell history cleared of anything sensitive; and pseudonymized user principal names and tenant identifiers on any audience-visible screen.

This extends v1's existing prohibition on leaking secrets into "logs, command arguments, or screenshots" to the live projected display and to tenant-identifying metadata.

### 8. Preparation timeline (new)

**Problem:** v1 specified a great deal of pre-event work — provision, consent, warm, seed, test connectivity, rehearse logins, capture replay artifacts — with no schedule. At review time the event was roughly three weeks away.

**Change:** T-minus milestones anchored to October 6, 2026: T-14 local build complete and blockers escalated; T-10 cloud deployed and suite green; T-7 first timed rehearsal on the pinned client with replay artifacts captured; T-3 second rehearsal after full fixture reset, materials frozen; T-1 warmed, seeded, credentials re-validated, offline fallbacks verified openable; day-of preflight with no updates installed. The agent is told to adjust and say so if less runway remains, rather than silently compressing.

### 9. Risk register deliverable (new, deliverable 9)

**Problem:** v1 required a fallback per run-of-show segment and a tiered fallback strategy, but no single place where the presenter could see failure mode, detection signal, and response together.

**Change:** `docs/RISKS-AND-FALLBACKS.md` listing each realistic failure mode — expired token, client update, cold start, conference network, Foundry throttling, telemetry ingestion delay, model nondeterminism, consent prompt reappearing — with a detection cue recognizable within seconds and the exact prepared fallback.

### 10. Non-negotiables summary (new)

**Problem:** v1's most important rules were distributed across roughly 3,700 words, with the critical delegation prohibition sitting in §3 and the evidence rule in the mission paragraph.

**Change:** ten numbered rules at the top covering source of truth, shipping running code, verifying before designing, enforcement at `tools/call`, the no-token-passthrough and no-app-token-fallback rule, the secrets prohibition, synthetic data only, the 25-minute budget, the gate/ask policy, and the instruction to resolve routine engineering choices without asking. Each is elaborated in the body; the summary duplicates rather than replaces.

## Line-Level Changes To Existing v1 Text

Every v1 line that is not carried over verbatim, and what happened to it.

| # | v1 text | Disposition in v2 |
| --- | --- | --- |
| 1 | Title `# Demo Generation Prompt: ...` | Retitled `# Demo Generation Prompt v2: ...` |
| 2 | "Generate the on-stage script as a separate deliverable." | Reworded; script now named `docs/ONSTAGE-SCRIPT.md` |
| 3 | "...published description are the authoritative requirements." | "published schedule description are authoritative" |
| 4 | "The session is on October 6, 2026, from 15:40 to 16:05..." | Added room: "in Ballroom East/Center" |
| 5 | "Do not claim execution or deployment succeeded without evidence." | Promoted to Non-Negotiable 2 |
| 6 | Foundry prominence constraint | Added: confirm current product name and documentation URL at implementation time |
| 7 | Heading `## First Actions And Compatibility Gate` | Became `## Phase Plan And Gates`; items became Phase 0 |
| 8 | First action 1 (inspect repo, reuse conventions, one subtree) | Shortened; superseded by the new starting-state and output-contract section |
| 9 | First action 7 (reference client / broker) | Moved to Phase 0 step 9; "use" changed to "plan" to fit the phase ordering |
| 10 | "Resolve routine choices independently..." paragraph | Split four ways: Non-Negotiables 9 and 10, Phase 4 approval gate, and the replay clause in the completion contract |
| 11 | ACA host bullet, "...unless an existing supported repository pattern provides a simpler equivalent" | Clause removed — the repository has no existing pattern, so the escape hatch was dead text |
| 12 | "Create a coverage matrix with one row for every requirement..." | Now names `docs/COVERAGE-MATRIX.md` |
| 13 | "Provide an MCP-specific control map showing..." | Now names `docs/CONTROL-MAP.md` |
| 14 | Deliverable 4, presenter client configuration | Added: record the pinned client version |
| 15 | Deliverable 5, operator commands | Added: no live step should require typing a long command; provide short aliases or task entries |
| 16 | Deliverable 7, presenter runbook | Split into runbook plus on-stage script, with tiers and stop-times added |
| 17 | "For cloud deployment... ask for explicit approval before provisioning..." | Approval requirement moved to the Phase 4 gate; the placeholder rule stayed with the deliverables |
| 18 | Prebuild/warm/connectivity bullet | Added: verify browser sign-in and localhost redirect on conference network; identify a tethered-hotspot fallback |
| 19 | "Build incrementally and run focused checks..." | Added: a replay does not count as a successful live integration |
| 20 | "...its approval behavior is manually verified." | "...manually verified on the pinned build." |
| 21 | "...rehearsed the 25-minute flow." | "...rehearsed the full flow within 25 minutes." |
| 22 | "...links to the runbook and attendee control map." | Reworded to "the runbook and control map"; the named artifacts are now defined in the output contract |
| 23 | "Start by reporting the selected architecture..." | "Start with Phase 0. Report the selected architecture, the compatibility record, and any true blockers..." |

## Deliberately Unchanged

These were reviewed and judged correct as written. Preserving them was a goal of the revision.

- **All of `Required Behavior And Evidence` §1-§6**, including the adversarial-checks table, carried over verbatim. This is the security core of the prompt and it maps cleanly to the accepted proposal.
- **The 25-minute run-of-show table.** The segment arithmetic sums exactly to 25 minutes and the ordering follows the narrative arc of the published description. Only the surrounding time-discipline guidance was added.
- **All eight original `Confirmed Constraints`**, which were extended but never relaxed.
- **The `One Story` architecture**, including the three-tool design (`get_order`, `assess_refund`, `refund_order`), the Foundry call located inside `assess_refund`, the separate upstream API with its own audience, and the second MCP resource with a genuinely different accepted audience.
- **Every security prohibition**: no token passthrough, no application-token fallback, no header-based identity, no secret in a public client, no fail-open switch, no fabricated approval field, no attributing identity from unvalidated claims, no claiming application logs are tamper-proof.
- **The `Authoritative Starting References` list** and the instruction to recheck all of it at implementation time rather than trusting either prompt's snapshot of product behavior.
- **The closing framing question**: *Who can call this tool, for this resource, with these arguments, and where is that decision enforced?*

## Summary

v2 keeps 88% of v1's lines verbatim and drops nothing. It adds a build sequence with gates, a concrete output contract for an empty repository, a tenant-capability check that could otherwise invalidate the identity design late, a cut-order that protects the talk's promises when time slips, and mitigations for the three most common ways a live OAuth demo fails: an expired token, an auto-updated client, and a hostile network.
