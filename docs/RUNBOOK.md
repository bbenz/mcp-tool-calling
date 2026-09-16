# Presenter Runbook

**Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy**
MCP Dev Summit Toronto · 2026-10-06 · 15:40–16:05 · **25 minutes, hard stop**

This is the operational document: what to run, when to stop, and what to do when something breaks. The words you say are in [ONSTAGE-SCRIPT.md](ONSTAGE-SCRIPT.md). Keep both open — runbook on your laptop, script in your notes.

> **The one rule:** cut *depth*, never *coverage*. Every promise in the published description must appear on screen, at minimum as a stated result with visible evidence. If you are behind, show the prepared artifact and move on. A skipped promise is a broken promise; a compressed one is just a shorter demo.

> **Deployment mode for this delivery: the operator scripts, in PowerShell.** There are Docker Compose and AKS deployments in [DEPLOYMENT.md](DEPLOYMENT.md), and they are useful for other rooms — a remote audience, a workshop, someone else's laptop. They are **not** what you present from. A laptop running four Python processes has fewer failure modes than a cluster provisioned an hour earlier, and nothing in these 25 minutes needs a network.

---

## T-minus checklist

> All commands run from the `demo/` directory. This runbook uses PowerShell, which is the rehearsed path — **present from PowerShell**. Every command has a bash twin (`.\scripts\x.ps1` → `./scripts/x.sh`) if you are on Linux or macOS; see `docs/SETUP.md` §2.

### T-24 hours

- [ ] `.\scripts\stop-all.ps1` then `.\scripts\start-all.ps1 -Reset`
- [ ] `.\scripts\check.ps1` → must end with **`READY`** (207 tests, 14/14 scenarios)
- [ ] Full rehearsal with a timer. Note your actual time at each stop-time.
- [ ] If you are using a live client, confirm by hand that the consent prompt and the per-call approval dialog both appear — no automated test can prove a UI worked.
- [ ] **Do not upgrade `mcp` inside 72 hours** of the talk unless something is broken.

### T-60 minutes

- [ ] Laptop on **mains power**; sleep, screensaver, and auto-lock **off**
- [ ] Notifications off (Windows Focus Assist / Do Not Disturb), Slack/Teams/mail quit
- [ ] Terminal font ≥ 20 pt, dark-on-light or high-contrast theme, window ≥ 120 columns
- [ ] **If using the web UI:** size it for the back row with **A+** in the page header (or `+` / `-` / `0`), and leave every expander **collapsed** — they are for readers, not for the room. The size persists across reloads.
- [ ] `.\scripts\start-all.ps1 -Reset` → `.\scripts\check.ps1` → **`READY`**
- [ ] Open the four windows below and leave them open
- [ ] **Airplane mode test:** disable Wi-Fi, run `.\scripts\scenario.ps1 allowed-refund`. It must pass. Re-enable Wi-Fi. This is your conference-network insurance.
- [ ] `.\scripts\reset.ps1` so the ledger starts clean

### T-5 minutes

- [ ] `.\scripts\health.ps1` → four green lines
- [ ] `.\scripts\reset.ps1` — start from the known digest `211597d92491`. Safe with the services running; it keeps the signing key.
- [ ] Slide 1 (trust-boundary diagram) on the projector
- [ ] Timer started **at your first word**, visible to you

### Window layout — set once, never rearrange on stage

| # | Window | Contents |
| --- | --- | --- |
| 1 | **Slides** | Trust-boundary diagram, control map |
| 2 | **Terminal A** *(primary)* | `demo/` — where every command runs |
| 3 | **Terminal B** | `demo/` — audit view only |
| 4 | **Editor** | `policy.py`, `tokens.py`, `mcp_server/app.py` pre-opened as tabs |

Switching windows costs attention. Aim for fewer than ten switches in 25 minutes.

---

## Timed run of show

Stop-times are **cumulative elapsed**. If you are past a segment's stop-time by more than **45 seconds**, invoke that segment's fallback and move on immediately. Do not do arithmetic on stage — just read the clock against the column.

