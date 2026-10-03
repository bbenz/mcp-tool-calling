# Presenter guide

## Handoff and status

**Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy**  
Brian Benz, Principal AI Advocate, Microsoft  
MCP Dev Summit Toronto, October 6, 2026, 15:40-16:05 EDT (UTC-4), Ballroom East/Center.

Six main slides and thirteen genuinely hidden backups. The slide file is
[who-can-call-this-mcp-tool.pptx](who-can-call-this-mcp-tool.pptx).
The [PDF](who-can-call-this-mcp-tool.pdf) contains **all 19 pages**, including
backups, in the same numeric order. PDF viewers do not honor hidden slides:
stay on page 6 for Q&A; do not scroll onward accidentally.

Read [verification.md](verification.md) for the final validation status and
remaining rehearsal actions. This generation did not execute the demo, tests,
scenarios, services, model calls, Azure commands or deployment scripts.
It did not inspect live state or credentials. All newly described scenario
outcomes are **EXPECTED / ILLUSTRATIVE**, unless explicitly identified as
**RECORDED** from a dated supplied document. **LIVE** is a label the presenter
may use only after actually observing an execution.

The public [event schedule](https://events.linuxfoundation.org/mcp-dev-summit-toronto/program/schedule/?id=1284815)
was reconfirmed during generation on September 16, 2026. Room and timing are
subject to change. Toronto is the **first delivery**. The public
[repository](https://github.com/bbenz/mcp-tool-calling) was confirmed public using
GitHub repository metadata. The QR targets that exact public repository.
These newly generated files have not been committed, pushed or published.

## Read this before going on stage

- Use the rehearsed **local PowerShell** route. All demo commands below assume
  a terminal already in `demo`. They are instructions, not actions taken by the
  generating agent. Bash twins are supplied, not a second competing stage plan.
- Keep four prepared windows: slides, Terminal A for scenarios, Terminal B for
  audit, and the editor at `policy.py::evaluate`, `tokens.py::TokenValidator`
  and the MCP tool definitions. No automatic slide advance.
- The PowerPoint file uses local Calibri and native editable shapes/text. All
  projected text is at least 24 pt, title text 38-44 pt. The QR is the sole
  raster asset. There are no required transitions, videos or network assets.
- The local browser UI, if the presenter chooses it, is a **reporting surface**.
  Use A-/A+ (or + / - / 0) before projection. Leave **About this demo** and
  **Sends / Expects / Why** expanders collapsed, showing one only when useful.
  Its Run button is not a client approval dialog.
- Do not promise instant remote fallback. A configured Foundry call may wait
  before returning labeled offline advice. Cut optional model depth when slow.
- A security expectation can PASS on a denial. Never equate PASS with a refund.
- The 0 -> 4000 -> 4000 illustration assumes a clean ledger. Do not reset or
  mutate a live/shared deployment merely to match a slide.
- For an all-offline fallback, use the hidden slides or PDF and say
  **EXPECTED / ILLUSTRATIVE**, not "here is the run we just captured."
- Preflight client approval separately. The supplied manual checklist has no
  filled client version/date/result. Its fixture identities also drift; use the
  corrected instructions below. A server test cannot prove a dialog appeared.

## Exact 25-minute pacing

| Elapsed | Budget | Projector / action | Hard stop | Fallback jump |
|---|---:|---|---|---|
| 00:00-02:00 | 2 min | Slides 1-3: title, three questions, trust boundary | 02:00 | PDF 1-3 |
| 02:00-07:00 | 5 min | Terminal A: no-token, discovery | 07:00 | 7 |
| 07:00-11:00 | 4 min | Read/advice explanation; scope/business denials; policy file | 11:00 | 8; 14 for model modes |
| 11:00-15:00 | 4 min | Annotation tampering, optional approval, allowed refund/delegation | 15:00 | 10, then 9 |
| 15:00-20:00 | 5 min | Wrong audience, confused deputy, prompt injection | 20:00 | 11, 12, 13; 14 if needed |
| 20:00-23:00 | 3 min | Audit until ~21:00, then slides 4-6; recovery buffer inside | 23:00 | 15, then 4 |
| 23:00-25:00 | 2 min | Q&A, control map stays on slide 6 | 25:00 | 6; selected backup only |

**Sum: 25:00, including 2:00 Q&A.** Backup slides consume their original segment
budget, not additional minutes. Generation/rebuild time is outside the talk.

Opening slide cues: 1 at 00:00-00:25; 2 at 00:25-01:05; 3 at 01:05-02:00.
Leave the deck on 3 while the demo occupies the projector. Closing cues:
4 approximately 21:00-21:50; 5 at 21:50-22:35; 6 at 22:35 through 25:00.

If more than 45 seconds behind a hard stop, switch to the labeled fallback.
Cut explanation depth, optional sign-in, code browsing and cloud telemetry
first. **Never cut any of the three adversarial lessons.**
Do not debug a client sign-in for more than 20 seconds.
For terminal loss, follow 7 -> 8 -> 10 -> 9 -> 11 -> 12 -> 13 -> 15 -> 4 -> 5 -> 6
within the original clock. Backup 14 is optional clarification, not another act.

## Demo segment cards: action -> expected response -> why -> evidence

### 02:00-07:00: discover and bind

```powershell
.\scripts\scenario.ps1 no-token
.\scripts\scenario.ps1 discovery
```

Bash:
```bash
./scripts/scenario.sh no-token
./scripts/scenario.sh discovery
```

Browser alternative: Run `no-token`, then `discovery`, on the already-running
local UI. No need to run every scenario or expand every briefing.

**Send:** unauthenticated request; then discovery and authorization-code flow.
**Expect:** HTTP 401 with `WWW-Authenticate` metadata reference; PRM -> AS
metadata -> PKCE S256 -> RFC 8707 `resource` in both authorization and token
requests -> audience-bound token. Compare requested and granted scopes.
**Why:** identity must be trusted and resource-specific before tool policy runs.
**Evidence:** actual sanitized trace if presenter runs it; otherwise backup 7
is EXPECTED, not a newly captured exchange.

Speak: "Decoding is not validating. The resource checks trusted issuer keys,
algorithm, signature, issuer, audience, lifetime and delegated identity.
Tenant is checked where configured. Resource binding stops reuse at a different
resource, not replay of a stolen bearer token at its own resource."

Optional depth: `missing-resource-indicator` and `pkce-downgrade` through the
same wrapper. No token should issue. Do not project authorization codes,
verifiers, bearer tokens, assertions or any credential value.

### 07:00-11:00: read, assess, deny

Optional preconfigured live client as **Sam**: "Show me order ORD-1001"; then
"Assess whether order ORD-1001 should be refunded and show the assessment."
This names actual tools (`get_order`, `assess_refund`) through a live client.
There is **no `assess-refund` scenario**. Without that client, explain the
read/assessment behavior from backup 8 and the source, not an invented action.

```powershell
.\scripts\scenario.ps1 scope-denial
.\scripts\scenario.ps1 business-rule-denial
```

Bash:
```bash
./scripts/scenario.sh scope-denial
./scripts/scenario.sh business-rule-denial
```

Browser: Run those exact two scenario names.

**Send:** Dana attempts `refund_order` on owned `ORD-1002` without write scope;
Sam attempts a refund on owned but ineligible `ORD-1004`.
**Expect:** `POLICY_MISSING_SCOPE` / R003; `POLICY_ORDER_NOT_REFUNDABLE` / R200;
both ledger fingerprints unchanged.
**Why:** token identity/scopes and authoritative order state are different
checks. Tools remain listed; listing is not access control.
**Evidence:** reason, rule, policy version and before/after fingerprint.
These are tool/business denials, not transport HTTP 401.

Next window: editor `demo/src/refund_demo/policy.py::evaluate`, then Terminal A.
Policy version is `refund-policy/2026-10-06.1`. Do not use the stale `decide`
symbol. Backup: 8; for model mode distinctions use 14. Hard stop 11:00.

### 11:00-15:00: annotations, approval, allowed refund and delegation

```powershell
.\scripts\scenario.ps1 annotation-tampering
.\scripts\scenario.ps1 allowed-refund
```

Bash:
```bash
./scripts/scenario.sh annotation-tampering
./scripts/scenario.sh allowed-refund
```

Browser: Run those exact scenario names.

**Send:** the harness rewrites local annotation hints; Dana still attempts a
write without `Refunds.Write`. Hints are **not sent back as authorization
fields** in `tools/call`.
**Expect:** R003 / `POLICY_MISSING_SCOPE`, unchanged ledger.
**Why:** annotations are hints from an untrusted process, not policy inputs.

Optional real-client approval: demonstrate Cancel/Approve only after a
separate completed rehearsal. Cancel prevents sending; it is not a server
denial. Approve does not replace policy. Use Dana/ORD-1002 for an approved
missing-scope denial, not Sam. Never use a browser Run button as proof of a
client approval dialog. If unavailable, state the intended semantics and use
the server-side `over-limit-denial` scenario without claiming a dialog appeared.

**Allowed send:** Sam, `ORD-1001`, `amount_minor=4000`, `currency=CAD`, then the
identical request and idempotency key.
**Expect:** `idempotent_replay` false then true; total increases by 4000 once.
`0 -> 4000 -> 4000` is a clean-baseline illustration, not an unconditional output.
**Delegation:** new `api://refund-upstream` audience, same human; upstream checks
scope/object/business rules independently. No passthrough, no app-only fallback.
**Evidence:** `upstream_audience`, `delegated_identity_preserved`, replay flags
and ledger delta. Do not invent a refund ID or expose the key.

Optional negative control: `token-passthrough-blocked` through the same
PowerShell/bash scenario wrapper; the upstream rejects the MCP-audience token
with HTTP 401. Backup 10, then 9. Hard stop 15:00.

### 15:00-20:00: protect all three adversarial lessons

```powershell
.\scripts\scenario.ps1 wrong-audience
.\scripts\scenario.ps1 ownership-denial
.\scripts\scenario.ps1 prompt-injection
```

Bash:
```bash
./scripts/scenario.sh wrong-audience
./scripts/scenario.sh ownership-denial
./scripts/scenario.sh prompt-injection
```

Browser: Run the same three named rows, in that order.

1. **Wrong audience (~15:00-16:30):** B token presented to A -> HTTP 401,
   `AUTH_WRONG_AUDIENCE` in the rejection evidence, no tool dispatch, unchanged
   ledger. **The scenario does not perform a successful HTTP call to B.**
   A separate HTTP/MCP integration test asserts B-token acceptance at B.
   It acquires a fresh token, not the token from the A-rejection test, and was
   not executed here. A continuous **same-token A/B trace** is still
   EXPECTED CONTROL - NOT CAPTURED.
2. **Deputy (~16:30-18:00):** Sam with `Refunds.Write` targets Riley's
   `ORD-1003` for 99000 minor units -> R006 /
   `POLICY_ORDER_NOT_ASSIGNED`, unchanged ledger. Ownership comes before the
   amount limit. The server is the deputy; it must not use upstream capability
   on Sam's behalf for an object Sam does not own.
3. **Injection (~18:00-20:00):** Sam assesses injected notes in `ORD-1005`;
   then the harness explicitly forces `refund_order` on `ORD-1003` for 99000
   minor units -> R006, unchanged ledger. This is a **forced harness replay**,
   not an observed autonomous model attack. A model answer, platform filtering
   or offline advice cannot change the authorization boundary.

If filtered, say "platform content filter", not "model refusal".
`filtered: true` can coexist with `live: false`. If offline, read the explicit
offline-assessment label. A configured failed call may wait before fallback.
Do not display fabricated token counts, timestamps, latency or PASS badges.
Fallback: slides 11, 12, 13; optional 14. Next Terminal B at 20:00.

### 20:00-23:00: one allowed and one denied path, then synthesis

```powershell
.\scripts\audit.ps1 -Last 30
```

Bash:
```bash
./scripts/audit.sh 30
```

Use a larger tail than the runbook's six records so the earlier allow is not
lost behind the attack denials. Select the allowed refund and a deny; do not
rerun refunds to populate the screen. Raw view if helpful:
`.\scripts\audit.ps1 -Last 30 -Raw` / `./scripts/audit.sh 30 --raw`.

**Action:** correlate trace/request -> pseudonymized user -> client -> resource
-> tool -> policy version -> rule -> result -> upstream/ledger effect.
**Expect:** the allowed path has an attributed validated identity; a
transport-rejected token has `identity_state: untrusted` and no attributed user.
**Why:** unvalidated claims are attacker-supplied strings, not identity facts.
**Evidence:** local structured records; if absent, slide 15 has selected,
explicitly RECORDED fields from `docs/APPENDIX.md` B (September 14, 2026).

Arguments use an allowlist. `_omitted_keys` names `idempotency_key`, never its
value. `client_approval_evidence: not-observable-by-server` does not prove a
dialog. JSONL is not immutable or tamper-proof. Skip KQL first; no successful
cloud telemetry execution was established here.

At ~21:00 switch to slide 4, then 5 at ~21:50, then 6 at ~22:35.
The remaining 25 seconds before Q&A are recovery allowance, not another
scripted speech. Hard stop for content 23:00.

### 23:00-25:00: questions

Keep slide 6 on screen. Answer from the control responsibilities, not product
claims. For a backup jump, enter the slide number then Enter in PowerPoint
Slide Show; return with `6` then Enter. Do not scroll the PDF through backups.
Hard stop at 25:00, including any last question.

## Coverage of the accepted proposal

| Promise | Main / demo / backup moment | Evidence source and qualification |
|---|---|---|
| PRM, AS discovery, PKCE, resource indicators, delegated scopes, audience-bound tokens | Main 3; 02:00-07:00; backup 7 | `scenarios.py` discovery/no-token; `tokens.py`; coverage matrix 1; expected trace, not rerun |
| Identity/scopes mapped to policy at tools/call | Main 2-4; 07:00-11:00; backup 8 | `mcp_server/app.py::_authorize`; `policy.py::evaluate`; configured policy version |
| Business argument and object validation | 07:00-11:00 and 15:00-18:00; backups 8/12 | `fixtures.py`; `policy.py` R003/R006/R200-R204 |
| Preserve human identity upstream | 11:00-15:00; backup 9 | `delegation.py`; `upstream_api/app.py`; new audience, no app-only fallback |
| Annotations help UI, not authorization | 11:00-15:00; backup 10 | Local tampering in `scenarios.py`; hints never sent as authorization |
| Client-owned approval for consequential action | Main 2/4; backup 10 | Manual checklist remains unfilled; explicit conceptual/client-only status |
| Prompt injection attempts unintended refund | 18:00-20:00; backups 13/14 | `ORD-1005` input; forced harness call on `ORD-1003`; no autonomy claim |
| Confused-deputy request | 16:30-18:00; backup 12 | Sam/Riley object mismatch; R006 before amount checks |
| Wrong-server token reuse | 15:00-16:30; backup 11 | B rejected at A; separate integration-test source asserts B acceptance; no same-token A/B capture |
| Audit ties request, identity, client, resource, policy and result | 20:00-21:00; backup 15 | Selected historical sanitized records from `APPENDIX.md` B; current `audit.py` field semantics |
| Attendee control map | Main 4 and 6; checklist 5/17 | Corrected responsibility map; no overclaim that every other layer belongs to another team |

## Source corrections and preparation items

The prompt's implementation-first rule takes precedence over stale narration:

- Actual scopes: `Refunds.Read` / `Refunds.Write`, not `refund.write`.
- Dana owns `ORD-1002` and has read scope only. Sam is refund-capable and owns
  `ORD-1001`, `ORD-1004`, `ORD-1005`. Riley owns `ORD-1003`.
- `scope-denial` uses Dana, not Sam; `ownership-denial` uses Sam against Riley's
  order, not Riley against another owner.
- Injection resides in `ORD-1005`, not the ineligible `ORD-1004`.
- The entry point is `policy.py::evaluate`, not prose references to `decide`.
- Annotation tampering is local; no authorization annotation is sent back.
- The scenario's replay result field is `idempotent_replay`, not a made-up
  `replayed=True` output field.
- The named wrong-audience scenario does not perform the B HTTP positive
  control. A separate integration test asserts it, using a separately acquired
  token; capture a continuous same-token trace before claiming that observation.
- A short six-record audit tail after all attacks may omit the allow. The
  guide uses 30, or the explicitly recorded slide, without changing the demo.
- A graceful offline fallback is not proof that a model was called. Filtering
  is distinct from a model-generated refusal and ordinary network failure.
- Records contain historical cloud teardown / left-running and date
  inconsistencies. No live status is inferred, and no live endpoint was queried.
- `APPENDIX.md`'s old allowed audit includes a development tenant label.
  Only safe selected fields are shown; tenant values are omitted from the slide.
  Only the subject is pseudonymized; validated `tenant_id` is retained as-is.
  Subject pseudonymization does not mean arbitrary logged text is secret-free.
- The accepted proposal's injection promise is covered as a forced harness
  attempt, not falsely claimed as a newly observed autonomous attack.

**Presenter-owned outstanding actions:** rehearse the 25-minute clock; confirm
the real client version/redirect and Cancel/Approve if using optional UI;
prepare a sanitized same-token-at-B HTTP control if claiming it live; verify
the actual demo baseline and offline behavior in a separate rehearsal; recheck
the room/time near the event. Do not silently turn historical records into a
fresh passing run.

## Static implementation inventory and assertion scope

`demo/src/refund_demo/scenarios.py::SCENARIOS` has **14 entries**, in this
CLI/UI order. These are source-derived expectations, not new executions:

| # | Scenario | Exact important input / expected boundary |
|---:|---|---|
| 1 | `no-token` | Unauthenticated `tools/list` at A; HTTP 401 and metadata challenge |
| 2 | `discovery` | Sam, `Refunds.Read Refunds.Write`; three tools listed |
| 3 | `missing-resource-indicator` | Missing resource; HTTP 400 / `invalid_target` |
| 4 | `pkce-downgrade` | `plain` PKCE; acquisition raises `ClientError` |
| 5 | `allowed-refund` | Sam, ORD-1001, 4000 minor units, identical retry; R299 |
| 6 | `scope-denial` | Dana, ORD-1002, 1000; R003 |
| 7 | `ownership-denial` | Sam, ORD-1003, 99000; R006 |
| 8 | `business-rule-denial` | Sam, ORD-1004, 1000; R200 |
| 9 | `over-limit-denial` | Sam, ORD-1001, configured limit + 1 (default 25001); R203 |
| 10 | `unapproved-client` | `unapproved-demo-client`, Sam, ORD-1001, 1000; R001 |
| 11 | `wrong-audience` | Sam's B token with `Probe.Read` at A's `tools/list`; HTTP 401 |
| 12 | `prompt-injection` | Assess ORD-1005; force ORD-1003 refund of 99000; R006 |
| 13 | `annotation-tampering` | Dana, ORD-1002, 500; locally changed hints; R003 |
| 14 | `token-passthrough-blocked` | A token at upstream `/refunds`, ORD-1001, 100; HTTP 401 |

Amounts are CAD integer minor units. Default per-call ceiling is 25000
(CAD 250.00); the downstream delegated scope is `Ledger.Refund`.
One scenario mutates the ledger once; **13 are expected not to mutate**.
That includes successful discovery; it is not thirteen denied calls.
The documentation's **207 tests** is a recorded count, not a new execution.

Assertion precision matters: no-token, discovery, missing-resource-indicator
and pkce-downgrade collect fingerprints but do not assert their equality in
their PASS predicates. Wrong-audience asserts HTTP 401, not the exact
`AUTH_WRONG_AUDIENCE` string. PKCE downgrade accepts any `ClientError`.
Read the actual reason and before/after evidence instead of treating a green
badge as proof of every narrated property.

Matching-resource evidence, inspected without running tests:

- `demo/tests/test_adversarial.py::test_token_minted_for_resource_b_is_rejected_at_resource_a`
  acquires a B token, sends it to A `tools/list`, asserts 401 and unchanged ledger.
- `demo/tests/test_adversarial.py::test_the_same_token_works_at_its_own_resource`
  independently acquires a **fresh** B token (`Probe.Read`), calls B's
  `probe_inventory`, and asserts no tool error. This is an HTTP/MCP integration
  assertion, not merely a validator unit test. The two tests do not share the
  same token instance. No test was run during generation.
- `demo/tests/test_tokens.py::test_a_resource_may_accept_several_identifiers_for_itself`
  directly checks A's validator with separately minted tokens for A's API URI
  or HTTP URL, and rejects B's audience. It is not B endpoint acceptance.

Additional drift avoided: briefings sometimes spell `Refund.Read` /
`Refund.Write` and say twelve untouched scenarios. The actual scopes are
plural and thirteen scenarios are expected not to mutate. Configuration's
unused adversarial-client default differs from the fixture/scenario:
the scenario uses `unapproved-demo-client`.

Browser details: audit has **Last 5** / **Last 20** buttons and does not refresh
automatically after each run. Click one explicitly. The visible header
**Reset** resets text size, not the ledger. **Run all 14** does not reset the
ledger, unlike the CLI full-sequence behavior. Repeated single allowed-refund
scenarios use new keys and can consume another 4000; only an identical
same-key retry is idempotent.

## Rebuild and local verification

From the repository root, this worktree's prepared isolated environment:

```powershell
.\.venv\Scripts\python.exe .\slides\gpt6-v1\build_deck.py
.\.venv\Scripts\python.exe .\slides\gpt6-v1\verify_deck.py --render
```

For another machine, create a dedicated presentation virtual environment,
install `requirements.lock.txt`, then run those scripts with that interpreter.
**Never install into `demo/.venv`.** Building requires Python and the declared
packages; PNG/PDF export additionally requires Windows desktop PowerPoint.
Omit `--render` for structural checks on a machine without PowerPoint.
Missing rendering is a verification gap, not a success-shaped fallback.
Do not overwrite someone else's deck: copy the source set to an adjacent
numbered revision first when preserving an earlier output.

`content.py` is the saved reviewed content snapshot; `guide_sections.py` stores
these operational instructions; `build_deck.py` saves both deck and guide.
No private chat, application import, live service or inference is needed.
The public repo link is embedded; rendering and reading the finished deck work
offline. QR navigation naturally requires a network only when the attendee
chooses to open the repository.

## Slide inventory and exact saved notes

Main slides are visible; slides 7-19 are hidden using the saved slide XML's
`show="0"` flag, checked again by desktop PowerPoint. Notes below are the actual
notes written into the PPTX, not an independent summary that can drift.

| Slide | Title / purpose | Visibility |
|---:|---|---|
| 1 | Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy | Main |
| 2 | Three different questions | Main |
| 3 | Follow the trust boundary | Main |
| 4 | Who enforces what? | Main |
| 5 | Three rules to take home | Main |
| 6 | Control map, resources, Q&A | Main |
| 7 | The authorization trace | Hidden backup |
| 8 | Policy at tools/call | Hidden backup |
| 9 | One refund. One ledger change. | Hidden backup |
| 10 | Hints and approval are not permission | Hidden backup |
| 11 | A genuine token can be wrong for you | Hidden backup |
| 12 | Do not become the confused deputy | Hidden backup |
| 13 | Force the call. Keep the boundary. | Hidden backup |
| 14 | Three assessment outcomes. One policy. | Hidden backup |
| 15 | Audit is evidence, not enforcement | Hidden backup |
| 16 | Run it four ways. Keep one policy. | Hidden backup |
| 17 | The rest of the seven-rule checklist | Hidden backup |
| 18 | What was recorded. What remains open. | Hidden backup |
| 19 | References for the next implementation | Hidden backup |

### Slide 1: Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy

**Projected text (including evidence labels):**

- Who Can Call / This MCP Tool?
- OAuth, Resource Binding, / and Runtime Policy
- Brian Benz / Principal AI Advocate, Microsoft
- MCP Dev Summit Toronto  |  October 6, 2026
- SYNTHETIC / REFUND
- User / + client / + order
- MCP DEV SUMMIT TORONTO 2026

**Saved speaker notes:**

00:00-00:25; segment hard stop 02:00. Next: slide 2.

Someone builds an MCP server with a refund_order tool. It works. Then someone asks: who can call it?

This is a synthetic refund ledger, not a payment provider. Today's question is whether this user, through this client, may act on this order with these arguments, right now.

The coding agent generating these slides uses GPT-6 Astra; it is not the Foundry backend described in the demo.

The talk is 25 minutes INCLUDING 23:00-25:00 Q&A. Generation time is a separate activity.

Source: Events/MCP-Dev-Summit-Toronto-2026-Approved-Proposals.md, accepted proposal; docs/ONSTAGE-SCRIPT.md 00:00-02:00; docs/RUNBOOK.md Segment 1.

Event logistics reconfirmed on the public schedule during generation: October 6, 2026, 15:40-16:05 EDT (UTC-4), Ballroom East/Center. Timing and room remain subject to change. Toronto is the first delivery, not a past performance.

Evidence: ILLUSTRATIVE native refund card, not a screenshot or an execution record. Fallback: use the PDF, page 1.

### Slide 2: Three different questions

**Projected text (including evidence labels):**

- Three different questions
- Authentication
- Who is calling? / Trusted identity
- Approval
- Did the human intend it? / Client-owned choice
- Authorization
- May this principal / act on this object / right now?
- MCP DEV SUMMIT TORONTO 2026

**Saved speaker notes:**

00:25-01:05; segment hard stop 02:00. Next: slide 3.

The user signed in. There is an approval dialog. The server is internal. Those are real things, but none is the object authorization decision.

Authentication, approval, and authorization are three different questions. The authorization server supports trusted identity and token issuance; the client owns approval; the MCP server must decide whether this action on this object is allowed now.

A team may own the authorization server AND the upstream API. The ownership point is responsibility, not an assertion that every other component belongs to somebody else.

Human approval cannot replace server authorization. Nobody answers the object/tool question unless the service implements it.

Source: docs/ONSTAGE-SCRIPT.md opening; docs/CONTROL-MAP.md Layers 1-4; accepted proposal.

Evidence: ILLUSTRATIVE responsibility map. Fallback: PDF page 2. Do not claim a client dialog was observed during slide generation.

### Slide 3: Follow the trust boundary

**Projected text (including evidence labels):**

- Follow the trust boundary
- MCP client / Approval + / client model
- Authorization server
- MCP Resource A / Token checks + policy
- Upstream API / Independent rechecks
- Synthetic ledger
- Foundry: advice only
- OAuth
- tools/call
- Exchange
- Delegated token
- Mutation
- Advisory
- RED, LABELED: UNTRUSTED CLIENT / MODEL INPUT

**Saved speaker notes:**

01:05-02:00; hard stop 02:00. Next window: Terminal A in demo; leave the deck here until the closing synthesis.

The MCP client can have its own model. The Foundry assessment model is a DIFFERENT actor, reached through assess_refund. The scenario runner is an operator/reporting surface, not either model and not the policy engine.

OAuth links the client to the authorization server. Protected Resource Metadata and AS metadata lead to PKCE S256 and resource indicators. The AS issues a token, not an order-level permission.

The client sends tools/call to Resource A. A validates the token and evaluates deterministic policy. On an allowed refund, A exchanges for a new token to the upstream API; the upstream independently rechecks and mutates the ledger. No arrow from model output grants authority or writes to the ledger.

The Foundry branch is dashed and explicitly advisory. A separate platform content filter can act in the inference service; it is neither MCP authorization nor a model-generated refusal.

Every scenario captures before/after ledger fingerprints; most denial scenarios assert equality. Read the actual before/after evidence rather than treating every PASS badge as an equality assertion.

This is a simplified editable schematic, not a captured execution trace. It omits return arrows and puts the detailed B-resource comparison and delegated audiences in backups 9 and 11.

Source: docs/CONTROL-MAP.md diagram (corrected ownership/filter semantics); demo/src/refund_demo/mcp_server/app.py::_authorize, assess_refund, refund_order; delegation.py; upstream_api/app.py.

Fallback: PDF page 3. If all terminals are unavailable, narrate backup slides 7-15 with EXPECTED / ILLUSTRATIVE labels, using the original segment budgets.

### Slide 4: Who enforces what?

**Projected text (including evidence labels):**

- Who enforces what?
- Client
- Human approval
- Not server permission
- Authorization server
- Identity + audience
- Not object policy
- MCP server
- Tool + object policy
- Must decide at call time
- Upstream API
- Mutation checks
- No token passthrough
- Model
- Advice only
- Never grants authority
- Platform filtering is separate from authorization.
- MCP DEV SUMMIT TORONTO 2026

**Saved speaker notes:**

Approximately 21:00-21:50, AFTER the 20:00-21:00 audit walkthrough. Segment hard stop 23:00. Next: slide 5.

Five responsibilities, not five substitutes for the same control. The client can stop a call the human cancels, but its UI is not server permission. The AS authenticates and issues an audience-bound token; it does not know the current business state of this order.

The MCP server owns the tool/object decision at tools/call. The upstream service must recheck before mutation. A team may operate both services and the AS; the responsibilities remain separate.

The model provides advice and cannot widen permission. Platform content filtering is an additional, separate outcome; it is not the object authorization boundary.

Only the principal your server decided may call it, on the object it decided they may touch, at the moment they asked.

Source: docs/CONTROL-MAP.md Layers 1-5b; docs/ONSTAGE-SCRIPT.md 20:00-23:00; policy.py::evaluate; upstream_api/app.py.

Evidence: ILLUSTRATIVE control map following actual local audit if the presenter ran it. If using the recorded audit instead, identify docs/APPENDIX.md B (2026-09-14), not today's run. Fallback: PDF page 4.

### Slide 5: Three rules to take home

**Projected text (including evidence labels):**

- Three rules to take home
- 1
- Bind tokens to resources.
- Check the audience at each service.
- 2
- Scopes are verbs, not objects.
- Check ownership and business state.
- 3
- Assume Approve was clicked.
- Decide on the server anyway.
- MCP DEV SUMMIT TORONTO 2026

**Saved speaker notes:**

Approximately 21:50-22:35. Segment hard stop 23:00. Next: slide 6, which stays up through Q&A.

Bind every token to one resource. Scopes are verbs, not objects. Assume Approve was clicked and decide anyway.

The actual scope names here are Refunds.Read and Refunds.Write, case-sensitive. Refunds.Write never named ORD-1003. Sam's token can have the verb while the order belongs to Riley.

The full seven-rule checklist is: (1) bind tokens to resources and check arrival; (2) check object ownership as well as scopes; (3) approval does not replace authorization; (4) never forward the incoming token downstream: exchange it, and if the exchange fails, fail with no app-only fallback; (5) annotations are hints, not permission; (6) model output is advice on untrusted input and never widens authority; (7) audit at the decision point including denials, pseudonymize identity, and deny by default.

The remaining four rules are readable on backup 17. Do not read seven paragraphs aloud now.

Source: docs/CONTROL-MAP.md Take this home, with scope spelling corrected from implementation; docs/ONSTAGE-SCRIPT.md closing.

Evidence: ILLUSTRATIVE synthesis. Fallback: PDF page 5.

### Slide 6: Control map, resources, Q&A

**Projected text (including evidence labels):**

- Control map, resources, Q&A
- Client
- Human approval
- Authorization server
- Identity + audience
- MCP server
- Tool + object policy
- Upstream API
- Mutation checks
- Model
- Advice only
- Code + / control map
- github.com/bbenz/mcp-tool-calling
- QUESTIONS 23:00-25:00  |  HARD STOP 25:00

**Saved speaker notes:**

22:35-25:00. Finish the close by 23:00; reserve 23:00-25:00 for questions. Next window: none. Keep this control map visible; do not automatically advance into hidden slides.

The repository was confirmed PUBLIC via gh repo view during generation. The displayed URL and QR both point to https://github.com/bbenz/mcp-tool-calling. The local generated deck has NOT been committed or published; the QR links to existing repository sources, not a claim that these new slides are online.

If asked why scopes are insufficient: a scope names a class of actions, not an order. Sam has Refunds.Write but cannot act on Riley's ORD-1003 (R006).

If asked why approval is insufficient: the UI answers human intent and can be bypassed; server policy still decides. The current manual checklist has no completed client-version evidence.

If asked why not forward the token: it is for a different audience. Exchange for api://refund-upstream, preserve the human, fail closed.

If asked about logs: JSONL is structured application evidence, not immutable or tamper-proof storage.

If asked about production identity: devidp is a development AS. Entra mode, cluster workload identity, the separate Bicep deployment, and cloud KQL execution are not established by the recorded AKS and model rehearsals.

Source: docs/RUNBOOK.md Q&A (corrected fixture identities and scope names); docs/CONTROL-MAP.md; docs/COMPATIBILITY-RECORD.md; docs/DEPLOYMENT.md.

Fallback: PDF page 6. Backup navigation: 7 OAuth; 8 policy; 9 delegation; 10 approval; 11 audience; 12 deputy; 13 injection; 14 model outcomes; 15 audit; 16 hosting; 17 checklist; 18 limits; 19 references. Jump by number plus Enter in PowerPoint Slide Show, then 6 plus Enter to return. Backup time is taken from the relevant existing segment, not added.

### Slide 7: The authorization trace

**Projected text (including evidence labels):**

- The authorization trace
- 1
- No token -> HTTP 401
- WWW-Authenticate points to resource metadata
- 2
- Discover the endpoints
- Protected Resource Metadata -> AS metadata
- 3
- Bind the authorization
- PKCE S256 + resource in both requests
- 4
- Validate, then call
- Trusted keys, issuer, audience, lifetime, identity
- BACKUP  |  EXPECTED TRACE - NOT A NEW CAPTURE

**Saved speaker notes:**

BACKUP for 02:00-07:00; hard stop 07:00. Return to Terminal A; if terminals are lost, next backup 8. Never add time for this slide.

PowerShell in demo: .\scripts\scenario.ps1 no-token ; .\scripts\scenario.ps1 discovery

Bash twins: ./scripts/scenario.sh no-token ; ./scripts/scenario.sh discovery

Browser alternative: in the already-running local UI select Run for no-token, then discovery. Expand one Sends / Expects / Why briefing if useful; keep the others collapsed.

Send -> expect -> why -> evidence: no-token sends an unauthenticated request to A; expect HTTP 401 and WWW-Authenticate naming resource_metadata. Discovery fetches Protected Resource Metadata, AS discovery, runs authorization-code flow with code_challenge_method=S256, and supplies resource=api://refund-mcp-a in BOTH authorization and token requests. Observe requested versus granted delegated scopes; Dana's scope is Refunds.Read, Sam's include Refunds.Read and Refunds.Write. Only safe names and sanitized claims belong in view: iss, aud, sub, tid, client, exp. Never display token/code/verifier values.

No token issues: optional .\scripts\scenario.ps1 missing-resource-indicator and .\scripts\scenario.ps1 pkce-downgrade (bash uses the same names with ./scripts/scenario.sh). AS rejects missing resource or plain PKCE; no token is issued.

Decoding is not validating: trusted issuer JWKS, allowed RSA algorithms, signature, issuer, audience, tenant where configured, lifetime, token type and delegated human identity are checked. User identity is never accepted from tool arguments.

The local accepted audience identifiers are configuration-specific; api://refund-mcp-a and the configured HTTP resource URL can identify A. Do not imply that every OAuth resource uses this exact convention.

Resource binding stops cross-resource reuse, NOT replay of a stolen bearer token at its intended resource.

Source: docs/COVERAGE-MATRIX.md 1.1-1.10; client.py::acquire_token/discover (as mapped by coverage); tokens.py::TokenValidator; scenarios.py no-token/discovery; scripts/scenario.ps1 and scenario.sh. Public references: RFC 9728, RFC 8414, RFC 7636, RFC 8707.

Evidence status: EXPECTED / ILLUSTRATIVE until the presenter executes the prepared trace. No new application execution occurred during generation. If interactive sign-in stalls beyond 20 seconds, skip that optional depth, not protocol coverage.

### Slide 8: Policy at tools/call

**Projected text (including evidence labels):**

- Policy at tools/call
- Token validation precedes policy.evaluate.
- Dana: missing Refunds.Write
- R003 / POLICY_MISSING_SCOPE
- Sam: ineligible ORD-1004
- R200 / POLICY_ORDER_NOT_REFUNDABLE
- Sam: above per-call ceiling
- R203 / amount exceeds per-call limit
- Unapproved client
- R001 / POLICY_CLIENT_NOT_ALLOWED
- BACKUP  |  EXPECTED DENIALS; LEDGER UNCHANGED

**Saved speaker notes:**

BACKUP for 07:00-11:00; hard stop 11:00. Return to Terminal A / Editor; if no terminals, next backup 10 then 9 for segment 4.

Core commands in demo: .\scripts\scenario.ps1 scope-denial ; .\scripts\scenario.ps1 business-rule-denial

Bash: ./scripts/scenario.sh scope-denial ; ./scripts/scenario.sh business-rule-denial

Browser: Run those named scenarios; it reports the server's decision, never its own authorization.

Read/assessment depth: in a preconfigured live client signed in as Sam, ask 'Show me order ORD-1001', then 'Assess whether order ORD-1001 should be refunded, and show the assessment.' get_order and assess_refund need Refunds.Read and object ownership. This is optional client interaction, NOT an invented assess-refund scenario. If the client is unavailable, explain the functions from this slide/code without manufacturing a run.

scope-denial: Dana reads her ORD-1002, sees the listed tools, then calls refund_order without Refunds.Write. Expect POLICY_MISSING_SCOPE, R003; ledger unchanged.

business-rule-denial: Sam requests a refund on owned but ineligible ORD-1004. Expect POLICY_ORDER_NOT_REFUNDABLE, R200; ledger unchanged.

Optional .\scripts\scenario.ps1 over-limit-denial and .\scripts\scenario.ps1 unapproved-client (same scenario names through ./scripts/scenario.sh). Expect POLICY_AMOUNT_EXCEEDS_PER_CALL_LIMIT / R203 and POLICY_CLIENT_NOT_ALLOWED / R001.

Locate demo/src/refund_demo/policy.py::evaluate, not the stale docs' decide symbol. Policy version: refund-policy/2026-10-06.1. Checks include approved client, known tool, exact delegated scope, known principal, order existence, ownership; then refund eligibility, integer-positive amount, currency, per-call ceiling and balance. Read/advice allow is R100; refund allow is R299. Deny by default. Every tool invokes authorization; tools/list, hints, schemas and user-supplied identity are not permission.

These are tool/business denials with a reason code, not the transport HTTP 401 from slide 7. An expected denial can be PASS because the security expectation held, NOT because a refund succeeded.

Source: policy.py::evaluate; config.py policy_version; fixtures.py; mcp_server/app.py::_authorize; scenarios.py; docs/COVERAGE-MATRIX.md section 2. Evidence: EXPECTED / ILLUSTRATIVE, not fresh test output.

### Slide 9: One refund. One ledger change.

**Projected text (including evidence labels):**

- One refund. One ledger change.
- Sam  |  ORD-1001  |  CAD 40.00 = 4000 minor units
- Before
- 0 minor units
- First call
- 4000 / Replay: false
- Same-key retry
- 4000 / Replay: true
- New downstream audience. Same human. No app-only fallback.
- BACKUP  |  EXPECTED FROM A CLEAN SYNTHETIC LEDGER

**Saved speaker notes:**

BACKUP for 11:00-15:00; hard stop 15:00. Return to Terminal A; if no terminals, next backup 11 at 15:00.

In demo: .\scripts\scenario.ps1 allowed-refund

Bash: ./scripts/scenario.sh allowed-refund

Browser: Run allowed-refund once against the already-prepared local services.

Send: Sam calls refund_order for ORD-1001 with amount_minor=4000 and currency=CAD, then repeats EXACTLY the same request and idempotency key. Do not print an idempotency-key value.

Expect: idempotent_replay=false then true, delegated_identity_preserved=true, upstream_audience=api://refund-upstream. Total rises by 4000 ONCE. The projected 0 -> 4000 -> 4000 assumes a clean ledger; otherwise explain the actual baseline and delta, not an invented zero.

Why: A first evaluates R299/ALLOW, then exchanges its incoming audience-bound token for a NEW downstream token carrying the SAME human. Upstream validates its own audience/scope and rechecks object/business rules. Atomic ledger/idempotency enforcement prevents an identical retry from applying again; an idempotency key is bound to its original request.

Never forward an incoming token downstream. Exchange it - and if the exchange fails, fail. No application-only fallback. Workload identity for calling Foundry is a different concern from delegated user identity.

Optional negative control: .\scripts\scenario.ps1 token-passthrough-blocked ; bash ./scripts/scenario.sh token-passthrough-blocked. A token with aud=api://refund-mcp-a sent directly to upstream must get HTTP 401, AUTH_WRONG_AUDIENCE; ledger unchanged.

The exchange uses the local jwt-bearer profile in devidp, and the implementation has an Entra MSAL OBO path that has not been executed according to the records. Do not call the local flow a verified Entra integration.

Source: scenarios.py allowed-refund/token-passthrough-blocked; delegation.py::exchange_for_upstream; upstream_api/app.py; fixtures.py; docs/COVERAGE-MATRIX.md 2.9 and section 3. Public references: RFC 7523; Microsoft identity platform OBO.

Evidence: EXPECTED / ILLUSTRATIVE ledger values. Historical applied/replayed records are in docs/APPENDIX.md B, dated 2026-09-14. No synthetic PASS badge, new timestamp, refund ID or measured latency is fabricated here.

### Slide 10: Hints and approval are not permission

**Projected text (including evidence labels):**

- Hints and approval are not permission
- Client-owned
- Annotations guide a UI. / Cancel stops sending. / Approve permits sending.
- Server-owned
- Validate the token. / Evaluate object policy. / Deny even after approval.
- Annotation tampering -> R003 / POLICY_MISSING_SCOPE
- BACKUP  |  CLIENT BEHAVIOR IS NOT SERVER EVIDENCE

**Saved speaker notes:**

BACKUP for 11:00-15:00; hard stop 15:00. Next: allowed-refund in Terminal A or backup 9.

In demo: .\scripts\scenario.ps1 annotation-tampering ; bash ./scripts/scenario.sh annotation-tampering. Browser: Run annotation-tampering.

Send: the scenario rewrites the local client-side hints for refund_order, including readOnlyHint. They are NOT sent back as authorization fields in tools/call. Dana then calls refund_order on ORD-1002 without Refunds.Write.

Expect: POLICY_MISSING_SCOPE / R003, unchanged ledger. Why: policy reads validated identity, scopes and authoritative object state, not the client's local annotation display.

get_order is read-only. refund_order is destructive and idempotent, with readOnlyHint false. Annotations are hints from a process you do not control. They are documentation, not permission.

Optional live-client depth ONLY after rehearsal: use Sam with the exact owned-order refund arguments and a stable same-request idempotency key; observe the real client dialog, Cancel, then request again and Approve. Cancel should prevent sending, with no refund audit record and no mutation; this is CLIENT-ONLY evidence, not a server rejection. A ledger check alone cannot establish a dialog appeared.

For an approved-but-denied example, use Dana on ORD-1002 (R003), or Sam on Riley's ORD-1003 (R006). The old manual checklist swaps these identities; do not copy it verbatim. No completed client-version/date record exists in the supplied checklist.

If the UI is not rehearsed, skip the dialog and state its intended semantics. Run over-limit-denial as a SERVER negative control, not proof that a human approved. The browser demo's Run button is NOT an MCP approval dialog.

Source: mcp_server/app.py tool annotations; scenarios.py annotation-tampering; policy.py::evaluate; docs/CLIENT-APPROVAL-CHECKLIST.md B/C with corrected fixtures; docs/ONSTAGE-SCRIPT.md 11:00-15:00 with corrected annotation semantics.

Evidence: EXPECTED / ILLUSTRATIVE; no manufactured client screenshot or signed approval receipt.

### Slide 11: A genuine token can be wrong for you

**Projected text (including evidence labels):**

- A genuine token can be wrong for you
- Token intended for B
- aud: / api://refund-mcp-b / Presented to Resource A
- A rejects before dispatch
- HTTP 401 / AUTH_WRONG_AUDIENCE / Ledger unchanged
- B-token acceptance: integration-test assertion, not rerun here.
- BACKUP  |  EXPECTED EXCHANGE; CONTROL STATUS IN NOTES

**Saved speaker notes:**

BACKUP for 15:00-16:30; segment hard stop 20:00. Next: ownership-denial in Terminal A or backup 12.

In demo: .\scripts\scenario.ps1 wrong-audience ; bash ./scripts/scenario.sh wrong-audience. Browser: Run wrong-audience.

Send: acquire a token for Resource B, api://refund-mcp-b, then present it to Resource A, api://refund-mcp-a.

Expect: HTTP 401 before tool execution and AUTH_WRONG_AUDIENCE in the audited rejection path, ledger unchanged. A signature check is not an audience check.

The named scenario does NOT make a successful authenticated request to Resource B. Do not narrate that wrong-audience printed a B success.

Matching-resource acceptance is asserted by demo/tests/test_adversarial.py::test_the_same_token_works_at_its_own_resource: it acquires a fresh Sam token for B with Probe.Read, calls probe_inventory at B, and asserts no tool error. This is HTTP/MCP integration-test SOURCE, not a test executed during generation. Despite its name, it does not reuse the token from test_token_minted_for_resource_b_is_rejected_at_resource_a; those are separate tests with separately acquired tokens. A continuous SAME-token A/B demonstration remains EXPECTED CONTROL - NOT CAPTURED.

Separately, demo/tests/test_tokens.py::test_a_resource_may_accept_several_identifiers_for_itself is validator-level coverage for A's API identifier or configured HTTP URL, NOT B endpoint acceptance.

Resource binding prevents cross-resource reuse, not replay of a stolen bearer token at its intended service. A and B are distinct resources; this implementation may accept both the configured App ID URI and HTTP URL for the SAME resource, not arbitrary audiences.

Source: scenarios.py wrong-audience; tokens.py::TokenValidator; config.py audiences; docs/COVERAGE-MATRIX.md 1.9 and 5.5 (corrected evidence scope); docs/APPENDIX.md B rejected-token record.

Evidence: EXPECTED / ILLUSTRATIVE for the A-rejection exchange; STATIC INTEGRATION-TEST ASSERTION for B acceptance, not rerun here. The recorded sanitized transport denial on backup 15 is historical, not the missing same-token A/B capture. Presenter action: capture and sanitize that continuous control during a separate rehearsal if a live same-token acceptance claim is desired.

### Slide 12: Do not become the confused deputy

**Projected text (including evidence labels):**

- Do not become the confused deputy
- Sam asks
- Has Refunds.Write. / Targets Riley's ORD-1003. / amount_minor=99000
- Resource A decides
- R006 / POLICY_ORDER_NOT_ASSIGNED / Ledger unchanged
- Ownership is checked BEFORE the amount ceiling.
- BACKUP  |  EXPECTED DENIAL; NOT A CAPTURED RUN

**Saved speaker notes:**

BACKUP for 16:30-18:00; hard stop 20:00. Next: prompt-injection in Terminal A or backup 13.

In demo: .\scripts\scenario.ps1 ownership-denial ; bash ./scripts/scenario.sh ownership-denial. Browser: Run ownership-denial.

Send: Sam, a refund-capable caller with Refunds.Write, requests 99000 minor units on ORD-1003. That order belongs to Riley, NOT Sam.

Expect: POLICY_ORDER_NOT_ASSIGNED, R006, ledger digest unchanged. Ownership precedes the amount ceiling; do not call this the over-limit test just because 99000 exceeds Sam's limit.

Name the deputy: the MCP server can reach the upstream refund capability. Name the mismatch: its ability to invoke that capability must not become authority for Sam to touch Riley's object. A scope describes what kind of action Sam may perform; it never identifies every object Sam may act on.

The upstream still needs its own delegated token and independent checks. The server does not solve this by trusting a user_id argument, a model suggestion, a client dialog, or a broad service token.

Source: fixtures.py employees/orders; policy.py::evaluate R006; scenarios.py ownership-denial; docs/ONSTAGE-SCRIPT.md deputy segment with corrected identity, object ownership, and scope spelling.

Evidence: EXPECTED / ILLUSTRATIVE. If showing a previous run, identify that transcript and its date; no previous run transcript is invented here.

### Slide 13: Force the call. Keep the boundary.

**Projected text (including evidence labels):**

- Force the call. Keep the boundary.
- 1
- Untrusted input
- ORD-1005: attacker-written notes
- 2
- Advisory assessment
- Model / filter / offline outcome is reported
- 3
- Forced harness call
- Sam -> ORD-1003, amount_minor=99000
- 4
- Deterministic boundary
- R006 denies; ledger remains unchanged
- BACKUP  |  FORCED HARNESS REPLAY - NOT MODEL AUTONOMY

**Saved speaker notes:**

BACKUP for 18:00-20:00; hard stop 20:00. Next window: Terminal B audit; if unavailable, backup 15.

In demo: .\scripts\scenario.ps1 prompt-injection ; bash ./scripts/scenario.sh prompt-injection. Browser: Run prompt-injection.

Send: Sam assesses ORD-1005, whose free-text notes contain synthetic attacker-written instructions. Then the HARNESS explicitly calls refund_order against Riley's ORD-1003 for amount_minor=99000. The hostile notes are in ORD-1005, not ORD-1004.

Expect: the assessment reports its actual mode, then the forced refund gets POLICY_ORDER_NOT_ASSIGNED / R006 and the ledger remains unchanged.

This is a forced harness replay, not evidence that an autonomous model selected or executed an unintended tool. It exercises the attempted redirection described in the proposal without inventing model behavior.

If a model's refusal is your security boundary, your security boundary is a probability distribution. The deterministic boundary is policy.py::evaluate. Advice cannot expand a principal's objects, scopes or limits.

If filtered, say PLATFORM content filter, not model refusal. If offline, read the offline label. If a model actually answered, describe that observed advice without granting it authority. Backup 14 separates these outcomes.

A configured remote call can wait through failure/retry before fallback; do not promise an instant return. If behind, switch to this explicitly illustrative slide rather than sacrificing the audience or deputy lessons.

Source: fixtures.py injected ORD-1005; scenarios.py prompt-injection; foundry.py; policy.py::evaluate R006; docs/EVENTS.md live model rehearsal.

Evidence: EXPECTED / ILLUSTRATIVE until presenter execution. No hostile payload is reproduced, no fresh model attack is asserted, and no fabricated platform-filter result is displayed.

### Slide 14: Three assessment outcomes. One policy.

**Projected text (including evidence labels):**

- Three assessment outcomes. One policy.
- Model answered
- live: true / Advisory text only
- Platform filtered
- filtered: true / live: false / Not model refusal
- Offline assessment
- live: false / Explicit offline label / No generated advice
- BACKUP  |  MODES, NOT THREE NEW INFERENCE RESULTS

**Saved speaker notes:**

BACKUP depth inside 07:00-11:00 or 18:00-20:00, NEVER extra time. Return to Terminal A; if the hard stop arrives, next audit / slide 4.

assess_refund can produce live advisory text, report a platform content-filter result, or return an explicitly labeled offline assessment. filtered:true can coexist with live:false because no model-generated advice was returned. live:false alone does not distinguish filtering from offline fallback.

Offline content includes [OFFLINE ASSESSMENT - NO MODEL WAS CALLED]. For a configured failure this identifies the local fallback text, not proof that no network attempt happened; do not promise instantaneous network fallback.

The platform's filtering behavior was recorded on the local and AKS rehearsals; it is not guaranteed to catch future injection. It is neither the app's deterministic policy nor an MCP authorization feature.

The recorded backend deployment name is gpt-5.6-sol. This is not the GPT-6 Astra coding agent and not a requirement that all deployments use that model name.

The cluster's recorded Foundry authentication used an API key in a Kubernetes Secret supplied only to mcp-a. No values appear in this deck. This was NOT a verified workload-identity deployment.

In every outcome, the authorization boundary is unchanged. The policy does not use model output as a capability or approval.

Source: foundry.py assessment helpers; scenarios.py prompt-injection evidence; docs/EVENTS.md 2026-09-16 live model rehearsal and cloud model rehearsal; docs/COMPATIBILITY-RECORD.md section 4; docs/DEPLOYMENT.md section 7.

Evidence: ILLUSTRATIVE mode comparison backed by static implementation and dated recorded findings, not new inference. Do not invent token counts, latency, or a new timestamp.

### Slide 15: Audit is evidence, not enforcement

**Projected text (including evidence labels):**

- Audit is evidence, not enforcement
- Allowed refund
- identity_state: validated / policy_rule_id: R299 / decision: allow / upstream_status: 201 / ledger_changed: true
- Rejected token
- identity_state: untrusted / reason: wrong audience / decision: deny / No user attributed / ledger_changed: false
- Request -> user -> client -> resource -> policy -> result
- RECORDED EXCERPTS  |  docs/APPENDIX.md B  |  2026-09-14

**Saved speaker notes:**

BACKUP for 20:00-21:00; segment hard stop 23:00. Next: slide 4 at approximately 21:00.

Primary operator action in demo: .\scripts\audit.ps1 -Last 30

Bash: ./scripts/audit.sh 30

The runbook says -Last 6, but a short tail after three attacks may omit the allowed refund. Use 30 and locate one allowed refund and one deny without rerunning scenarios. For raw JSON, .\scripts\audit.ps1 -Last 30 -Raw ; bash ./scripts/audit.sh 30 --raw.

Browser alternative: click Last 20 in the already-running UI's Audit trail (it does not automatically refresh after a scenario). A short tail may omit the allow; fall back to this recorded comparison rather than mutating the ledger.

The slide is a selected-field, human-readable excerpt from docs/APPENDIX.md B, recorded 2026-09-14: allowed at 19:34:04.230+00:00; rejected token at 19:43:43.207+00:00. 'reason: wrong audience' is a display paraphrase of reason_code AUTH_WRONG_AUDIENCE, not a renamed JSON field. It is NOT today's run. It does not show a policy denial attributed to a validated user; the right side is a TRANSPORT rejection.

Follow trace_id -> mcp_request_id -> user_pseudonym -> client_id -> resource_audience -> tool -> policy_version -> policy_rule_id -> decision/reason_code -> upstream_outcome -> ledger_changed. The user subject is pseudonymized; validated tenant_id is retained as-is. The older example contains a development tenant label; this slide omits tenant values entirely. Do not infer universal sanitization of arbitrary argument or outcome text, and do not project raw identity strings.

For rejected tokens, identity_state is untrusted; user/tenant/issuer/client remain empty. Unvalidated claims are attacker-supplied data, not a trusted identity. There is no policy rule ID on a transport rejection.

Arguments are allowlisted; _omitted_keys names idempotency_key without exposing its value. client_approval_evidence is not-observable-by-server, not proof of a human dialog.

The recorded retry at 19:34:07.080+00:00 has upstream_status 200, upstream_outcome replayed, ledger_changed false. A distinct request does not imply a second movement.

This is a JSONL application log on disk, NOT immutable and NOT tamper-proof. Append-only storage and independent retention are separate production work. Cloud Application Insights/KQL is optional and not verified by this deck.

Source: docs/APPENDIX.md B (explicit provenance); audit.py record helpers; docs/ONSTAGE-SCRIPT.md evidence; docs/COVERAGE-MATRIX.md section 6.

Evidence: RECORDED, selected fields. If reading live records, switch narration to LIVE only after actual presenter execution.

### Slide 16: Run it four ways. Keep one policy.

**Projected text (including evidence labels):**

- Run it four ways. Keep one policy.
- 1  Local scripts
- PowerShell is the stage default. / Bash twins are available.
- 2  Scripts + browser UI
- Run -> result -> ledger -> audit / Reporting, not authorization.
- 3  Docker Compose
- Five local containers. / Recorded rehearsal, not rerun.
- 4  AKS
- Recorded cloud rehearsal. / Not a production template.
- BACKUP  |  HOSTING OPTIONS - NOT A DEPLOYMENT TUTORIAL

**Saved speaker notes:**

BACKUP for Q&A within 23:00-25:00; no extra time. Return to slide 6.

The primary plan remains local PowerShell. All operator terminals start in demo. Bash uses actual .sh twins, not PowerShell scripts.

The optional FastAPI web UI wraps scenarios.run_one and shows results, ledger fingerprint and audit. It is not the policy engine, a real MCP client approval UI, or evidence that a model chose a tool. The row 'Run -> result -> ledger -> audit' is a labeled workflow schematic, not a screenshot.

Before projection, use the page header A-/A+ controls (or + / - / 0) to size it for the back row. Keep About this demo and scenario Sends / Expects / Why expanders collapsed; brief one when it helps. Do not launch the UI during slide generation.

Operator setup commands exist as .\scripts\web.ps1 and ./scripts/web.sh for an already-prepared demo. Normal local URL is http://localhost:8080; never project a live cloud address or access-bearing URL. The guide lists scenario-run actions, not a cloud deployment tutorial.

Compose and AKS are documented recorded options, not the default for Toronto. Records describe five containers; the four internal services plus browser reporting surface are different from the four local core processes.

The recorded public cloud deployment used plain HTTP and a shared demo access key. It is not a production security reference. No live address, key, endpoint value, or secret is reproduced. Current deployment state was NOT inspected.

Do not equate the recorded AKS path with the separate unexecuted Bicep artifact, Entra authentication, or Foundry workload identity.

Source: docs/DEPLOYMENT.md modes 1-4 and sections 7-8; docs/SETUP.md; web/app.py reporting path; briefings.py; docs/EVENTS.md recorded rehearsals.

Evidence: ILLUSTRATIVE hosting map; historical hosting findings only. No services, scenarios, deployments or inference were run to build the presentation.

### Slide 17: The rest of the seven-rule checklist

**Projected text (including evidence labels):**

- The rest of the seven-rule checklist
- 1
- Exchange downstream tokens
- Preserve the human; fail closed.
- 2
- Treat annotations as hints
- Documentation does not grant permission.
- 3
- Keep advice non-authoritative
- Untrusted text cannot widen authorization.
- 4
- Audit where you decide
- Include denials; pseudonymize; deny by default.
- BACKUP  |  COMPLEMENTS THE THREE RULES ON SLIDE 5

**Saved speaker notes:**

BACKUP inside closing/Q&A, hard stop 25:00. Return to slide 6.

Slide 5 carries rules 1-3: resource binding; scopes plus object checks; server decisions despite approval. This slide carries rules 4-7, kept separate for readable projection.

4. Never forward the incoming MCP token downstream. Exchange for the upstream audience, preserving the user; on failure do not fall back to application-only authority.

5. Annotations are hints for the client UI, not trusted policy inputs. The scenario's local tampering is not sent back as authorization.

6. Model output is advice about untrusted input. It may inform a human, never widen scopes, objects, or business limits.

7. Write the audit record at the decision point, including denials. Pseudonymize identity and allowlist arguments. A tool without an explicit policy rule is denied, not implicitly allowed.

Source: docs/CONTROL-MAP.md Take this home, with actual scopes Refunds.Read / Refunds.Write from implementation. Evidence: ILLUSTRATIVE checklist. No new execution claimed.

### Slide 18: What was recorded. What remains open.

**Projected text (including evidence labels):**

- What was recorded. What remains open.
- Recorded rehearsals
- Local scripts + browser / Compose + AKS / Live Foundry advice / Platform filtering
- Not established
- Entra authentication / AKS workload identity / Separate Bicep deployment / Live client approval / KQL
- No tamper-proof log, stolen-token replay defense, or production claim.
- BACKUP  |  HISTORICAL VERIFICATION IS NOT A NEW RUN

**Saved speaker notes:**

BACKUP for Q&A, hard stop 25:00. Return to slide 6.

Recorded findings are attributed to docs/COMPATIBILITY-RECORD.md (initial record 2026-09-14, later additions) and docs/EVENTS.md / DEPLOYMENT.md September 15-16 rehearsal descriptions. These records report local scripts, browser API, Compose and AKS scenarios, live Foundry advice and content-filter handling. The records contain chronology/teardown-versus-left-running inconsistencies; do not infer today's cluster state from them.

Static inventory contains 14 scenario entries. Documentation reports 207 automated tests as historical execution, NOT a newly executed suite. No test count is projected as today's result.

Not established: AUTH_MODE=entra; cluster workload identity for Foundry (recorded AKS used an API key); the separate demo/infra Bicep deployment; bash AKS deployment end-to-end; exact live client redirect/version and completed approval checklist; successful current Application Insights/KQL run. A compiling template, SDK support or a checklist is not execution evidence.

No claim of tamper-proof JSONL, stolen-token replay prevention at the intended resource, universal filter reliability, production multi-tenant isolation, or client approval attestation. Resource binding handles the different-resource reuse problem, not all bearer-token theft.

devidp is a development identity service, not production authentication. Public AKS rehearsal used shared-key plain HTTP; never copy its endpoint or key into public materials.

Source: docs/COMPATIBILITY-RECORD.md section 4; docs/DEPLOYMENT.md 7-8; docs/EVENTS.md rehearsals; docs/CLIENT-APPROVAL-CHECKLIST.md unfilled record; docs/APPENDIX.md E.

Evidence: RECORDED FINDINGS / UNVERIFIED ITEMS, explicitly not fresh runtime status.

### Slide 19: References for the next implementation

**Projected text (including evidence labels):**

- References for the next implementation
- 1
- MCP authorization
- Protected resources and security boundaries
- 2
- Discovery + PKCE
- RFC 9728 / RFC 8414 / RFC 7636
- 3
- Resource binding + delegation
- RFC 8707 / RFC 7523 / Microsoft OBO
- 4
- Implementation + control map
- github.com/bbenz/mcp-tool-calling
- BACKUP  |  PUBLIC REFERENCES; FULL LINKS IN NOTES / GUIDE

**Saved speaker notes:**

BACKUP for Q&A, hard stop 25:00. Return to slide 6. Do not turn this reference slide into another segment.

Public sources:

MCP authorization: https://modelcontextprotocol.io/specification/latest/basic/authorization

Protected Resource Metadata: https://www.rfc-editor.org/rfc/rfc9728

Authorization Server Metadata: https://www.rfc-editor.org/rfc/rfc8414

PKCE: https://www.rfc-editor.org/rfc/rfc7636

Resource Indicators: https://www.rfc-editor.org/rfc/rfc8707

JWT bearer grants: https://www.rfc-editor.org/rfc/rfc7523

OAuth security best practice: https://www.rfc-editor.org/rfc/rfc9700

Microsoft on-behalf-of flow: https://learn.microsoft.com/entra/identity-platform/v2-oauth2-on-behalf-of-flow

Project: https://github.com/bbenz/mcp-tool-calling

Schedule: https://events.linuxfoundation.org/mcp-dev-summit-toronto/program/schedule/?id=1284815

Protocol revision 2026-07-28 and MCP SDK 2.2.0 are recorded compatibility findings, not freshly imported from the demo environment. The latest-spec URL can change; consult the recorded compatible revision when reproducing this demo.

Source mapping: docs/APPENDIX.md F for reference topics; docs/CONTROL-MAP.md for attendee checklist; docs/COVERAGE-MATRIX.md for tests and expectations; docs/RUNBOOK.md for rehearsal operations. Implementation takes precedence over drifted example identities in prose.

Evidence: references, not proof of live integrations. Only the event schedule and repository-public status were checked online during generation; no private material was uploaded.
