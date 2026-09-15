# Setup

Operator setup for the **"Who Can Call This MCP Tool?"** demo. Local-only setup takes about ten minutes and is all you need to run every scenario in the talk. The Entra and Azure sections are optional and were not deployed — read [§7](#7-optional-microsoft-entra-id-mode) before attempting them.

This page covers the local setup. For the containerised and cloud options — Docker Compose and Azure Kubernetes Service — and for the optional web interface, see **[DEPLOYMENT.md](DEPLOYMENT.md)**. None of them are needed for the talk.

---

## 1. Prerequisites

| Requirement | Notes |
| --- | --- |
| **Python 3.12.10** | Install with `winget install Python.Python.3.12` (Windows) or from python.org. **Verify it is real**: `python --version` must print a version. If it opens the Microsoft Store, the Store alias stub is shadowing it — see below. |
| Git | Only for cloning and for the commit history. |
| ~200 MB disk | Virtual environment and dependencies. |
| Free TCP ports | `8800`, `8801`, `8802`, `8803` on localhost — plus `8080` if you use the web interface. |

No Azure subscription, no Entra tenant, and no network access are required for the local demo.

Only for the optional deployment modes in [DEPLOYMENT.md](DEPLOYMENT.md):

| Requirement | Needed for |
| --- | --- |
| Docker Desktop (Compose v2+) | Mode 3, local containers |
| `az` 2.88+ and `kubectl` 1.30+ | Mode 4, Azure Kubernetes Service |

Mode 4 does **not** need Docker: the image is built server-side by ACR Tasks.

### If `python` opens the Microsoft Store

The Store alias stub exits silently and looks like a broken install. Either disable it in **Settings → Apps → Advanced app settings → App execution aliases** (turn off `python.exe` and `python3.exe`), or simply use the interpreter path directly. Every command in these docs uses the explicit venv path for exactly this reason. The `py` launcher is **not** installed on the presenting machine.

---

## 2. Bootstrap

**All commands run from the `demo/` directory**, not the repository root:

```powershell
cd demo
.\scripts\bootstrap.ps1
```

Bash (including Git Bash on Windows):

```bash
cd demo
chmod +x scripts/*.sh      # only if your clone lost the executable bit
./scripts/bootstrap.sh
```

This creates `demo/.venv`, upgrades pip, installs the project in editable mode with dev extras, and copies `.env.example` to `.env` if you do not already have one. It is safe to re-run; it will not overwrite an existing `.env`.

Every operator command has both a `.ps1` and a `.sh` form. The bash scripts detect whether the virtual environment uses the POSIX `.venv/bin` layout or the Windows `.venv/Scripts` layout, so they work under Git Bash on Windows as well as under Linux and macOS.

### Choosing a shell (and a note on WSL)

| You are in | Use | Notes |
| --- | --- | --- |
| Windows PowerShell / `pwsh` | `.\scripts\*.ps1` | The rehearsed path. Use this on stage. |
| Git Bash on Windows | `./scripts/*.sh` | Shares the same Windows `demo/.venv`. |
| Linux, macOS | `./scripts/*.sh` | Bootstrap creates a POSIX `.venv/bin` layout. |
| WSL | `./scripts/*.sh`, **after its own bootstrap** | See below. |

A `.ps1` file **cannot** be executed by bash — `./scripts/scenario.ps1` from a bash prompt fails with `No such file or directory` (or a syntax error) because bash is not a PowerShell interpreter. Use the `.sh` twin, or invoke PowerShell explicitly: `pwsh scripts/scenario.ps1 wrong-audience`.

WSL is a **separate operating system**, so it needs its own virtual environment. `demo/.venv` created on Windows contains Windows binaries (`cryptography`, `pydantic-core`, and friends are compiled), and Linux cannot load them. The two layouts cannot coexist at the same path, so pick one per checkout: either work in Windows and use PowerShell or Git Bash, or work in WSL and run `./scripts/bootstrap.sh` *inside* WSL to build a Linux venv. Mixing them is the most common cause of confusing import errors.

---

## 3. Configuration

Configuration is read by `refund_demo.config` (pydantic-settings) from `demo/.env` and the process environment. `.env.example` is committed and contains **names and descriptions only — never values**.

The defaults work with no edits. The settings that matter:

| Setting | Default | Meaning |
| --- | --- | --- |
| `AUTH_MODE` | `devidp` | `devidp` = local authorization server. `entra` = Microsoft Entra ID. **Use `devidp` on stage.** |
| `DEVIDP_BASE_URL` | `http://localhost:8800` | Local authorization server. |
| `MCP_A_BASE_URL` | `http://localhost:8801` | Resource A — the refund MCP server. |
| `MCP_B_BASE_URL` | `http://localhost:8802` | Resource B — the second resource, used for the wrong-audience proof. |
| `UPSTREAM_BASE_URL` | `http://localhost:8803` | The refund API behind the MCP server. |
| `MCP_A_AUDIENCE` | `api://refund-mcp-a` | Resource A's App ID URI. |
| `MCP_B_AUDIENCE` | `api://refund-mcp-b` | Resource B's App ID URI. |
| `UPSTREAM_AUDIENCE` | `api://refund-upstream` | The upstream API's own audience — deliberately different from both MCP servers. |
| `FOUNDRY_ENDPOINT` | *(empty)* | Leave empty for the labelled offline assessment. Set to a real endpoint for live inference. |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | *(empty)* | Optional. When set, audit records are also exported to Azure Monitor. Empty = local-only telemetry. |

Local state (ledger, audit log, signing key, PID files, logs) lives in `demo/.local/`, which is git-ignored.

**Secrets are never committed.** `.gitignore` excludes `.env*` (except `.env.example`), `*.pem`, `*.pfx`, `*.key`, and the whole `.local/` directory.

---

## 4. Start, check, stop

| Task | PowerShell | Bash |
| --- | --- | --- |
| Start all four services | `.\scripts\start-all.ps1` | `./scripts/start-all.sh` |
| ...and reset the ledger first | `.\scripts\start-all.ps1 -Reset` | `./scripts/start-all.sh --reset` |
| Health of each service | `.\scripts\health.ps1` | `./scripts/health.sh` |
| **Full verification** | `.\scripts\check.ps1` | `./scripts/check.sh` |
| Stop everything | `.\scripts\stop-all.ps1` | `./scripts/stop-all.sh` |

`check` is the single command that proves the demo is ready. It prints `READY` only if every test and every scenario passed.

Expected healthy state:

```
  healthy  devidp    http://localhost:8800
  healthy  upstream  http://localhost:8803
  healthy  mcp-a     http://localhost:8801
  healthy  mcp-b     http://localhost:8802
```

Logs stream to `demo/.local/logs/<service>.log`. PIDs are tracked in `demo/.local/pids/`, so `stop-all.ps1` stops exactly the processes it started and nothing else.

---

## 5. Running scenarios

| Task | PowerShell | Bash |
| --- | --- | --- |
| One named scenario | `.\scripts\scenario.ps1 allowed-refund` | `./scripts/scenario.sh allowed-refund` |
| List the scenarios | `.\scripts\scenario.ps1` | `./scripts/scenario.sh` |
| All 14, in order | `.\scripts\scenario.ps1 -All` | `./scripts/scenario.sh --all` |
| Read the audit trail | `.\scripts\audit.ps1 -Last 5` | `./scripts/audit.sh 5` |
| Audit as raw JSON | `.\scripts\audit.ps1 -Last 3 -Raw` | `./scripts/audit.sh 3 --raw` |
| Ledger back to fixtures | `.\scripts\reset.ps1` | `./scripts/reset.sh` |

The 14 scenario names:

`no-token` · `discovery` · `missing-resource-indicator` · `pkce-downgrade` · `allowed-refund` · `scope-denial` · `ownership-denial` · `business-rule-denial` · `over-limit-denial` · `unapproved-client` · `wrong-audience` · `prompt-injection` · `annotation-tampering` · `token-passthrough-blocked`

Every scenario records the ledger digest before and after, so "nothing changed" is a printed fact rather than a claim.

### Reset safety

Reset is deliberately **not** an MCP tool. No model and no client can call it. It is an operator script (`refund_demo.reset`), it only ever removes files inside `demo/.local/`, and it **refuses to run when `AUTH_MODE=entra`** unless `ALLOW_RESET=1` is explicitly set — so it cannot be pointed at anything shared by accident.

It also **keeps the local signing key**, which is why it is safe to run between segments with the services still up — exactly how the runbook uses it. The key is infrastructure, not demo state: deleting it underneath running services makes `devidp` mint tokens with a new key while every service still serves and caches the old JWKS, and the demo then fails with misleading `invalid_token` errors that only a full restart clears.

If you genuinely want a fresh key, stop the services first and pass `-NewKey` (`--new-key` in bash). Rotating the key is **refused while `devidp` is listening**, so the footgun is not reachable by accident.

### Optional: the web view

A browser view over the same scenarios, for a room where the back row cannot read a terminal. Start the four services first, then:

| Task | PowerShell | Bash |
| --- | --- | --- |
| Serve the UI on `:8080` | `.\scripts\web.ps1` | `./scripts/web.sh` |
| On another port | `.\scripts\web.ps1 -Port 9000` | `./scripts/web.sh --port 9000` |

It is a **reporting surface, not a decision point** — every allow and deny it shows was decided by the MCP server, and the page holds no policy of its own. Reset is disabled over HTTP by default, runs are serialized so two clicks cannot interleave against one ledger, and no token or PKCE verifier ever reaches the page. Details and the optional access key: [DEPLOYMENT.md §2](DEPLOYMENT.md#2-scripts-plus-the-web-ui).

---

## 6. Presenter client configuration (Copilot / VS Code)

The demo runs end to end from `scripts\scenario.ps1` with no MCP client at all. Connecting a real client is what makes the **approval** story tangible, so do it if you can, but keep it off the critical path.

`demo/client-config/mcp.json.example` contains a secret-free server entry. **Merge** it into your existing client MCP configuration — do not overwrite the file, you will lose your other servers.

```jsonc
{
  "servers": {
    "refund-demo": {
      "type": "http",
      "url": "http://localhost:8801/mcp"
    }
  }
}
```

There is no secret and no token in this file. The client discovers the authorization server from the 401 challenge and runs its own OAuth flow — which is precisely the behaviour being demonstrated.

**Record the pinned client version here during rehearsal:**

| Field | Value |
| --- | --- |
| Client | *(e.g. VS Code + GitHub Copilot)* |
| Version | `__________` ← fill in at rehearsal, re-check the morning of the talk |
| Verified on | `__________` |

Two things must be confirmed by hand, because no automated test can prove a UI worked — use `docs/CLIENT-APPROVAL-CHECKLIST.md`.

⚠️ **Redirect URIs are an open item.** The exact callback URI your client uses could not be verified without a live client. If registration fails, read the URI out of the client's own error message and register that. See `demo/identity/README.md`.

---

## 7. Optional: Microsoft Entra ID mode

> **Not verified.** No tenant access was authorized during the build, so the MSAL on-behalf-of path and live Entra discovery have **never been executed**. The scripts are written and reviewed, not proven. Budget real time, and never switch modes on the day of the talk.

```powershell
cd demo\identity
.\setup-entra.ps1 -TenantId <guid> -WhatIf   # review first
.\setup-entra.ps1 -TenantId <guid>
```

Creates three app registrations (Resource A, Resource B, upstream API), exposes delegated scopes, sets authorized client applications, and prints the values for `.env`. Requires **Application Administrator** or **Cloud Application Administrator**, plus a Privileged Role Administrator for admin consent.

Entra app registrations **cannot** be created by Bicep. This is a directory operation and is handled by these scripts through Microsoft Graph — anyone claiming otherwise is describing something that does not exist.

The public client gets **no secret**. The confidential middle-tier uses a certificate, not a shared secret.

---

## 8. Optional: containers and Azure

Three deployment options beyond the operator scripts. **None of them are needed for the 25-minute talk**, and none of them change the script-based demo. Full instructions: **[DEPLOYMENT.md](DEPLOYMENT.md)**.

### Docker Compose — five containers locally

| Task | PowerShell | Bash |
| --- | --- | --- |
| Build and start | `.\scripts\compose-up.ps1` | `./scripts/compose-up.sh` |
| Stop | `.\scripts\compose-down.ps1` | `./scripts/compose-down.sh` |
| Stop and wipe state | `.\scripts\compose-down.ps1 -Volumes` | `./scripts/compose-down.sh --volumes` |

Both wrappers wait for all five containers to report healthy before printing the URL. Note that inside the Compose network the services advertise each other by service name, so a host MCP client will not resolve them — use the script path for the live-client segment.

> **Verified end to end.** The image builds and all 14 scenarios pass inside Compose, with the clean-ledger digest matching the laptop exactly. If `docker compose build` fails on a TLS error from `files.pythonhosted.org`, that is your network, not the Dockerfile — see [DEPLOYMENT.md §5](DEPLOYMENT.md#5-when-the-image-build-cannot-reach-pypi), which has three workarounds.

### Azure Kubernetes Service — one pod, five containers

> **Never deployed.** Manifests are schema-checked and pinned by 46 tests; no cluster was created, because no subscription was authorized.

| Task | PowerShell | Bash |
| --- | --- | --- |
| Deploy | `.\scripts\aks-up.ps1` | `./scripts/aks-up.sh` |
| **Tear down** | `.\scripts\aks-down.ps1` | `./scripts/aks-down.sh` |

Creates a resource group, an ACR, and a small AKS cluster; builds the image with `az acr build` (server-side, so a blocked local PyPI does not matter); applies `demo/k8s/`; prints a public URL with a generated access key. Only the web container is exposed — `devidp` mints tokens for anyone who asks and must never get a public address.

**Tear it down the same day.** A demo cluster left running over a conference weekend is a real bill.

### Bicep — App Service / Container Apps

> **Never deployed.** `demo/infra/main.bicep` compiles cleanly with `az bicep build`, and that is the only claim made for it.

```powershell
cd demo\infra
.\deploy.ps1 -WhatIf          # review the plan and the cost note first
.\deploy.ps1
.\teardown.ps1                # scoped to the demo resource group only
```

See `demo/infra/README.md` for parameters, outputs, cost considerations, and teardown scope.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `./scripts/scenario.ps1: No such file or directory` in bash | Two separate causes: bash cannot execute PowerShell, **and** you are probably in the repo root rather than `demo/` | `cd demo`, then use the bash script: `./scripts/scenario.sh wrong-audience`. To run the PowerShell one from bash, call it through PowerShell: `pwsh demo/scripts/scenario.ps1 wrong-audience` |
| `scenario.ps1 : The term ... is not recognized` | Running from the repo root | Either `cd demo` first, or use the full path — the scripts locate `demo/` themselves, so `.\demo\scripts\scenario.ps1 wrong-audience` works from the root |
| `no virtualenv found` from a `.sh` script | The venv has not been created, or was created for the other platform | Run `./scripts/bootstrap.sh` in the *same* shell family you intend to use (see §2) |
| `python` prints nothing, exits 0 | Microsoft Store alias stub | Use `.venv\Scripts\python.exe`, or disable the alias (§1) |
| Port already in use on start | Previous run not stopped | `.\scripts\stop-all.ps1`, then start again |
| Scenario hangs ~30 s then times out | A service died — check `.local/logs/<service>.log` | `stop-all` then `start-all` |
| Every call suddenly fails `invalid_token` after a reset | The signing key was rotated underneath running services | Should no longer be reachable — reset keeps the key and refuses `-NewKey` while `devidp` listens. If you see it, `stop-all` then `start-all -Reset` |
| `IDEMPOTENCY_KEY_REUSED` | Correct behaviour: a key was replayed with different parameters | `.\scripts\reset.ps1` |
| Ledger digest differs from a prior run | Scenarios ran without a reset | `.\scripts\start-all.ps1 -Reset` |
| `assess_refund` output is prefixed `[OFFLINE ASSESSMENT ...]` | No `FOUNDRY_ENDPOINT` configured | Expected offline. Set the endpoint for live inference. |
| Tests skip with "services not running" | Services are down | Start them; `conftest.py` skips e2e tests rather than failing them |
| `docker compose build` fails with `SSLV3_ALERT_HANDSHAKE_FAILURE` on `files.pythonhosted.org` | The network allows `pypi.org` but blocks the wheel CDN | Not a Dockerfile problem. Deploy to AKS instead (`az acr build` runs server-side), point the build at an internal mirror with `--build-arg PIP_INDEX_URL=...`, or use the script path. [DEPLOYMENT.md §5](DEPLOYMENT.md#5-when-the-image-build-cannot-reach-pypi) |
| `compose-up` times out waiting for healthy containers | A service failed to start inside its container | `docker compose -f docker/docker-compose.yml logs <service>` |
| Web UI loads but every call is `invalid_token` under Compose | Issuer and resource URLs disagree with the network addresses | All five containers must share one `DEVIDP_ISSUER` and one set of `MCP_*_PUBLIC_URL`. They are set together in `docker/docker-compose.yml`; changing one alone breaks audience validation |
| A host MCP client cannot reach the server under Compose | Metadata advertises `http://mcp-a:8801`, which only resolves inside the Compose network | Expected. Use the script-based demo for the live-client segment |
| Web UI returns `401 access key required` | `WEB_ACCESS_KEY` is set | Append `?k=<key>` to the URL, or send `X-Demo-Key`. `/health` is deliberately exempt so probes keep working |
| Reset button does nothing / `403` | Reset is off over HTTP by default | Correct behaviour. Use `.\scripts\reset.ps1`, or set `WEB_ALLOW_RESET=1` locally — never on a public address |
| `aks-up` fails at `az acr build` | Not signed in, or no subscription selected | `az login`, then `az account set --subscription <id>` |
| AKS pod is `CrashLoopBackOff` | Most often a container cannot write its state directory | `kubectl -n refund-demo logs <pod> -c <container>`. The pod sets `fsGroup: 10001`, which is what makes the `emptyDir` writable by the non-root user |
| AKS Service has no external IP | Load balancer still provisioning | `kubectl -n refund-demo get svc refund-demo-web -w`. Give it a few minutes |
| Tool calls fail with `421 Misdirected Request` in containers | The MCP transport's DNS rebinding protection allows only loopback `Host` headers, and under Compose the Host header is the service name | Add the hostname to `MCP_ALLOWED_HOSTS` (Compose already sets `mcp-a:*,mcp-b:*`). Do **not** disable the protection. The OAuth handshake succeeding first makes this look like a token bug; it is not |
| `docker compose build` fails on `No matching distribution found for pywin32` | `requirements.txt` is frozen on Windows and something Windows-only lost its marker | Append `; sys_platform == "win32"` to the pin. `test_requirements_mark_windows_only_pins` catches this before a build does |
| Dozens of `httpx.ConnectError` failures from `pytest` | The Compose stack is holding ports 8800–8803, so the tests cannot bind their own services | `.\scripts\compose-down.ps1` first, then re-run. Nothing is broken |
| `allowed-refund` fails on a **second** Compose run | The `demo-state` volume survives `compose-down`, so the order was already refunded — the demo is correctly refusing to double-spend | `.\scripts\compose-down.ps1 -Volumes` to wipe state, or run `.\scripts\reset.ps1` inside the stack. This is the same reason you reset before going on stage |