### Segment 1 · 00:00–02:00 · Frame the question

| | |
| --- | --- |
| **Stop-time** | 02:00 |
| **Tier** | A |
| **Window** | Slides |
| **Actions** | Show the annotated trust-boundary diagram from your slides. Name the three distinct things: authentication, authorization, approval. |
| **Commands** | none |
| **Evidence** | Diagram with red boundaries on client and model |
| **Fallback** | Talk it through against the control table in `README.md` — same four actors, same ownership |
| **Hard rule** | Do not demo here. Do not apologise for the size of the topic. |

### Segment 2 · 02:00–07:00 · Protocol trace

| | |
| --- | --- |
| **Stop-time** | 07:00 |
| **Tier** | **A** (trace) · B (interactive sign-in) |
| **Window** | Terminal A |
| **Command** | `.\scripts\scenario.ps1 no-token` then `.\scripts\scenario.ps1 discovery` |
| **Expected** | `no-token` → 401 + `WWW-Authenticate` naming resource metadata. `discovery` → PRM → AS metadata → PKCE `S256` → `resource=api://refund-mcp-a` → token with one audience. Both `PASS`. |
| **Evidence** | The printed trace. Field **names** and redacted values only — the verifier, code, and token are never printed. |
| **Code bookmark** | `client.py::acquire_token` |
| **Fallback** | If a live client sign-in stalls > 20 s, abandon it and use the scenario trace. It proves the same flow. |
| **Say aloud** | *"Resource binding stops cross-resource reuse. It does not stop replay of a stolen token at its own resource."* |

> ⚠️ **Do not attempt an interactive browser sign-in unless you are ahead of schedule.** It is Tier B and it is the single most common way this segment overruns.

### Segment 3 · 07:00–11:00 · Read, assess, deny

| | |
| --- | --- |
| **Stop-time** | 11:00 |
| **Tier** | A (denials) · B (live Foundry) |
| **Window** | Terminal A, then Editor |
| **Commands** | `.\scripts\scenario.ps1 scope-denial` · `.\scripts\scenario.ps1 business-rule-denial` |
| **Expected** | `scope-denial` → `POLICY_MISSING_SCOPE` (R003). `business-rule-denial` → `POLICY_ORDER_NOT_REFUNDABLE` (R200). Both `ledger: UNCHANGED`. |
| **Evidence** | Reason code + rule ID + `refund-policy/2026-10-06.1`, and an unchanged digest |
| **Code bookmark** | `policy.py` — the rule table. Show that it is a flat list of checks, not a framework. |
| **Fallback** | If the Foundry call is slow or throttled, the offline path returns instantly, labelled `[OFFLINE ASSESSMENT - NO MODEL WAS CALLED]`. **Read that label out loud** and continue. |
| **Say aloud** | *"The model produced advice. Advice is not a decision. The decision is in this file."* |

### Segment 4 · 11:00–15:00 · Annotations, approval, delegation

| | |
| --- | --- |
| **Stop-time** | 15:00 |
| **Tier** | A (annotation + refund + delegation) · B (client cancel/approve) |
| **Window** | Terminal A |
| **Commands** | `.\scripts\scenario.ps1 annotation-tampering` then `.\scripts\scenario.ps1 allowed-refund` |
| **Expected** | Tampering: identical denial, same rule ID. Refund: `RFND-…` applied, `ledger: CHANGED`, retry `replayed=True`, `total_refunded_minor: 0 -> 4000`, `delegated_identity_preserved: True`, `upstream_audience: api://refund-upstream`. |
| **Evidence** | Ledger rises **once** across two calls; audience differs while subject is preserved |
| **Code bookmark** | `mcp_server/app.py` tool annotations; `delegation.py::exchange_for_upstream` |
| **Fallback** | If the live client cancel/approve cycle misbehaves, state it as client-only evidence and run `.\scripts\scenario.ps1 over-limit-denial` — a server denial no dialog can override. |
| **Say aloud** | *"`readOnlyHint` is documentation. It is not a permission."* |

### Segment 5 · 15:00–20:00 · The three adversarial checks

