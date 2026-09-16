# Compatibility Record

**Recorded:** 2026-09-14 · **Talk:** 2026-10-06, MCP Dev Summit Toronto · **Re-verify by:** 2026-10-03

This is the Phase 0 gate output. Every version below was read from the machine that will present, not from documentation. Re-run `scripts\check.ps1` and re-read this file within three days of the talk; the MCP ecosystem moves faster than a conference schedule.

---

## 1. Verified environment

| Component | Version | How it was verified |
| --- | --- | --- |
| OS | Windows 11 (10.0.26200) | `platform.platform()` |
| Python | **3.12.10** | `sys.version` — installed via `winget install Python.Python.3.12` |
| MCP Python SDK | **2.2.0** | `importlib.metadata.version("mcp")` |
| MCP protocol revision | **2026-07-28** | `mcp.types.LATEST_PROTOCOL_VERSION` |
| starlette | 1.6.0 | metadata |
| uvicorn | 0.52.4 | metadata |
| PyJWT | 2.13.0 | metadata |
| cryptography | 50.0.1 | metadata |
| httpx | 0.28.1 | metadata |
| httpx2 | 2.12.0 | pulled in by `mcp` 2.2.0 for its own client transport |
| pydantic | 2.13.5 | metadata |
| pydantic-settings | 2.15.0 | metadata |
| msal | 1.38.0 | metadata (Entra path only) |
| openai | 3.8.0 | metadata (Foundry path only) |
| azure-identity | 1.25.3 | metadata (Foundry path only) |
| pytest | 9.1.1 | metadata |
| PyYAML | 6.0.3 | metadata — pulled in by `uvicorn[standard]`; used by the deployment-manifest tests |

Exact pins for a reproducible rebuild are in `demo/requirements.txt` (55 packages, generated with `pip freeze`).

Tooling used for the optional deployment paths:

| Component | Version | How it was verified |
| --- | --- | --- |
| Docker Engine | 29.8.0 (linux containers) | `docker version` |
| Docker Compose | v5.5.1 | `docker compose version` |
| Azure CLI | 2.88.0 | `az version` |
| kubectl | v1.36.1 | `kubectl version --client` |

### The package CDN was blocked on this machine, then cleared

`pypi.org` responded normally (HTTP 200), but `files.pythonhosted.org` — the CDN that serves the actual wheels — failed the TLS handshake:

```
curl: (35) schannel: ... SEC_E_ILLEGAL_MESSAGE
pip: SSLError(1, '[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ...')
```

Reproduced identically from the host and from inside a `docker build`. **It cleared a day later without any change on this machine**, and the image then built on the first attempt. That timing matters for the record: it was a network condition, not a repository defect, and it can return in a conference venue.

It still shaped one permanent decision and one temporary one:

