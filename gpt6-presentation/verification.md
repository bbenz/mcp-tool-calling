# Presentation verification

## Current status

**Deck verified; presenter rehearsal items remain.** Structural, local-render,
source-reconciliation and independent visual checks passed. All nineteen slides
were visually reviewed. The three minor visual refinements were applied,
rerendered and accepted on reinspection. This is a verified presentation
artifact, not certification that the live demo is currently ready.

Output: six main slides, thirteen genuinely hidden backup slides, actual notes
on all nineteen slides, editable PowerPoint shapes and text. The PDF includes
**all nineteen slides**, including backups. The contact sheet and individual
1920 x 1080 PNGs are in [previews](previews).

The demo was not executed. Expected outcomes remain explicitly labeled.
Historical audit excerpts are identified as recorded, with their source and
date. "Deck validated" must not be read as "live demo rehearsed today."

## Source basis and evidence boundaries

- Source worktree revision: `9d5b15d8aec2065d8b8fa04ffffc7bc79edb2e84`.
- The requested GPT-6 prompt was absent from this worktree; the existing copy
  in the main checkout was read and executed without copying or modifying it.
- The accepted proposal, runbook, stage script, control map, coverage matrix,
  README, event records, deployment/setup docs, compatibility record, risk
  register, approval checklist and appendix were read. The directly relevant
  implementation was reviewed statically, never imported as an application.
  That review also covered the operator command wrappers, audit schema, and
  targeted matching-resource integration/unit-test source.
- Current public schedule confirms Brian Benz, October 6, 15:40-16:05,
  Ballroom East/Center. Event timezone is EDT (UTC-4). Timing and room are
  subject to change. Verification date: September 16, 2026.
- `gh repo view` confirmed `https://github.com/bbenz/mcp-tool-calling` is public.
  The QR image is programmatically compared with a QR generated from that
  exact URL; the embedded hyperlink uses the same target. This does not imply
  that the newly generated deck has been published.
- The deck's one raster asset is that QR. There are no screenshots masquerading
  as captures, external image fetches, live websites, videos or embedded code.

## Checks performed

| Check | Result |
|---|---|
| Saved PPTX reopened with python-pptx | PASS |
| 16:9 dimensions | PASS: 13.333333 x 7.5 inches |
| Main/backup inventory | PASS: 6 visible + 13 hidden |
| Real slideshow visibility | PASS: XML `show="0"` for 7-19, independently recognized by PowerPoint COM |
| Notes | PASS: 19/19 nonempty, exact match to saved content source |
| Timing | PASS: 1500 seconds, contiguous seven segments; Q&A 1380-1500 seconds |
| Projection fonts | PASS: explicit effective sizes >=24 pt, including footers; titles 38-44 pt |
| Font availability | Calibri installed locally; no online fonts or substitution required |
| Shape bounds | PASS: all within slide bounds |
| PowerPoint text geometry | PASS after repairs: no detected text overflow or text-to-text overlap; text stays within the half-inch safe region |
| Local desktop renderer | PASS: PowerPoint 16.0 exported all 19 slides at 1920 x 1080 |
| PDF | PASS: 19 pages, extractable text on every page, page bounds checked |
| Contact sheet | Generated from all 19 rendered slides |
| Independent visual inspection | All 19 full-size images and contact sheet reviewed; no blocking clipping, overlap, contrast or margin defect |
| QR/hyperlink target | PASS: exact confirmed public repository; no placeholder URL |
| Animation/transition scan | PASS: no slide timing/transition elements |
| Credential-pattern review | PASS on generated source, guide, PPTX XML/relationships and PDF text; no token/key/secret values or access-bearing URLs |
| Embedded content | PASS: no OLE/ActiveX payloads or embedded live content |
| Foreground/background contrast | PASS: tested palette pairs 6.06:1 to 13.21:1 |
| Generator syntax | PASS: all four Python source modules compile |
| Reproducibility | PASS: second build's uncompressed PPTX package parts matched exactly |
| Required source paths | 24 listed source paths present during prerequisite preparation |
| Implementation reconciliation | PASS: fixture roles, ownership, scopes, amounts, reasons/rules, replay flags, policy version and actual commands checked statically |
| Application tests / services / inference | NOT RUN, intentionally outside authorization |

Machine-readable results are in
[verification-results.json](verification-results.json). Word counts there
include titles and evidence/footer labels, not only body text. The main-slide
word target is a design target; the architecture and control-map labels use
the prompt's explicit diagram/table exception. No test-count badge is projected.

## Repair cycle

The first render was not accepted:

1. Footer glyph bounds extended slightly into the half-inch safe region.
   All footers and slide numbers were moved upward.
2. The opening subtitle, speaker block and synthetic refund card had text
   boxes shorter than PowerPoint's measured text height. Boxes were expanded,
   without reducing type.
3. The authorization card had an over-wide line. Its sentence was rewrapped
   into shorter explicit lines, preserving the principal/object/time question.
4. The architecture client label needed more vertical room. Its text frame was
   enlarged without shrinking the 24 pt labels.
5. The first control map's long middle labels wrapped and its platform-filter
   caption overlapped the last row. Labels were shortened and row spacing
   adjusted so all responsibilities remain legible.
6. Several backup step labels and hosting-card bodies needed taller text
   frames. Heights were corrected instead of using auto-shrink.