| | |
| --- | --- |
| **Stop-time** | 20:00 |
| **Tier** | **A** (all three) |
| **Window** | Terminal A |
| **Commands** | `.\scripts\scenario.ps1 wrong-audience` · `.\scripts\scenario.ps1 ownership-denial` · `.\scripts\scenario.ps1 prompt-injection` |
| **Expected** | 1 — B-token rejected at A with `AUTH_WRONG_AUDIENCE`, **plus the control**: the same token succeeds at B. 2 — `POLICY_ORDER_NOT_ASSIGNED` (R006). 3 — the injected note is recorded, the forced call is denied. All three: `ledger: UNCHANGED`. |
| **Evidence** | Three different reason codes, three unchanged digests |
| **Code bookmark** | `tokens.py` audience check; `policy.py` R006 |
| **Fallback** | Behind schedule? Run `wrong-audience` live and **read** the other two results from a prior `run-all` transcript. State that you are showing recorded output. Never skip one. |
| **Say aloud (injection)** | *"Whatever the model decided doesn't matter. I'm forcing the call through the harness. This is a harness replay, not a fresh model attack — and the server still says no."* |
| **If the filter fires (cloud mode)** | With `FOUNDRY_ENDPOINT` set, the evidence shows `assessment_was_blocked_by_content_filter: True` and `handled_by: platform content filter`. **Say it precisely:** the *platform* refused the prompt — not the model, and not this application. Then make the real point: *"That's a third layer, and it isn't mine. It's in the platform, not my code and not MCP. It's also still not the boundary — watch."* Run the forced call and show the identical denial. |
| **Say aloud (deputy)** | *"Riley has the write scope. Riley is not confused. The server is the deputy, and it refuses to be confused on Riley's behalf."* |

> This segment is **the promise of the talk**. Protect its five minutes. If you must steal time, steal it from Segment 3's code walkthrough.

### Segment 6 · 20:00–23:00 · Audit and control map *(recovery buffer lives here)*

| | |
| --- | --- |
| **Stop-time** | 23:00 |
| **Tier** | A (local audit) · C (KQL) |
| **Window** | Terminal B, then Slides |
| **Commands** | `.\scripts\audit.ps1 -Last 6` |
| **Expected** | Records tying trace ID → MCP request ID → pseudonymized user → client → audience → tool → policy version → rule → result → ledger change. The rejected token appears as `identity  untrusted` with **no** user attributed. `arguments` shows `_omitted_keys: ["idempotency_key"]`. |
| **Evidence** | One allowed and one denied request followed end to end |
| **Fallback** | Skip the Application Insights query entirely (Tier C). The local JSON view never depends on the network. |
| **Say aloud** | *"This is a JSONL file on a disk. It is a good application log. It is not immutable and it is not tamper-proof — that needs append-only storage with independent retention, and that's a different talk."* |
| **Then** | Control map on screen. Leave it up. |

### Segment 7 · 23:00–25:00 · Q&A

Control map stays on the projector. Prepared answers below.

---

## Degradation ladder

Decide **before** you are under pressure.

**Tier A — always live, never cut:**
1. 401 challenge + Protected Resource Metadata fetch
2. One allowed refund, ledger changing exactly once
3. One policy denial at `tools/call` with a reason code
4. Wrong-audience rejection **with its control**
5. The audit record tying request → user → client → resource → policy → result

**Tier B — live if on time, otherwise prepared evidence:**
- Interactive sign-in · live Foundry `assess_refund` · client cancel-then-approve · annotation tampering via a live client · live prompt-injection model run

**Tier C — compress first:**
- Narration depth · code walkthroughs · the Application Insights query · appendix topics → Q&A or the repo

**Per-segment hard stop:** more than **45 seconds** over a stop-time → prepared artifact, move on. No exceptions, no negotiating with yourself on stage.

---

## Recovery paths

