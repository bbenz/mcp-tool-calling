# PowerPoint Generation Prompt v1: Who Can Call This MCP Tool?

Use this prompt with a coding agent **in this repository** to generate the slide deck for Brian Benz's MCP Dev Summit Toronto 2026 session. The demo, the tests, the runbook, and the on-stage script already exist and are verified — this prompt produces the **slides that wrap around them**, and nothing else.

This prompt is written to be run **in a single pass, with no clarifying questions**, because it may be executed in front of an audience. Resolve every ambiguity yourself, state the assumption in your final report, and keep going.

---

## Non-Negotiables

Read this list first. Everything below elaborates on it.

1. **This is a terminal demo with slides around it, not a slide talk.** Roughly **five** of the twenty-five minutes have slides on the projector. Build **8–10 visible slides. Twelve is a hard ceiling.** A deck that takes 25 minutes to present has destroyed the demo it was supposed to support.
2. **The repository is the source of truth, not your memory of this topic.** Read the files in [Source Files](#source-files-in-priority-order) before writing a single slide. Every claim, reason code, rule ID, and count on a slide must be traceable to one of them.
3. **Verify every number at generation time.** Counts drift. Do not copy "14 scenarios" or "217 tests" from this prompt — re-derive them (`demo/src/refund_demo/scenarios.py`, and the count reported by the test suite in `docs/COVERAGE-MATRIX.md` / `README.md`). If a number you find disagrees with this prompt, trust the repository and say so in your report.
4. **Never put a credential on a slide** — not a real one, not a fake one, not a truncated one. No JWTs, no `eyJ…` strings, no client secrets, no PKCE verifiers, no authorization codes, no API keys. Field **names** and the word `<redacted>` only. Someone will photograph the slide; teach the right lesson.
5. **Do not overstate what was proven.** The [Honesty Constraints](#honesty-constraints--what-must-not-appear-on-a-slide) section lists five specific claims this talk deliberately does *not* make. Reproducing any of them on a slide contradicts the talk itself.
6. **Do not touch the demo.** No edits under `demo/src/`, `demo/tests/`, `demo/k8s/`, or `demo/scripts/`. Do not start or stop services, do not run the test suite, do not call Azure, do not run `kubectl`, and **do not install anything into `demo/.venv`** — that environment is pinned and recorded in `docs/COMPATIBILITY-RECORD.md`. Deck tooling goes in its own virtual environment (see [Output Contract](#output-contract)).
7. **Every slide carries speaker notes**, drawn from `docs/ONSTAGE-SCRIPT.md`, with the segment stop-time from `docs/RUNBOOK.md` and an explicit next-window cue.
8. **No animations, no builds, no transitions, no video.** Remote clickers lag, presenter view drifts, and a build that half-fires on stage costs more than it ever bought.
9. **Verify the output programmatically before you claim success** — reopen the `.pptx`, check it, and render at least two slides to images and actually look at them. See [Verification Contract](#verification-contract).
10. **Resolve routine design choices yourself.** Do not ask which font, which colour, or whether to include a slide. Decide, justify it in one line in your report, and move on.

---

## Mission

Produce a conference-ready PowerPoint deck for:

> **Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy**
> Brian Benz · MCP Dev Summit Toronto · <https://events.linuxfoundation.org/mcp-dev-summit-toronto/>
> 2026-10-06 · 15:40–16:05 · Ballroom East/Center · intermediate audience
> **25 minutes total, including introduction and Q&A. Hard stop.**

The deck's job is to do the three things a terminal cannot: **frame the question** in the first two minutes, **hold the synthesis** on screen while the audience absorbs it at the end, and **stand in for the demo** if the demo dies. Nothing else.

The talk's argument, in one sentence, is the thing the deck must make unmissable:

> **Authentication, approval, and authorization are three different questions, and only one of them is yours to answer.**

---

## The Time Budget That Determines Everything

From `docs/RUNBOOK.md`. Note the middle column — this is why the deck is small.

| Segment | Elapsed | On the projector |
| --- | --- | --- |
| 1 · Frame the question | 00:00–02:00 | **Slides** |
| 2 · Protocol trace | 02:00–07:00 | Terminal A |
| 3 · Read, assess, deny | 07:00–11:00 | Terminal A, then the editor |
| 4 · Annotations, approval, delegation | 11:00–15:00 | Terminal A |
| 5 · Three adversarial checks | 15:00–20:00 | Terminal A |
| 6 · Audit, then the control map | 20:00–23:00 | Terminal B, then **slides** |
| 7 · Q&A | 23:00–25:00 | **Slides** (control map stays up) |

**Two slide windows: about two minutes at the start and about three and a half at the end.**

**No mid-demo slides.** Do not create "you are here" markers, section dividers, or a recap slide between segments 2 and 5. The runbook budgets fewer than ten window switches for the whole session; every interstitial spends two of them and buys nothing. If you feel the urge to add one, add it to the hidden appendix instead.

---

## Required Slide Plan

Build exactly this. Deviate only with a stated reason.

### Opening — on screen 00:00–02:00

| # | Slide | Must contain | Notes source |
| --- | --- | --- | --- |
| 1 | **Title** | Session title, speaker name, event, date. Nothing else — no agenda, no bio, no logo wall. | Runbook Segment 1 |
| 2 | **The question** | *"Someone builds an MCP server with a `refund_order` tool. It works. Then someone asks: who can call this tool?"* and the three usual non-answers — "the user signed in", "there's an approval dialog", "it's only on the internal server" — with the punchline: **none of them answers the question.** | Script 00:00–02:00 |
| 3 | **Three different questions** | Authentication = *who are you* (authorization server). Approval = *did the human mean it* (the client, on hardware you don't control). Authorization = *is this principal allowed to do this specific thing to this specific object, right now* — **nobody answers that unless you write it.** Visually distinguish the third. | Script 00:00–02:00 |
| 4 | **Trust boundary** | The architecture diagram from `docs/CONTROL-MAP.md` (mermaid source is in that file — reproduce it as native PowerPoint shapes, not a screenshot). **Red = outside your trust boundary**: the MCP client and the model. Bottom line of the slide: *every denial prints the ledger digest before and after, so "nothing happened" is shown, not asserted.* | Script 00:00–02:00 |

Then the presenter switches to Terminal A for nineteen minutes. **The deck contributes nothing until 21:30.**

### Close — on screen from ~21:30

| # | Slide | Must contain | Notes source |
| --- | --- | --- | --- |
| 5 | **Five layers** | The control map as a table or row of columns: MCP client, authorization server, **MCP server**, upstream API, model. For each: who owns it, what it denies, and its limitation. Make the third column visually dominant — it is the only one the audience owns. Include Layer 5b (the platform content filter) only if it fits without shrinking type. | `docs/CONTROL-MAP.md`; script 20:00–23:00 |
| 6 | **The answer** | One sentence, very large, alone on the slide: **"Only the principal your server decided may call it, on the object it decided they may touch, at the moment they asked."** | Script 20:00–23:00 |
| 7 | **Take this home** | The seven rules from the *Take this home* section of `docs/CONTROL-MAP.md`. Emphasise the three the script says to remember: bind every token to one resource · scopes are verbs, not objects · assume Approve was clicked and decide anyway. | `docs/CONTROL-MAP.md` |
| 8 | **Q&A backdrop** | Repeat slide 5's control map, plus the repository URL and a QR code in the footer. The runbook says the control map stays up through Q&A, and the audience will want the link during exactly those two minutes — so both live on one slide and the presenter never has to choose. | Runbook Segment 7 |

Slides 9 and 10 are **optional** and only justified if they do not push the visible count past twelve:

- **What I did not prove** — the honesty slide. Entra implemented but not executed; the audit log is not tamper-proof; resource binding does not stop replay at its own resource; the injection demo is a harness replay, not a fresh model attack. This is strongly in the voice of the talk and makes an excellent Q&A backdrop if it can share screen time with slide 8.
- **Try it yourself** — repository, `scripts\check.ps1`, the scenario list, the docs index.

### Appendix — hidden, never shown unless the demo dies

The runbook's total-terminal-loss recovery is *"slides plus `docs/COVERAGE-MATRIX.md` — read the expected evidence column."* Make that possible from the deck alone.

Add **one hidden slide per Tier A item** (see the runbook's degradation ladder), each stating the scenario name, what it proves, and the **exact expected evidence**:

| Scenario | Expected evidence on the fallback slide |
| --- | --- |
| `no-token` + `discovery` | 401 with `WWW-Authenticate` naming Protected Resource Metadata → PRM → AS metadata → PKCE `S256` → `resource=api://refund-mcp-a` → single-audience token |
| `allowed-refund` | `RFND-…` applied, ledger **CHANGED**, `0 → 4000`, retry `replayed=True`, `upstream_audience: api://refund-upstream`, `delegated_identity_preserved: True` |
| `scope-denial` | `POLICY_MISSING_SCOPE`, R003, ledger **UNCHANGED** |
| `wrong-audience` | `AUTH_WRONG_AUDIENCE` at Resource A — **and the control**: the same token succeeds at Resource B |
| `ownership-denial` | `POLICY_ORDER_NOT_ASSIGNED`, R006, ledger **UNCHANGED** |
| `prompt-injection` | Injected note recorded, forced call denied, ledger **UNCHANGED** |
| Audit record | trace ID → MCP request ID → pseudonymized user → client → audience → tool → policy version → rule → result → ledger change; rejected token appears as `identity: untrusted` with no attributed user |

Mark these slides hidden in PowerPoint (`slide.hidden = True` equivalent) so they never appear in a straight-through run, and list their slide numbers in your final report so the presenter can jump to them.

---

## Design Rules For A Ballroom

**Geometry.** 16:9, 13.333 in × 7.5 in. Leave a 0.6 in safe margin — projector edges get cropped and the front row's heads occupy the bottom of the screen. **Put nothing important in the bottom 1.2 inches.**

**Type.** This is the rule that actually matters, and the one decks fail.

- Slide titles: **40 pt minimum**
- Body: **28 pt minimum**
- **Absolute floor, including diagram labels, table cells, footers, and captions: 24 pt.** Diagram labels are where every deck breaks this. If the diagram does not fit at 24 pt, the diagram has too much in it — remove a box, do not shrink the text.
- One typeface family. Segoe UI or Arial; nothing that might not be installed on the venue laptop.

**Density.** Twenty-five words per slide is the target, forty is the ceiling. Maximum six lines of text. If a slide needs more, it is two slides — or, far more likely, it is a paragraph that belongs in the speaker notes.

**Colour.** Dark text on a light background: the session is at 15:40 in a lit ballroom, and light backgrounds survive ambient light and bad projectors better than dark ones. Contrast ratio **7:1 or better** for all text.

**Red is reserved.** Red means exactly one thing in this deck — **outside your trust boundary** — matching the mermaid diagram in `docs/CONTROL-MAP.md`. Never use red for ordinary emphasis, never for a heading, never for decoration. The audience must be able to learn what red means on slide 4 and still trust it on slide 8. Use weight, size, or a single accent colour for emphasis instead.

**Also banned:** clip art, stock photography, vendor logo walls, an agenda slide, a bio slide, a "thank you" slide, gradients behind text, and any icon that has to be explained.

---

## Content Rules

**These five sentences must appear in the deck, verbatim** (from *Sentences worth protecting* in `docs/ONSTAGE-SCRIPT.md`). They are what survives if the presenter loses ten minutes:

1. Authentication, approval, and authorization are three different questions. Only one of them is yours to answer.
2. A scope is a verb, not an object. `refund.write` never named `ORD-1003`.
3. Annotations are hints from a process you don't control.
4. Never forward an incoming token downstream. Exchange it — and if the exchange fails, fail.
5. If a model's refusal is your security boundary, your security boundary is a probability distribution.

**Identifiers must be exact.** Copy them from the repository, never from recollection: `AUTH_WRONG_AUDIENCE` (`tokens.py`) · `POLICY_MISSING_SCOPE` (R003) · `POLICY_ORDER_NOT_ASSIGNED` (R006) · `POLICY_ORDER_NOT_REFUNDABLE` (R200) — all in `policy.py` · policy version `refund-policy/2026-10-06.1`, which lives in `config.py`, not `policy.py` · audiences `api://refund-mcp-a`, `api://refund-mcp-b`, `api://refund-upstream`. A wrong rule ID on a slide is the one error an expert audience will catch and remember.

**Synthetic data only.** Orders `ORD-1001` … `ORD-1005`, employees Dana, Sam, and Riley, amounts in minor units. No real customers, no real money, ever.

**Language.** Plain, direct, declarative. The audience is intermediate: assume APIs, OAuth basics, and tool calling; explain the MCP-specific boundaries. No "leverage", no "seamless", no "empower", no exclamation marks, no rhetorical questions on slides except the title's own.

---

## Honesty Constraints — what must NOT appear on a slide

The talk's credibility rests on being precise about what was and was not demonstrated. Do not write, imply, or soften any of these:

| Do not claim | The accurate statement |
| --- | --- |
| Microsoft Entra ID was used or tested | Implemented, **not executed** — no tenant was authorized for this build. The local `devidp` is a real authorization server validated by the same `TokenValidator`. |
| The audit log is tamper-proof or immutable | It is a JSONL file on a disk. Structured, pseudonymized, written at the decision point including denials — and nothing more. |
| Resource binding prevents token replay | It stops reuse at a *different* resource. It does **not** stop replay of a stolen token at its own resource. |
| The model refused the injection | In cloud mode the **platform content filter** refused the prompt — not the model, and not this application. Say *platform*. And it is still not the boundary. |
| The AKS deployment uses workload identity | It authenticates with an **API key**. The account holds *Foundry User* on the model resource, which permits inference but not creating role assignments. |

If you find yourself writing a slide that needs one of these to land, the slide is wrong — cut it.

---

## Output Contract

Create a `slides/` directory at the repository root containing:

| Path | What it is |
| --- | --- |
| `slides/who-can-call-this-mcp-tool.pptx` | The deck. This is the deliverable. |
| `slides/SLIDE-NOTES.md` | The full outline in markdown — every slide's title, body text, and speaker notes. A `.pptx` does not diff in git; this is how the deck gets reviewed, corrected, and regenerated. |
| `slides/build_deck.py` | The generator script, so the deck is reproducible rather than hand-assembled. Re-running it must produce the same deck. |
| `slides/.venv/` | A **separate** virtual environment for `python-pptx`. Add it to `.gitignore`. Do not install deck tooling into `demo/.venv`. |

**Start by invoking the `pptx` skill** if it is available in your environment — it knows how to build well-formed decks and will save you from reinventing the layout handling. `python-pptx` is not currently installed anywhere in this repository, so create `slides/.venv` and install it there.

**The repository has no git remote.** Use `https://github.com/<owner>/<repo>` as a visible placeholder on the resources slide, generate the QR code from it, and **flag it clearly in your final report** so the presenter replaces it before the event. Do not invent a plausible-looking URL — a QR code that goes nowhere is worse than an obvious blank.

Commit the deck and the sources. A binary in git is a small price; a deck that exists only on one laptop the week of a conference is a real risk.

---

## Verification Contract

Do not report success on the basis that the file was written. Reopen it and check it.

**Programmatic checks** (write these as assertions in a script, and report the results):

- [ ] Visible slide count is **≤ 12**; hidden appendix slides are genuinely marked hidden
- [ ] **Every text run in the file is ≥ 24 pt** — walk every shape on every slide, including tables, grouped shapes, and text boxes inside groups. Report any violation with its slide number and the offending text; do not silently fix it by shrinking something else.
- [ ] No slide exceeds 40 words of body text
- [ ] All five load-bearing sentences are present, verbatim
- [ ] Every slide has non-empty speaker notes
- [ ] No credential-shaped strings anywhere in the file: search for `eyJ`, `Bearer `, and any unbroken alphanumeric run of 40 characters or more
- [ ] Every reason code and rule ID on a slide also appears in `demo/src/refund_demo/policy.py` or `tokens.py`; the policy version string is in `config.py`
- [ ] Slide dimensions are 13.333 in × 7.5 in

**Visual check.** PowerPoint COM is registered on this machine, so export at minimum **slide 4 (trust boundary)** and **slide 5 (five layers)** to PNG and *look at them*. These two carry the most content and are where overlapping shapes and clipped labels actually happen. If a renderer is unavailable, say so plainly in your report rather than implying you inspected something you did not.

**Final report** — keep it short, and include:

1. The slide inventory: number, title, one-line purpose, visible or hidden
2. Every number you re-derived from the repository, with the value you found
3. Any design decision you made that this prompt left open, with a one-line reason
4. The results of the verification checks, including anything that failed
5. The placeholder repository URL, called out for replacement
6. What you did **not** do

---

## If You Are Running This Live

- **Never let the first run be the on-stage run.** Execute this prompt end to end beforehand, keep the output, and know roughly how long it takes.
- **Ask no questions.** If something is ambiguous, choose, proceed, and record the choice in the report.
- **Stay inside the fence.** No test runs, no service restarts, no deployments, no Azure calls, no `kubectl`, no edits under `demo/`. There is a live AKS cluster attached to this repository; leave it alone.
- **Fail forward.** If one check fails, finish the deck and report the failure. A deck with one flagged issue is a result; an abandoned run in front of an audience is not.
- **Bound the effort.** One pass. No refactors, no exploring adjacent improvements, no rewriting the docs you read.

---

## Source Files, In Priority Order

| File | What to take from it |
| --- | --- |
| `docs/ONSTAGE-SCRIPT.md` | The narration. **Speaker notes come from here.** The *Sentences worth protecting* section is the deck's spine. |
| `docs/CONTROL-MAP.md` | The trust-boundary diagram (mermaid source), the five layers, the reason-code tables, and the seven takeaways. |
| `docs/RUNBOOK.md` | Segment stop-times, the window layout, the degradation ladder (which drives the hidden appendix), and the prepared Q&A answers. |
| `docs/COVERAGE-MATRIX.md` | Claim → scenario → test → evidence. Use it to confirm every slide claim is actually backed. |
| `demo/src/refund_demo/policy.py`, `tokens.py`, `config.py` | Authoritative rule IDs and reason codes (`policy.py`, `tokens.py`) and the policy version string (`config.py`). |
| `demo/src/refund_demo/scenarios.py` | The fourteen scenario names and their formal claims. |
| `docs/RISKS-AND-FALLBACKS.md` | What can go wrong and what is prepared — the source of the honesty slide. |
| `docs/EVENTS.md` | Event details, and what was rehearsed versus assumed. |
| `docs/COMPATIBILITY-RECORD.md` | Dated findings and defects. Useful background; **do not** put defect numbers on a slide. |
| `README.md` | Repository structure and current counts. |

---

## Definition Of Done

The deck is done when a presenter who has never seen it can open it five minutes before walking on stage and find: a title slide, four minutes' worth of opening framing, nothing in the middle, a synthesis that stays up through Q&A, and a hidden appendix that can carry the entire session if every terminal on the laptop dies at 15:41.
