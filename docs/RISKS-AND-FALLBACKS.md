# Risks And Fallbacks

Every realistic failure mode, how the presenter detects it **within seconds**, and the exact prepared fallback.

**The principle:** each failure has a decision already made. On stage you execute a decision; you do not make one. Anything that takes more than ~10 seconds to diagnose gets its fallback, immediately.

**Single biggest mitigation:** the entire Tier A path runs **offline, locally, with no cloud dependency**. The conference network cannot take the demo down. Prove it at T-60 by running `scenario.ps1 allowed-refund` with Wi-Fi disabled.

---

## Risk register

### R1 · Expired access token

| | |
| --- | --- |
| **Likelihood** | Low locally · Medium in `entra` mode |
| **Detection** | `AUTH_TOKEN_EXPIRED` in the scenario output — immediate |
| **Why it is unlikely** | `devidp` issues 1-hour tokens (`ACCESS_TOKEN_TTL_SECONDS = 3600`) and **every scenario acquires a fresh token when it runs**. A token would have to be older than the whole talk. |
| **Fallback** | Re-run the scenario; it mints a new token. If a live client is stuck, disconnect and reconnect it — or drop to `scenario.ps1`, which never depends on client token state. |
| **Prevention** | `.\scripts\check.ps1` at T-60 forces a full fresh acquisition. |

### R2 · Client update changed the OAuth or MCP behaviour

| | |
| --- | --- |
| **Likelihood** | **Medium — this is the most likely thing to break.** Clients auto-update. |
| **Detection** | At T-60: the client fails to connect, or prompts differently than rehearsed |
| **Fallback** | **Do not debug on stage.** The client is Tier B in its entirety. Every claim it supports is proven by `scripts\scenario.ps1`, which has no client dependency. Say: *"I'm going to show this through the protocol trace instead — same flow, fewer moving parts."* |
| **Prevention** | Pin and record the client version in `docs/SETUP.md` §6. **Disable client auto-update for the week of the talk.** Re-run `docs/CLIENT-APPROVAL-CHECKLIST.md` after any update. |

### R3 · Cold start / service not ready

| | |
| --- | --- |
| **Likelihood** | Low locally · High for a first cloud deploy |
| **Detection** | First scenario hangs, or `health.ps1` shows a service not green — under 5 s |
| **Fallback** | `.\scripts\stop-all.ps1; .\scripts\start-all.ps1` — about 10 seconds to all-healthy. Narrate the control map while it restarts; that segment has words that do not need a terminal. |
| **Prevention** | `start-all.ps1` blocks on health before returning. Run `check.ps1` at T-60 to warm every code path — the first JWKS fetch and first SQLite open are the only slow ones, and they happen there. |

### R4 · Conference network is unusable

| | |
| --- | --- |
| **Likelihood** | **High. Assume it.** |
| **Detection** | Anything network-bound stalls |
| **Fallback** | **None needed for Tier A.** All four services are `localhost`; the ledger is local SQLite; `devidp` is local; the audit view reads a local file. Foundry falls back to a labelled offline assessment. The only casualties are the live Foundry call (Tier B) and the Application Insights query (Tier C). |
| **Prevention** | **Run the airplane-mode test at T-60.** If `allowed-refund` passes with Wi-Fi off, the network cannot hurt you. |

### R5 · Foundry throttling, latency, or quota

| | |
| --- | --- |
| **Likelihood** | Medium |
| **Detection** | > 3 s with no output during `assess_refund` |
| **Fallback** | `foundry.py` falls back automatically and returns `live: false` with the prefix `[OFFLINE ASSESSMENT - NO MODEL WAS CALLED]`. **Read that label out loud** — do not let it pass as live output. |
| **Why this costs nothing** | The model has **no authority in this demo**. Its output is advisory and the talk says so. An offline assessment demonstrates the same point: advice is not a decision. |
| **Prevention** | Leave `FOUNDRY_ENDPOINT` empty unless you have rehearsed the live call and are on schedule at 07:00. |

