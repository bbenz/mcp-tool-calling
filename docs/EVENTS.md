# Events

Where this demo has been delivered, and what changed each time.

This is a **reusable demo, not a single-use one**. The material is built around a 25-minute slot, but the tier system in [RUNBOOK.md](RUNBOOK.md#degradation-ladder) exists precisely so it can be stretched to a workshop or compressed to a lightning talk without rebuilding it. Each delivery gets a row below and a record underneath, so the next person running it — including a future you — inherits what actually happened rather than what was planned.

| # | Event | Date | Slot | Mode | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | **MCP Dev Summit Toronto** | 2026-10-06 · 15:40–16:05 | 25 min | Local scripts (PowerShell) | **Upcoming — first delivery** |

---

## 1. MCP Dev Summit Toronto 2026

**Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy**
Brian Benz · 2026-10-06 · 15:40–16:05 · 25 minutes

The demo was built for this session. Everything in this repository was written against a 25-minute slot with a live audience, no reliable network assumption, and no Azure subscription in the room.

**Planned configuration**

| | |
| --- | --- |
| Deployment mode | **Mode 1 — operator scripts, PowerShell** ([DEPLOYMENT.md](DEPLOYMENT.md#1-operator-scripts--the-rehearsed-path)) |
| Auth mode | `devidp` — the local authorization server, not Entra |
| Network dependency | **None on the critical path.** Foundry falls back to a labelled offline assessment |
| Live MCP client | Tier B — used if the schedule allows, abandoned without comment if not |
| Tier A segments | 401 + PRM discovery · one allowed refund · wrong-audience rejection · ownership denial · the audit record |
| Planned cuts if behind | Interactive sign-in, live Foundry, client cancel/approve, the Application Insights query |

**Why not the cloud modes.** Docker and AKS were added after the demo was built, for reuse rather than for this room. A conference network is the worst place to depend on a load balancer that was provisioned an hour earlier, and a single laptop running four Python processes has fewer failure modes than a cluster. Mode 1 stays the rehearsed path.

**Cloud rehearsal — 2026-09-15.** Mode 4 was deployed for real ahead of this event and torn down afterwards, so that the cloud option is a rehearsed fallback rather than a paper one. A single-node AKS cluster in `eastus`, image built by ACR Tasks, one pod with all five containers ready and zero restarts, **14/14 scenarios passing against the public IP**, and a ledger digest identical to the laptop's. Two bugs surfaced that only a real deployment could have found — both in the deploy script, both now fixed and recorded as defects 14 and 15 in [COMPATIBILITY-RECORD.md](COMPATIBILITY-RECORD.md). Cold deploy took roughly 8 minutes.

A security review of that public exposure then found four more defects (16–19), the worst being an access-key gate that failed **open** — a missing Secret would have served the whole demo anonymously with the pod still reporting healthy. All four are fixed, and the fixes were proven on a second live deployment before teardown. The cluster is **not** left running: see [DEPLOYMENT.md §8](DEPLOYMENT.md#8-security-posture-of-the-cloud-mode) before sharing a link at any future event, because the endpoint is plain HTTP and the key travels in the URL.

**Retrospective** *(fill in after delivery)*

| | |
| --- | --- |
| Actual finish time | |
| Segments cut | |
| Live client used | |
| Questions that landed | |
| Questions that exposed a gap | |
| What to change next time | |

---

## Running this demo at another event

### Before you accept the slot

Check the length against the tiers rather than the segment list.

| Slot | What fits |
| --- | --- |
| **10 min** (lightning) | Tier A only, and only three of the five: discovery, wrong-audience, one denial. No client, no Foundry, no audit walkthrough. |
| **25 min** (as built) | [RUNBOOK.md](RUNBOOK.md) as written. Tier A live, Tier B if on time. |
| **45 min** | Add the live MCP client properly, the delegation exchange, and the full audit trail. Take questions between segments instead of at the end. |
| **90 min / workshop** | Attendees run it themselves. Hand out [SETUP.md](SETUP.md), then work the scenarios in the order they appear in [COVERAGE-MATRIX.md](COVERAGE-MATRIX.md). The web UI (mode 2) is worth its weight here — a room full of people can see the same verdict without reading your terminal. |

### Choosing a deployment mode for the room

| Room | Mode | Why |
| --- | --- | --- |
| Normal conference stage | **1 — scripts** | Fewest moving parts. Rehearsed. No network needed. |
| Large room, back row cannot read a terminal | **2 — scripts + web UI** | Same services, bigger type, PASS/FAIL badges readable from distance |
| Remote or hybrid, attendees follow along | **4 — AKS** | One shared link. Set an access key. Tear it down the same day. |
| Workshop where attendees install nothing | **3 — Compose** or **4 — AKS** | Compose if they have Docker; AKS if they have a browser |
| Somebody else's laptop | **3 — Compose** | One `compose-up`, no Python version negotiation |

If you pick 3 or 4, read [DEPLOYMENT.md §5](DEPLOYMENT.md#5-when-the-image-build-cannot-reach-pypi) first. A blocked PyPI CDN is a common corporate-network condition and it fails the image build, not the demo.

### The week before

1. `check.ps1` or `check.sh` → `READY`. Not "mostly ready".
2. Walk [RUNBOOK.md](RUNBOOK.md) once against a clock, out loud.
3. Decide your Tier B cuts **now**, not on stage.
4. Re-read [RISKS-AND-FALLBACKS.md](RISKS-AND-FALLBACKS.md). Every entry there happened to someone.
5. If using mode 4, deploy and tear down once as a rehearsal. Never deploy for the first time on the day.

### The day of

- `start-all -Reset` at T-5, with services up. Reset keeps the signing key, so this is safe (see [SETUP.md](SETUP.md#reset-safety)).
- Confirm the clean ledger digest is `211597d92491`.
- Have `docs/CONTROL-MAP.md` open in a second window as the fallback slide.

### After

Add a row to the table at the top, copy the template below, and fill in the retrospective while it is still fresh. The gap between what you planned to say and what the room actually asked is the most useful thing this file can carry forward.

---

## Per-event template

```markdown
## N. <Event name> <year>

**<Talk title>**
<Presenter> · <YYYY-MM-DD> · <start>–<end> · <duration>

| | |
| --- | --- |
| Deployment mode | |
| Auth mode | |
| Network dependency | |
| Live MCP client | |
| Tier A segments | |
| Planned cuts if behind | |

**Retrospective**

| | |
| --- | --- |
| Actual finish time | |
| Segments cut | |
| Live client used | |
| Questions that landed | |
| Questions that exposed a gap | |
| What to change next time | |
```

---

## See also

- [RUNBOOK.md](RUNBOOK.md) — the timed schedule and the tier system
- [DEPLOYMENT.md](DEPLOYMENT.md) — the four ways to run it
- [RISKS-AND-FALLBACKS.md](RISKS-AND-FALLBACKS.md) — what goes wrong and what to do
- [ONSTAGE-SCRIPT.md](ONSTAGE-SCRIPT.md) — literal prompts and narration