| Symptom | Detection (seconds) | Action |
| --- | --- | --- |
| A scenario hangs | No output after ~5 s | `Ctrl+C`, `.\scripts\health.ps1`. One service red → `.\scripts\stop-all.ps1; .\scripts\start-all.ps1` (~10 s). Narrate the control map while it restarts. |
| Ledger in an unexpected state | Digest is not what you expected | `.\scripts\reset.ps1` (instant) |
| `IDEMPOTENCY_KEY_REUSED` | Reason code printed | Correct behaviour from a re-run. Say so, then `.\scripts\reset.ps1`. |
| Conference Wi-Fi dies | Anything network-bound stalls | **Nothing on the critical path needs the network.** Foundry falls back to the labelled offline path. Keep going. |
| Live client will not authenticate | Sign-in > 20 s | Abandon the client. It is Tier B. Every claim it supports is proven by `scenario.ps1`. |
| Consent prompt does not reappear | No dialog on connect | Cached token. Do not debug on stage — clear the client's cached authorization and re-check after the talk. |
| Foundry throttled or slow | > 3 s with no output | Offline path returns immediately and labels itself. Read the label aloud. |
| Model refuses the injection | Model output differs from rehearsal | **Expected and fine.** The harness forces the call anyway. Say: *"the model's answer isn't the boundary."* |
| Content filter blocks the assessment | `assessment_was_blocked_by_content_filter: True` | **Expected in cloud mode, and worth a sentence.** The platform refused the prompt — say *platform*, not *model*. Then force the call and show the identical denial. |
| Services "healthy" but code changes do nothing | `start-all` says all healthy, yet behaviour is stale | Orphaned processes from an earlier run still hold 8800–8803, and `start-all` health-checked *those*. `stop-all` only knows its own PIDs. Recover: `Get-NetTCPConnection -LocalPort 8800 -State Listen` (repeat for 8801–8803), `Stop-Process -Id <pid> -Force` for each, then `start-all`. |
| Text too small from the back of the room | Someone squints | Click **A+** in the page header, or press `+` / `-` / `0` on the page. The size persists across reloads. |
| Total terminal loss | Obvious | Slides alone. Every claim maps to a named scenario and a test — state the claim, name the scenario, and say what the evidence would have been. |

---

## Q&A — prepared answers

**"Why aren't scopes enough?"**
A scope is a *verb*, not an *object*. `refund.write` says Riley may issue refunds. It says nothing about *which order*. `ORD-1003` belongs to someone else, and R006 is the only thing between a correctly-scoped token and another employee's book. If you want scopes to carry objects, you end up minting a scope per order — that is not an authorization model, it is a denial-of-service against your own token endpoint.

**"Isn't a confirmation dialog enough?"**
The dialog runs on the user's machine, in software you do not control, and it can be modified, automated, or skipped. It answers *"did the human mean to do this?"* — a real and necessary question, but a different one from *"is this human allowed to do this?"* Watch section C of the approval checklist: the human clicks **Approve** and the server denies anyway. That is the correct outcome, and it is only possible if the server decides independently.

**"Why can't I forward the incoming MCP token to my API?"**
Because it was minted for a different audience, and the moment a downstream service accepts it you have built a confused deputy on purpose. Every service that accepts your MCP token becomes reachable by anyone holding it. Exchange it — on-behalf-of — for a token scoped to the downstream audience, preserving the user. And if the exchange fails, **fail**. A silent fallback to an app-only token is how a user-scoped request quietly becomes an application-privileged one. `scenario token-passthrough-blocked` shows the forwarded token being rejected.

**"Why a local IdP instead of Entra?"**
`devidp` is a real authorization server: RS256 with a real JWKS, PKCE S256 only, mandatory RFC 8707 resource indicators, RFC 7523 for the on-behalf-of exchange — and it is validated by the *same* `TokenValidator` that Entra tokens go through. The boundaries you are watching are genuine. The Entra path is implemented; it has not been executed, because no tenant was authorized for this build. I would rather tell you that than imply a test I did not run.

**"Is the audit log tamper-proof?"**
No. It is a JSONL file. It is structured, pseudonymized, and written at the decision point including denials — which already puts it ahead of most production systems. It is not immutable. Tamper-evidence requires append-only storage with independent retention and a separate trust domain.