### R6 · Telemetry ingestion delay

| | |
| --- | --- |
| **Likelihood** | **High** — Application Insights commonly lags 2–5 minutes |
| **Detection** | The KQL query returns nothing for a call you just made |
| **Fallback** | **Do not wait for ingestion on stage.** Use `.\scripts\audit.ps1 -Last 6` — it reads the local JSONL file and is instantaneous. The KQL query is Tier C and is printed in `docs/APPENDIX.md` for attendees to read later. |
| **Prevention** | Plan to skip the portal entirely. If you do show it, run the query against data generated at T-60, not on stage. |

### R7 · Model nondeterminism during the injection demo

| | |
| --- | --- |
| **Likelihood** | **High — and it does not matter.** |
| **Detection** | The model's response differs from rehearsal |
| **Fallback** | **None needed. This is designed in.** The harness records what the model did, then forces the candidate `refund_order` call regardless, and the server denies it. Say: *"Whatever the model just decided is irrelevant — I'm forcing the call through anyway."* |
| **Honesty requirement** | Label the forced call a **harness replay**, not a fresh model attack. Never present model refusal as the security boundary — that is the exact mistake the segment exists to correct. |

### R8 · Consent prompt does not reappear

| | |
| --- | --- |
| **Likelihood** | **High** on a second run — clients cache tokens aggressively |
| **Detection** | Connect and no dialog appears |
| **Fallback** | Carry on. Consent is Tier B and the discovery mechanics are fully shown by `scenario.ps1 discovery`. Say: *"my client already has a token — which is exactly why the server still validates every single call."* That turns the failure into the point. |
| **Prevention** | `docs/CLIENT-APPROVAL-CHECKLIST.md` §D at T-60. **Never debug client caches on stage.** |

### R9 · Ledger in an unexpected state