7. Footer objects were moved to the end of the shape order, after meaningful
   slide content, for a more sensible reading sequence.

All slides were regenerated and rerendered after repairs. The final
PowerPoint geometry pass reported **zero** overflow, text-overlap or margin
issues. Independent visual review examined slide-01.png through slide-19.png
individually, plus the contact sheet. It found three nonblocking refinements:
bring the architecture labels closer to their arrows, separate the Q&A link
from its footer, and remove a lonely last word in the offline-assessment card.
Those changes were applied and all nineteen slides were rerendered. The
reviewer rechecked slides 3, 6 and 14 and accepted them without further changes.
Source review then clarified slide 11's matching-resource control: there is a
separate HTTP/MCP integration-test assertion for B acceptance, not merely a
validator test. Its label and notes were corrected without claiming a new run.
Slide 11 was rerendered and visually inspected again; the corrected label fits
clearly. Final source/guide, PPTX XML and PDF sanitization covered 141 text
surfaces, and the final content rebuild again matched package parts exactly.

## Source-derived values and reconciled limitations

- **14 scenarios**, statically counted in `scenarios.py::SCENARIOS`. One
  mutation scenario and thirteen expected non-mutating scenarios; discovery
  succeeds without mutation, so this does not mean thirteen denied calls.
- **3 MCP tools**, **3 employee fixtures**, **5 order fixtures**.
- **207 tests** is the documentation's recorded count, not a freshly run suite.
- Dana: `Refunds.Read`, owns ORD-1002. Sam: read/write, owns ORD-1001/1004/1005.
  Riley: read/write, owns ORD-1003. Injected notes are in ORD-1005.
- Actual scopes: `Refunds.Read`, `Refunds.Write`; B uses `Probe.Read`;
  downstream delegation uses `Ledger.Refund`.
- Default policy: `refund-policy/2026-10-06.1`; default ceiling 25000 CAD
  minor units. Allowed request is 4000; ownership/injection request is 99000.
- Allowed output flag is `idempotent_replay`, false then true. Audit outcomes
  are `applied` / `replayed`; audit rule field is `policy_rule_id`.
- Scenario client is `unapproved-demo-client`, not conflicting prose/default
  names. The guide avoids these drifted examples.
- The guide names the exact integration-test and validator-test symbols and
  distinguishes assertions from execution. The A-rejection and B-acceptance
  tests acquire separate tokens; they are not a continuous same-token trace.
- Scenario PASS predicates are narrower than some narration: wrong-audience
  checks HTTP 401 rather than the exact reason, and PKCE downgrade accepts a
  `ClientError`. Four protocol scenarios collect fingerprints without asserting
  equality. The guide explicitly records these limitations.
- The subject is pseudonymized in audit; validated tenant_id is retained as-is
  by the implementation. Tenant values are omitted from projected excerpts.
  No universal secret-detection claim is made for arbitrary logged text.
- A final source follow-up tightened slide 3's notes: every scenario captures
  fingerprints, but most (not all) denial scenarios assert equality. The
  projected slide content is unchanged.

## Design choices

- Exactly six main slides preserve the requested two projector windows.
  Thirteen hidden backups, rather than ten cramped slides, split model modes,
  the remaining checklist, integration limits and references.
- High-contrast forest/cream palette: dark opening/takeaways, light content.
  Red is restricted to explicitly labeled untrusted client/model input.
- Calibri is used throughout because it is installed and projection-friendly.
  Diagram/evidence labels stay at 24 pt rather than shrinking to fit.
- Architecture uses native nodes and connectors; return arrows are omitted
  deliberately for clarity. The Foundry branch is advisory and never points
  at ledger mutation. Resource B details live in the appendix.
- No private cloud endpoint, access key, JWT, idempotency-key value or hostile
  payload is needed to teach the boundary.

## Material limitations / presenter actions

1. **The same-token-at-B HTTP positive control is not captured by the named
   wrong-audience scenario.** Slide 11 labels B acceptance an integration-test
   assertion, not rerun here. The guide names the separate tests and their
   separately acquired tokens. A continuous same-token A/B trace remains
   EXPECTED CONTROL - NOT CAPTURED. Rehearse and sanitize it separately if
   claiming that live observation.
2. **Real client approval remains a manual rehearsal item.** The supplied
   checklist has no filled version/date/results. The browser Run button and a
   server denial cannot prove a dialog was shown or Cancel was clicked.
3. **No current live-state claim.** Local/Compose/AKS and Foundry findings are
   attributed to dated supplied records. Source documents contain historical
   date and teardown/left-running inconsistencies. No cluster status was read.
4. **Production integrations are not inferred.** Entra mode, AKS Foundry
   workload identity, the separate Bicep deployment and a successful live
   Application Insights/KQL session are not established by these slides.
5. **PDF backup navigation is manual.** It includes hidden slides as normal
   pages; hold on page 6 for questions.
6. **Rehearse the clock.** The planned budgets total 25:00, but this is not
   evidence of a timed delivery. Keep 23:00-25:00 for Q&A.

## What was not done

No edits to `demo`, `docs`, `Events`, existing prompts, application configuration
or `demo/.venv`; no application imports/tests, service starts/stops, scenario
execution, ledger reset, credential reads, Azure APIs, kubectl, deployment,
inference charges, commit, push or publication. No source or slide assets were
uploaded to a third-party rendering service.
