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

---

## 4. What is verified, and what is not

### Verified on this machine

- All 141 automated tests pass (`pytest tests/ -q`).
- All 14 stage scenarios pass (`python -m refund_demo.scenarios run-all`).
- Full protocol trace: 401 challenge → PRM → AS metadata → PKCE S256 → RFC 8707 resource indicator → audience-bound token → `tools/call`.
- On-behalf-of exchange, delegated identity preservation, and upstream re-enforcement.
- All three adversarial checks, each with an unchanged ledger digest.
- The web API end to end against live services: health, scenario listing, a real run, ledger digest, audit tail, and `403` on reset.
- **The container image builds**, and **all 14 scenarios pass inside Docker Compose** with all five containers healthy.
- **The clean-ledger digest is identical in Compose and on the laptop** (`211597d92491…`), so seeded data and fingerprinting agree across environments.
- Image layout: source at `/app/src`, `.local` resolving to `/app/.local`, `.venv` and `tests` excluded, and the non-root user able to write the state directory.
- Compose file syntax (`docker compose config`), Dockerfile lint (`docker build --check`, no warnings), and cross-file agreement between Compose, Kubernetes and the Dockerfile (46 tests).
- Both teardown scripts on a non-existent resource group, and identical registry-name derivation between PowerShell and bash.

### NOT verified — state this plainly if asked

| Item | Why | Risk |
| --- | --- | --- |
| **Microsoft Entra ID mode** (`AUTH_MODE=entra`) | No tenant access was authorized | The MSAL on-behalf-of path and real Entra discovery are **untested**. `AUTH_MODE=devidp` is the presentation default. |
| **Azure deployment** (`demo/infra`) | Provisioning was not approved; nothing was deployed | Bicep compiles (`az bicep build`) but has never been applied. Treat first deploy as a two-hour task, not a five-minute one. |
| **AKS deployment** | No subscription was authorized | Manifests are schema-shaped and pinned by 46 tests; no rollout was observed. The image and the application are now proven under Compose, which removes much of the risk but not the cluster-specific part. Rehearse it days ahead, never on the day (R17). |
| **`readOnlyRootFilesystem: true`** | Compose does not set it, and no pod has run | If a container crashloops on AKS, relax this first. `/tmp` is an `emptyDir` and `PYTHONDONTWRITEBYTECODE=1` is set, so it *should* hold. |
| **Copilot / VS Code MCP OAuth redirect URIs** | Could not be confirmed against a live client | `demo/identity/README.md` marks these as TODO. Confirm from the client's own error message during rehearsal. |
| **Least-privilege Foundry RBAC role** | Not confirmed against live role definitions | `demo/infra/modules/foundry.bicep` documents the assumption. |
| **Live Foundry inference** | No endpoint configured | `assess_refund` falls back to an offline assessment that is explicitly labelled `live: false` and prefixed `[OFFLINE ASSESSMENT - NO MODEL WAS CALLED]`. It can never be mistaken for live output. |

---

## 5. Re-verification checklist (run 2026-10-03)

1. `demo\.venv\Scripts\python.exe -m pip list --outdated` — note any change to `mcp`.
2. If `mcp` has a new minor version, re-check the seven API facts in §2 before upgrading. Do not upgrade inside the last 72 hours unless something is broken.
3. `scripts\check.ps1` — must print `READY`.
4. Confirm `mcp.types.LATEST_PROTOCOL_VERSION` still reads `2026-07-28`; if not, record the new value here and re-read the authorization section of the spec.
5. Re-confirm the pinned client version in `docs/SETUP.md` §6 against the installed client.