| | |
| --- | --- |
| **Likelihood** | Medium — rehearsing without a reset |
| **Detection** | A digest that is not the clean-start `211597d92491`, or `IDEMPOTENCY_KEY_REUSED` |
| **Fallback** | `.\scripts\reset.ps1` — instant, scoped to `demo\.local\`, and safe with the services running. If `IDEMPOTENCY_KEY_REUSED` appears, **say what it is**: correct behaviour, refusing to replay a key against different parameters. It is a feature demonstrating itself at an awkward moment. |
| **Prevention** | `.\scripts\reset.ps1` at T-5. Reset is not an MCP tool, so no model and no client can trigger it. |

### R9b · A reset invalidates every token

*Found during dress rehearsal, and fixed — recorded because the failure mode is instructive and the fix is load-bearing.*

| | |
| --- | --- |
| **Likelihood** | Was **high** — the runbook asks for a reset at T-5 with the services already up. Now prevented in code. |
| **Detection** | Every call fails `invalid_token` / `KeyError: 'access_token'` immediately after a reset, with nothing obviously wrong in the logs |
| **Cause** | Reset used to delete the local signing key. The file regenerates on demand, so it looked harmless — but `devidp` then minted tokens with a **new** key while every running service went on serving and caching the **old** JWKS. Nothing validates, and no amount of resetting fixes it. |
| **Fallback** | `.\scripts\stop-all.ps1` then `.\scripts\start-all.ps1 -Reset`. A full restart is the only cure once it happens. |
| **Prevention** | Reset now **keeps the key** (it is infrastructure, not demo state), and rotating it with `-NewKey` is **refused while `devidp` is listening**. Pinned by `tests/test_reset.py`. |

### R10 · Port already in use

| | |
| --- | --- |
| **Likelihood** | Medium |
| **Detection** | `start-all.ps1` reports a bind failure — immediate |
| **Fallback** | `.\scripts\stop-all.ps1` (uses tracked PIDs from `.local/pids/`, so it stops only what it started), then start again. |
| **Prevention** | Always `stop-all.ps1` before closing the laptop. |

### R11 · `mcp` SDK upgraded and broke an API

| | |
| --- | --- |
| **Likelihood** | Low if you leave it alone · **Certain if you run `pip install -U` the night before** |
| **Detection** | Import errors or `check.ps1` failing |
| **Fallback** | `pip install -r requirements.txt --force-reinstall` restores the exact 55 pinned versions. |
| **Prevention** | **Do not upgrade inside 72 hours of the talk.** `docs/COMPATIBILITY-RECORD.md` §2 lists the seven API facts to re-verify if you ever do. |

### R12 · Laptop sleeps, locks, or shows a notification

| | |
| --- | --- |
| **Likelihood** | Medium |
| **Detection** | Obvious and painful |
| **Fallback** | Services survive a lock; unlock and continue. If the machine slept, `health.ps1` then `start-all.ps1` if needed. |
| **Prevention** | T-60 checklist: mains power, sleep off, screensaver off, Focus Assist on, chat apps quit. |

### R13 · Live client authentication stalls mid-demo

| | |
| --- | --- |
| **Likelihood** | Medium |
| **Detection** | Browser or client sign-in still spinning after ~20 s |
| **Fallback** | Abandon it mid-flow — `Esc`, back to Terminal A, run the equivalent scenario. Rehearse this transition once so it looks deliberate. |
| **Prevention** | Only attempt interactive sign-in if you are **ahead** at 02:00. |

### R14 · Running long

| | |
| --- | --- |
| **Likelihood** | **High.** Everyone runs long. |
| **Detection** | Elapsed time past a segment's stop-time in `RUNBOOK.md` |
| **Fallback** | **The 45-second rule.** More than 45 s over a stop-time → prepared artifact, move on. Cut Tier C first (narration depth, code walkthroughs, KQL), then Tier B (live client, live model). **Never cut Tier A.** |
| **Prevention** | Segment 6 contains deliberate recovery buffer. A timed rehearsal at T-24 with real numbers written down. |

### R15 · Total terminal or machine loss

| | |
| --- | --- |
| **Likelihood** | Low |
| **Detection** | Obvious |
| **Fallback** | Slides plus `docs/COVERAGE-MATRIX.md`. Every claim has a named scenario, a named test, and an expected-evidence column — read them. State plainly that you are describing recorded results. **The coverage matrix is the disaster-recovery artifact.** |
| **Prevention** | Keep `COVERAGE-MATRIX.md` and `CONTROL-MAP.md` open in a browser tab and on a phone. |

### R16 · Container image build fails on a blocked package index

| | |
| --- | --- |
| **Likelihood** | **Seen once on the build machine, then cleared on its own** · Medium on any corporate network |
| **Detection** | `docker compose build` dies on the `pip install` layer with `SSLV3_ALERT_HANDSHAKE_FAILURE` against `files.pythonhosted.org` — within about ten seconds |
| **Why it happens** | Some networks allow `pypi.org` (the index) but block the CDN that serves the wheels. Resolution starts, then the first download dies at TLS. It is the network, not the Dockerfile — reproduced identically from the host and from inside the build, and it stopped happening without any change to this repository. |
| **Fallback** | **Do not debug this on the day.** Three ways past it, in order: deploy to AKS instead (`az acr build` runs server-side and is unaffected); pass `--build-arg PIP_INDEX_URL=<internal mirror>`; or drop to the script-based demo, which needs no image at all. |
| **Prevention** | Build the image at home, on a network you control, before you need it — and keep that image, because a venue network can reintroduce this. `curl -o /dev/null -w '%{http_code}' https://files.pythonhosted.org/simple/` is a one-second check: `404` means reachable, a TLS error means blocked. |

### R17 · AKS deployment not ready in time

