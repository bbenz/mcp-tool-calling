# Setup

Operator setup for the **"Who Can Call This MCP Tool?"** demo. Local-only setup takes about ten minutes and is all you need to run every scenario in the talk. The Entra and Azure sections are optional and were not deployed — read [§7](#7-optional-microsoft-entra-id-mode) before attempting them.

---

## 1. Prerequisites

| Requirement | Notes |
| --- | --- |
| **Python 3.12.10** | Install with `winget install Python.Python.3.12` (Windows) or from python.org. **Verify it is real**: `python --version` must print a version. If it opens the Microsoft Store, the Store alias stub is shadowing it — see below. |
| Git | Only for cloning and for the commit history. |
| ~200 MB disk | Virtual environment and dependencies. |
| Free TCP ports | `8800`, `8801`, `8802`, `8803` on localhost. |

No Azure subscription, no Entra tenant, and no network access are required for the local demo.

### If `python` opens the Microsoft Store

The Store alias stub exits silently and looks like a broken install. Either disable it in **Settings → Apps → Advanced app settings → App execution aliases** (turn off `python.exe` and `python3.exe`), or simply use the interpreter path directly. Every command in these docs uses the explicit venv path for exactly this reason. The `py` launcher is **not** installed on the presenting machine.

---

## 2. Bootstrap

```powershell
cd demo
.\scripts\bootstrap.ps1
```

Bash equivalent: `./scripts/bootstrap.sh`

This creates `demo/.venv`, upgrades pip, installs the project in editable mode with dev extras, and copies `.env.example` to `.env` if you do not already have one. It is safe to re-run; it will not overwrite an existing `.env`.

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

```powershell
.\scripts\start-all.ps1          # start all four services, wait for health
.\scripts\start-all.ps1 -Reset   # ...and reset the ledger to fixtures first
.\scripts\health.ps1             # one-line health for each service
.\scripts\check.ps1              # full verification: 78 tests + 14 scenarios
.\scripts\stop-all.ps1           # stop everything
```

`check.ps1` is the single command that proves the demo is ready. It prints `READY` only if every test and every scenario passed.

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

```powershell
.\scripts\scenario.ps1 allowed-refund     # one named scenario
.\scripts\scenario.ps1 -All               # all 14, in order
.\scripts\audit.ps1 -Last 5               # read the audit trail
.\scripts\reset.ps1                       # ledger back to fixtures
```

The 14 scenario names:

`no-token` · `discovery` · `missing-resource-indicator` · `pkce-downgrade` · `allowed-refund` · `scope-denial` · `ownership-denial` · `business-rule-denial` · `over-limit-denial` · `unapproved-client` · `wrong-audience` · `prompt-injection` · `annotation-tampering` · `token-passthrough-blocked`

Every scenario records the ledger digest before and after, so "nothing changed" is a printed fact rather than a claim.

### Reset safety

Reset is deliberately **not** an MCP tool. No model and no client can call it. It is an operator script (`refund_demo.reset`), it only ever removes files inside `demo/.local/`, and it **refuses to run when `AUTH_MODE=entra`** unless `ALLOW_RESET=1` is explicitly set — so it cannot be pointed at anything shared by accident.

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

## 8. Optional: Azure deployment

> **Never deployed.** `demo/infra/main.bicep` compiles cleanly with `az bicep build`, and that is the only claim made for it.

```powershell
cd demo\infra
.\deploy.ps1 -WhatIf          # review the plan and the cost note first
.\deploy.ps1
.\teardown.ps1                # scoped to the demo resource group only
```

See `demo/infra/README.md` for parameters, outputs, cost considerations, and teardown scope. Nothing in the 25-minute talk requires this.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `python` prints nothing, exits 0 | Microsoft Store alias stub | Use `.venv\Scripts\python.exe`, or disable the alias (§1) |
| Port already in use on start | Previous run not stopped | `.\scripts\stop-all.ps1`, then start again |
| Scenario hangs ~30 s then times out | A service died — check `.local/logs/<service>.log` | `stop-all.ps1` then `start-all.ps1` |
| `IDEMPOTENCY_KEY_REUSED` | Correct behaviour: a key was replayed with different parameters | `.\scripts\reset.ps1` |
| Ledger digest differs from a prior run | Scenarios ran without a reset | `.\scripts\start-all.ps1 -Reset` |
| `assess_refund` output is prefixed `[OFFLINE ASSESSMENT ...]` | No `FOUNDRY_ENDPOINT` configured | Expected offline. Set the endpoint for live inference. |
| Tests skip with "services not running" | Services are down | Start them; `conftest.py` skips e2e tests rather than failing them |
