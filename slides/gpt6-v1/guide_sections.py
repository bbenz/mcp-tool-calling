"""Presenter instructions saved with the generator, independent of chat history."""

INTRO = r"""# Presenter guide

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
"""