| | |
| --- | --- |
| **Likelihood** | Low now that the path has been proven end to end — but still medium on a first attempt from an unrehearsed machine |
| **Detection** | `aks-up` stalls at cluster creation or at `rollout status`, or the Service never gets an external IP |
| **Why it happens** | `az aks create` takes several minutes on a good day, and load-balancer IP assignment is not instant. Quota, region capacity, and ACR attachment are all ways a first run stops. The one proven run took roughly 8 minutes end to end. |
| **Fallback** | The cloud path is **never on the critical path**. Close the tab and run the demo locally; nothing in the 25 minutes requires it. |
| **Prevention** | **Deploy and tear down once as a rehearsal, days ahead.** Never deploy for the first time on the day of a talk. `kubectl -n refund-demo get pods` and `kubectl -n refund-demo logs <pod> -c <container>` are the only two diagnostics worth running. If `az acr build` dies with a `charmap` codec error, the image almost certainly built anyway — check `az acr task list-runs --registry <registry> --top 1 -o table` before re-running anything. |

### R18 · Cloud demo left running after the event

| | |
| --- | --- |
| **Likelihood** | **High if not scheduled** — this one costs money *and*, on plain HTTP, credibility |
| **Detection** | None. That is the problem: nothing fails, the bill just accrues, and the endpoint stays reachable |
| **Fallback** | `.\scripts\aks-down.ps1` / `./scripts/aks-down.sh` deletes the whole resource group — cluster, registry, load balancer, public IP, managed identity — and clears the stale kubeconfig entry. |
| **Prevention** | Tear down the **same day**, before you leave the venue. The deploy script prints the teardown command in its final output for exactly this reason. Put a calendar reminder on the day you deploy, not the day after. Cost is roughly **$0.10–0.12/hour**. |

### R19 · The cloud link is shared over plain HTTP

| | |
| --- | --- |
| **Likelihood** | Certain if you put the URL on a slide at a conference |
| **Detection** | None in-band. Assume the key is public the moment the link is used on a shared network |
| **Why it happens** | The Service is HTTP with no TLS, and the access key travels as `?k=` in the URL. Anyone on the path — venue Wi-Fi, a proxy, any transit hop — reads it from one request. They then have the whole app: run scenarios, **move the ledger digest you are about to show**, read the audit trail. It reaches nothing real and cannot pivot into Azure (`automountServiceAccountToken: false`). |
| **Fallback** | Redeploy for a clean ledger and a fresh key — about 8 minutes, or under 2 if the cluster still exists. Or drop to mode 1, which needs no network at all. |
| **Prevention** | Treat the link as **single-session and disposable**. For anything more exposed, add `loadBalancerSourceRanges` to `k8s/service.yaml`, make the Service internal and use `kubectl port-forward`, or front it with an HTTPS ingress. Full detail in [DEPLOYMENT.md §8](DEPLOYMENT.md#8-security-posture-of-the-cloud-mode). |

---

These are not failure modes — they are things that must be said regardless of how well the demo runs. Omitting them under time pressure would be a more serious failure than any crash above.

| Commitment | Where |
| --- | --- |
| Resource binding stops **cross-resource reuse**, not replay at the intended resource | Segment 2 |
| A cancelled request is **client-only evidence** — the server never saw it | Segment 4 |
| The forced injection call is a **harness replay**, not a fresh model attack | Segment 5 |
| Model refusal is **not** the security boundary | Segment 5 |
| The audit log is a JSONL file — **not immutable, not tamper-proof** | Segment 6 |
| Entra mode and the Azure deployment are **implemented but unexecuted** — no tenant or subscription was authorized | Q&A, if asked |
| The **`aks-up.sh` bash deploy path has never driven a real deployment** — the verified cloud run used the PowerShell script | Q&A, if asked |
| One pod with five containers is a **demo shape, not a hosting recommendation** — the SQLite ledger makes one writer a hard constraint | Q&A, if asked |