1. **Permanent: the web UI is built on Starlette, not FastAPI.** Starlette was already a dependency of the MCP SDK, so it needed no install at a moment when no install was possible. Starlette is what FastAPI is built on; for a handful of JSON routes and one HTML page the difference is an import. It stays as-is — it works, it is tested, and swapping it now would add a dependency for no gain.
2. **Resolved: the container image is now built and exercised.** While the block was active the AKS scripts were written to build server-side with `az acr build`, which remains the right design — it keeps the cloud path independent of laptop egress. See [DEPLOYMENT.md §5](DEPLOYMENT.md#5-when-the-image-build-cannot-reach-pypi) and risk R16.

Re-check before relying on Compose at an event:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://files.pythonhosted.org/simple/   # 404 = reachable
```

### Python was not present

The presenting machine had **no Python installation** — only the Windows Store alias stub, which exits silently and is easy to mistake for a working interpreter. Python 3.12.10 was installed as a hard prerequisite.

Consequence for the runbook: **use `.venv\Scripts\python.exe` explicitly.** A bare `python` may resolve to the Store stub, and the `py` launcher is not installed.

---

## 2. MCP SDK API facts that shaped the implementation

These were established by introspecting the installed SDK, because the v2 API differs from widely published v1 examples.

| Fact | Consequence |
| --- | --- |
| Server class is `mcp.server.mcpserver.MCPServer` | Not `FastMCP`. v1 samples will not run. |
| `TokenVerifier` is a Protocol with `async def verify_token(token) -> AccessToken \| None` | Returning `None` is what produces the 401 challenge. |
| `AccessToken` carries `token, client_id, scopes, expires_at, resource, subject, claims` | `claims` is how validated claims reach the tool layer without re-parsing. |
| `AuthSettings(issuer_url, resource_server_url, required_scopes, validate_token_resource, ...)` | Drives the Protected Resource Metadata document the SDK publishes. |
| `validate_token_resource` compares `AccessToken.resource` to `resource_server_url` | Set to **`False`** here, with justification below. |
| `get_access_token()` from `mcp.server.auth.middleware.auth_context` | The only trustworthy identity source inside a tool. |
| Deliberate tool failures must raise `mcp.server.mcpserver.exceptions.ToolError` | Any other exception is replaced with a generic `Error executing tool <name>`, and the denial reason never reaches the client. |
| Result model fields are snake_case: `is_error`, `structured_content` | camelCase attribute reads silently return `False`/`None`. |
| Client transport is `streamable_http_client(url, http_client=...)` yielding `(read, write)` | Not `streamablehttp_client`. |

### Why `validate_token_resource=False`

The SDK's built-in check asserts that the token's `resource` value equals `resource_server_url` (an HTTP URL). Our tokens are audience-bound to an **App ID URI** (`api://refund-mcp-a`), which is what Entra issues and what the RFC 8707 `resource` indicator names here. Those two strings are legitimately different.

Turning the SDK check off does **not** turn off audience validation. `refund_demo.tokens.TokenValidator` verifies `aud` against this resource's own accepted identifiers on every request, and rejects anything else with `AUTH_WRONG_AUDIENCE`. This is the configuration the SDK documents for servers that validate the audience themselves. Leaving the flag unset emits an `MCPDeprecationWarning`.

Evidence that the binding still holds: `tests/test_tokens.py::test_token_for_resource_b_is_rejected_at_resource_a` and the `wrong-audience` scenario.

---

## 3. Defects found and fixed during the build

Recorded because each one would have produced a misleading demo.

| # | Defect | Symptom it would have caused on stage | Fix |
| --- | --- | --- | --- |
| 1 | Policy rule R007 was unreachable — R006 already denied the same case | A rule shown on screen that can never fire | Removed; R006 documented as *the* confused-deputy boundary |
| 2 | Blocking JWKS fetch inside the dev IdP's own async `/token` handler | On-behalf-of exchange deadlocked; refunds timed out | Validation moved to a worker thread (`anyio.to_thread.run_sync`) in the IdP, the MCP verifier, and the upstream API |
| 3 | Denials raised a plain `Exception` | Client saw `Error executing tool refund_order` with no reason | `ToolDenied` now subclasses `ToolError`; reason code and rule ID reach the client |
| 4 | Ledger fingerprint had no single comparable value | "Nothing changed" was not provable at a glance | Added a SHA-256 `digest` over refund count and per-order totals |
| 5 | Replaying an idempotency key with a **different amount** returned the original refund | A second, different request would report success it never got | Mismatched replays now raise `IDEMPOTENCY_KEY_REUSED` |
| 6 | Dead `REQUIRED_SCOPES` mapping in `policy.py` | Misleading code during a walkthrough | Removed |
| 7 | `audit.write()` never emitted to the logger | The Application Insights KQL query in the appendix matched **nothing** on stage | Audit records now mirrored to the `refund_demo` logger as `customDimensions`, wrapped so telemetry can never break an audit write |
| 8 | `devidp` never called `telemetry.configure()` | The one service missing from any trace | `configure("devidp")` in `create_app()` |
| 9 | Reset deleted the local signing key | **Every call fails `invalid_token` after the T-5 reset.** The key regenerates, so `devidp` mints tokens with a new key while running services still serve and cache the old JWKS. Only a full restart recovers. | Reset keeps the key by default; `--new-key` is refused while `devidp` is listening. Pinned by `tests/test_reset.py` (R9b) |
| 10 | Bash operators had no `scenario`/`audit` scripts, and every `.sh` hardcoded `.venv/bin/python` | The two most-used stage commands were PowerShell-only, and no `.sh` ran under Git Bash on Windows | Added `scenario.sh`, `audit.sh`, and `_common.sh`, which resolves `.venv/bin` or `.venv/Scripts` |
| 11 | `scenario list` printed blank descriptions | The list of what the demo can show was unreadable — the claim lived in a `claim=` keyword argument, not in a docstring, so the listing had nothing to read | Introduced a canonical `CLAIMS` dict as the single source for both the listing and each result, pinned by a drift test |
| 12 | `requirements.txt` pinned `pywin32==312` with no environment marker | **The container image could not be built at all** — `pip` stopped at `No matching distribution found for pywin32`, because it has no Linux build. The file was frozen on Windows, so the laptop never noticed | Marked `; sys_platform == "win32"`. `test_requirements_mark_windows_only_pins` fails on any unmarked Windows-only pin |
| 13 | Both MCP servers called `streamable_http_app()` with no transport settings | **Every tool call failed with `421 Misdirected Request` in containers**, but only *after* a fully successful OAuth handshake — so it read as a token bug when it was a transport bug. The SDK auto-enables DNS rebinding protection for loopback servers and then allows only `localhost`-ish `Host` headers; under Compose the Host header is `mcp-a:8801` | Settings now build explicit `TransportSecuritySettings`. Protection stays **on**; `MCP_ALLOWED_HOSTS` extends the allowlist. Pinned by three tests |
| 14 | `aks-up.ps1`'s `Invoke-Az` helper used `ValueFromRemainingArguments` | **The deploy script died on its first command**, before creating anything: `ValueFromRemainingArguments` does not stop PowerShell binding things that look like parameters, so `-o none` failed with *"the parameter name 'o' is ambiguous"* against `-OutVariable` / `-OutBuffer`. A pure syntax check cannot catch this — the script parses fine | The helper now takes a single `[string[]]` array and every call site passes `@('acr','build',...)` |
| 15 | `az acr build` streamed its build log to a Windows console | **The deploy aborted with `UnicodeEncodeError: 'charmap' codec can't encode`** — *after* the image had been built and pushed successfully. `az` is a Python app; colorama writes the streamed log in cp1252 and dies on the first character it cannot map. `PYTHONIOENCODING=utf-8` does **not** fix it, because colorama wraps the console handle itself | `--no-logs` on the build. It still waits for the run and still fails loudly; the script prints the `az acr task logs` command to use when it does |
| 16 | The web access-key gate treated an empty key as "no gate" | **A missing or mis-keyed Secret removed authentication entirely** on the public deployment, with the pod still reporting healthy, nothing in the logs, and no visible difference — every route served anonymously to the internet. `deployment.yaml` also marked the `secretKeyRef` `optional: true`, so the pod scheduled happily without it | `WEB_REQUIRE_ACCESS_KEY=1` is set on the public deployment and makes an empty key return **503**, not 200. Laptop and Compose runs are unaffected. `/health` still answers so probes survive an operator error. Proven on a live public endpoint by deleting the Secret |
| 17 | `BIND_HOST: "0.0.0.0"` lived in the ConfigMap, which all five containers read | The five containers share one network namespace, so only `web` needs a public bind — but **`devidp` was listening on the pod IP**, reachable from any other pod in the cluster, with no NetworkPolicy in the way. That is an unauthenticated token-minting oracle that will issue a token for an arbitrary audience. It also made the comment in `service.yaml` untrue | `BIND_HOST` moved out of the ConfigMap onto each container: `127.0.0.1` for the four internal ones, `0.0.0.0` for `web`. Probes for the four had to become `exec` curl against localhost, because a kubelet `httpGet` targets the pod IP. Verified on a live pod: `podIP:8800` refuses, `localhost:8800` answers |
| 18 | `/authorize` interpolated query parameters into HTML and never validated `redirect_uri` | Reflected XSS via `client_id`/`scope`/`resource`, and an **open redirect that hands a live authorization code to any host** — the exact failure this talk argues against, sitting inside the demo. Not internet-reachable in the shipped topology, which is the only reason it was not worse | `html.escape()` on the three interpolated values, and `redirect_uri` restricted to loopback callbacks per RFC 8252. Pinned by 10 tests |
| 19 | The access key was compared with `==` | Not constant-time. Not practically exploitable — a 32-character CSPRNG secret behind a load balancer — but a real defect in code that argues about careful authorization | `hmac.compare_digest` |
| 20 | `foundry.assess()` always sent `temperature=0.0` | **The model was never called.** Reasoning-class deployments accept only the default temperature and reject an explicit `0.0` with a 400. Every `assess_refund` call fell into the offline fallback — and because that fallback is deliberately graceful and clearly labelled, the demo kept passing 14/14 and nothing surfaced the fact that no model had ever been reached. The generic `BadRequestError` in the audit record sent the investigation toward auth and networking; the offending parameter was in the message the whole time | Determinism is still requested first, and a 400 that names `temperature` triggers one retry without it. The audit record now carries the provider's message, while the on-screen summary keeps a short label. Pinned by `tests/test_foundry.py` |
| 21 | `stop-all.ps1` only stops the services it has PIDs for | Orphaned uvicorn processes from an earlier session keep ports 8800–8803 bound. `start-all` then reports **`all services healthy`** — because it health-checked the *ghosts*, not the processes it just launched. Code edits appear to have no effect, which is a genuinely disorienting thing to hit while rehearsing | Documented in the runbook with the recovery: check `Get-NetTCPConnection -LocalPort 8800..8803 -State Listen`, stop those PIDs explicitly, then start again |

---

## 4. What is verified, and what is not

### Verified on this machine

- All 207 automated tests pass (`pytest tests/ -q`).
- All 14 stage scenarios pass (`python -m refund_demo.scenarios run-all`).
- Full protocol trace: 401 challenge → PRM → AS metadata → PKCE S256 → RFC 8707 resource indicator → audience-bound token → `tools/call`.
- On-behalf-of exchange, delegated identity preservation, and upstream re-enforcement.
- All three adversarial checks, each with an unchanged ledger digest.
- The web API end to end against live services: health, scenario listing, a real run, ledger digest, audit tail, and `403` on reset.
- **The container image builds**, and **all 14 scenarios pass inside Docker Compose** with all five containers healthy.
- **The demo runs on a real AKS cluster.** Image built by ACR Tasks, pod rolled out 5/5 ready with zero restarts, **all 14 scenarios passed against the public IP**, and the access-key gate returned `401` without a key and `200` with one while `/health` stayed open for probes.
- **The clean-ledger digest is identical on the laptop, in Compose, and on AKS** (`211597d92491…`); a full scenario run lands on `a24b01f92f67` on both the laptop and the cluster.
- **`readOnlyRootFilesystem: true` holds in practice** — no container restarted.
- Image layout: source at `/app/src`, `.local` resolving to `/app/.local`, `.venv` and `tests` excluded, and the non-root user able to write the state directory.
- Compose file syntax (`docker compose config`), Dockerfile lint (`docker build --check`, no warnings), and cross-file agreement between Compose, Kubernetes and the Dockerfile (63 tests).
- Both teardown scripts on a non-existent resource group, and identical registry-name derivation between PowerShell and bash.

### NOT verified — state this plainly if asked

| Item | Why | Risk |
| --- | --- | --- |
| **Microsoft Entra ID mode** (`AUTH_MODE=entra`) | No tenant access was authorized | The MSAL on-behalf-of path and real Entra discovery are **untested**. `AUTH_MODE=devidp` is the presentation default. |
| **Azure deployment** (`demo/infra`) | The AKS path uses `k8s/` and the deploy script instead; the Bicep was never applied | Bicep compiles (`az bicep build`) but has never been deployed. Note this is a *different* artifact from the verified AKS path — that one is proven, this one is not. |
| **`aks-up.sh`** (bash deploy) | The verified deployment ran `aks-up.ps1` | Syntax-checked and command-for-command equivalent to the PowerShell version, but never driven a real deployment. |
| **Copilot / VS Code MCP OAuth redirect URIs** | Could not be confirmed against a live client | `demo/identity/README.md` explains how to read the correct value out of the client's own `AADSTS50011` error rather than guessing it. |
| **Least-privilege Foundry RBAC role** | Not confirmed against live role definitions | `demo/infra/modules/foundry.bicep` documents the assumption. |
| **Live Foundry inference** | Verified against a real deployment, on the laptop **and in AKS** | `assess_refund` was run live against an Azure AI Services deployment (`gpt-5.6-sol`): a benign order returned model text with real token counts, and the injected order was rejected by the platform content filter. In the cluster the same call reported `live: true` in ~6.5 s using an API key from a Kubernetes Secret. With no endpoint configured the tool returns a labelled offline assessment, so the demo still runs with the network off. |
| **Platform content filter as a defence layer** | Verified live, on the laptop and in AKS | Azure's content filter refused the injected order notes before the model generated anything. Reported as `filtered: true` and `handled_by: platform content filter`, not as an outage. The refund is still denied by the policy engine either way. |
| **Foundry credentials confined to one container** | Verified by reading the live pod | All Foundry settings live in the `refund-demo-foundry` Secret, mounted only by `mcp-a`. Checked with `printenv` in each of the five running containers: only `mcp-a` has `FOUNDRY_API_KEY`, and the other four see the empty ConfigMap defaults. |
| **Workload identity for Foundry** | **Not verified** | The cluster authenticates with an API key. The build account holds *Foundry User* on the model resource — enough for inference, not enough for `roleAssignments/write` — so a managed identity could not be granted access. `DefaultAzureCredential` is what the laptop uses and the code path is shared, but `aks-up` does not create the federated credential. |

---

## 5. Re-verification checklist (run 2026-10-03)

1. `demo\.venv\Scripts\python.exe -m pip list --outdated` — note any change to `mcp`.
2. If `mcp` has a new minor version, re-check the seven API facts in §2 before upgrading. Do not upgrade inside the last 72 hours unless something is broken.
3. `scripts\check.ps1` — must print `READY`.
4. Confirm `mcp.types.LATEST_PROTOCOL_VERSION` still reads `2026-07-28`; if not, record the new value here and re-read the authorization section of the spec.
5. Re-confirm the pinned client version in `docs/SETUP.md` §6 against the installed client.
