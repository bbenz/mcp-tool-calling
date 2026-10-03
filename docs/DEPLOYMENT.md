# Deployment

Four ways to run this demo. They exist for different rooms, not as alternatives of equal standing.

| Mode | Use it when | Needs | Status |
| --- | --- | --- | --- |
| **1. Operator scripts** | **On stage. This is the rehearsed path.** | Python 3.12 | Verified |
| **2. Scripts + web UI** | A browser view helps the back row read the verdicts | Python 3.12 | Verified |
| **3. Docker Compose** | Handing the demo to someone who has Docker and nothing else | Docker Desktop | Verified: built and all 14 scenarios pass in containers |
| **4. Azure Kubernetes Service** | Remote audience, shared link, or the "what would this look like hosted" question | Azure subscription, `az`, `kubectl` | Verified: deployed, and all 14 scenarios pass against the public IP |

**Nothing in the 25-minute talk requires modes 3 or 4.** They are additions. Mode 1 is unchanged by their existence — same scripts, same commands, same output.

Every command below is run from the `demo/` directory.

---

## 1. Operator scripts — the rehearsed path

This is [SETUP.md](SETUP.md) §4 and §5, restated here only so the four modes sit side by side.

| Task | PowerShell | Bash |
| --- | --- | --- |
| Bootstrap | `.\scripts\bootstrap.ps1` | `./scripts/bootstrap.sh` |
| Start the four services | `.\scripts\start-all.ps1 -Reset` | `./scripts/start-all.sh --reset` |
| Full verification | `.\scripts\check.ps1` | `./scripts/check.sh` |
| One scenario | `.\scripts\scenario.ps1 wrong-audience` | `./scripts/scenario.sh wrong-audience` |
| Stop | `.\scripts\stop-all.ps1` | `./scripts/stop-all.sh` |

A `.ps1` cannot be run by bash and a `.sh` cannot be run by PowerShell. Use the twin for the shell you are in.

---

## 2. Scripts plus the web UI

The web front end is a **reporting surface, not a decision point**. It runs scenarios and renders what came back. Every allow and every deny in it was decided by the MCP server; the page cannot authorize anything, and it holds no policy of its own. That distinction is the whole talk, so it is enforced in code and pinned by tests rather than described in a comment.

Start the four services first, then add the view:

| Task | PowerShell | Bash |
| --- | --- | --- |
| Serve the UI | `.\scripts\web.ps1` | `./scripts/web.sh` |
| On another port | `.\scripts\web.ps1 -Port 9000` | `./scripts/web.sh --port 9000` |

Then open <http://localhost:8080>.

The page shows the 14 scenarios with the claim each one makes, a PASS/FAIL badge, the full protocol trace for the selected run, the live ledger digest, the audit tail, and a badge in the header naming the platform it is running on. It is a single self-contained HTML document: no CDN, no build step, no external requests. A test asserts that, because a demo about trust boundaries should not fetch a script from someone else's CDN in front of an audience.

### The expanders

Every scenario row expands to a short briefing: **what it sends**, **what to expect back**, and **why that matters** — plus the formal claim under test. There is an **About this demo** expander above the list covering what the app is, how it works, what to watch, and what it is not.

They exist because the page is read without narration at least as often as with it — over a shoulder, on a phone, or from a link after the talk. All of them start collapsed, because a wall of prose behind a presenter is worse than none; **Expand all** opens the lot for someone reading alone.

The prose lives in `demo/src/refund_demo/briefings.py`, deliberately apart from `CLAIMS` in `scenarios.py`. `CLAIMS` is load-bearing — the scripts print it and the tests assert against it — and nobody should be tempted to soften a claim to make it read better on a slide. Tests pin that the two sets stay in step, that no field is left thin, and that scenario *results* are still HTML-escaped even though the briefings are intentionally not.

### What the UI deliberately will not do

- **Reset is off.** `POST /api/reset` returns `403` unless `WEB_ALLOW_RESET=1`, and it is still refused outright in `AUTH_MODE=entra`. Reset mutates the ledger; it stays an operator action.
- **Runs are serialized.** One scenario at a time, so two clicks cannot interleave against one ledger and produce a digest nobody can explain.
- **No secrets are rendered.** Tokens, codes and PKCE verifiers never reach the page.

### Optional access key

Set `WEB_ACCESS_KEY` and every route except `/health` requires it, as an `X-Demo-Key` header or a `?k=` query parameter. `/health` stays open so container and Kubernetes probes keep working.

```powershell
$env:WEB_ACCESS_KEY = 'something-long'
.\scripts\web.ps1
# then open http://localhost:8080/?k=something-long
```

This is a shared secret over HTTP. It keeps a casual passer-by off the page; it is not authentication, and it is not what the talk is arguing for.

---

## 3. Docker Compose

Five containers from one image: `devidp`, `upstream`, `mcp-a`, `mcp-b`, `web`. One image for all five, so a token minted by the issuer and validated by a resource server cannot drift apart between builds.

| Task | PowerShell | Bash |
| --- | --- | --- |
| Build and start | `.\scripts\compose-up.ps1` | `./scripts/compose-up.sh` |
| Start without rebuilding | `.\scripts\compose-up.ps1 -NoBuild` | `./scripts/compose-up.sh --no-build` |
| Stop, keep the ledger | `.\scripts\compose-down.ps1` | `./scripts/compose-down.sh` |
| Stop and wipe state | `.\scripts\compose-down.ps1 -Volumes` | `./scripts/compose-down.sh --volumes` |

Both wrappers wait until all five containers report **healthy** before printing the URL, so a green prompt means the services actually answered, not that Docker created something.

Published on the host:

```
http://localhost:8080                                           web UI
http://localhost:8800/.well-known/openid-configuration          issuer metadata
http://localhost:8801/.well-known/oauth-protected-resource      Resource A metadata
http://localhost:8802/.well-known/oauth-protected-resource      Resource B metadata
```

### One thing that is different under Compose

Inside the network the containers address each other by **service name** (`http://mcp-a:8801`), and those are the identifiers the metadata advertises. An MCP client running on your host will be pointed at `http://mcp-a:8801` by the protected-resource metadata and will not resolve it.

That is not a bug to work around — it is what happens when issuer, resource identifier and network address stop agreeing, which is the same class of mistake the `wrong-audience` scenario is about. **For the live-client segment, use mode 1.**

### State

All five containers share one named volume mounted at `/app/.local`: one ledger, one audit log, one signing key. `compose-down` keeps it so a restart resumes where you were; `-Volumes` / `--volumes` drops it, which is the container equivalent of resetting with a fresh key.

Because the volume survives a restart, **the refund in `allowed-refund` survives it too**. The scenario uses a fixed idempotency key, so a second run is a *retry* of the same business request rather than a new one: it still passes, reports `refund_applied_by_this_run: False`, and leaves the ledger digest exactly where it was. Nothing is exhausted and nothing needs wiping to keep the suite green.

Wipe state when you want the first-call demonstration back — a ledger that moves `0 → 4000` on stage rather than a replay:

```powershell
.\scripts\compose-down.ps1 -Volumes ; .\scripts\compose-up.ps1
```

A clean ledger fingerprints as `211597d92491…` in Compose, which is byte-identical to a clean ledger on the laptop.

The ledger is SQLite. **Nothing here scales past one writer**, which is why the Kubernetes deployment below is a single pod rather than something that looks more impressive and works less well.

---

## 4. Azure Kubernetes Service

> **Deployed and verified.** A real cluster was created in `eastus`, the image was built by ACR Tasks, the pod rolled out first time with all five containers ready, and **all 14 scenarios passed against the public IP** — with a post-run ledger digest of `a24b01f92f67`, identical to the laptop. Budget real time for a *first* run anyway: cluster creation alone takes several minutes, and you should never do it for the first time on the day of a talk.
>
> Observed timings on that run: resource group and registry seconds, ACR build ~2 minutes, `az aks create` ~4 minutes, rollout under a minute, load-balancer IP ~30 seconds.

### Prerequisites

- An Azure subscription you are willing to spend money on
- `az` (2.88+) — `az login`
- `kubectl` (1.30+)
- **No local Docker required.** The image is built by ACR Tasks, server-side.

### Deploy

| Task | PowerShell | Bash |
| --- | --- | --- |
| Deploy | `.\scripts\aks-up.ps1` | `./scripts/aks-up.sh` |
| Pick a region | `.\scripts\aks-up.ps1 -Location westeurope` | `./scripts/aks-up.sh --location westeurope` |
| Pick a node size | `.\scripts\aks-up.ps1 -NodeSize Standard_D2as_v5` | `./scripts/aks-up.sh --node-size Standard_D2as_v5` |
| Skip the prompt | `.\scripts\aks-up.ps1 -Yes` | `./scripts/aks-up.sh --yes` |
| **Tear down** | `.\scripts\aks-down.ps1` | `./scripts/aks-down.sh` |

The script prints the subscription, region, registry, cluster and image tag, warns that this creates billable resources, and waits for confirmation. Then, in order: resource group → container registry → `az acr build` → AKS cluster → `az aks get-credentials` → apply `k8s/` → wait for rollout → print the public URL.

Repeat runs are idempotent: existing resource group, registry and cluster are reused, and only a fresh image tag and a rolling replacement are applied.

### If `az acr build` dies with a Unicode error

On a Windows console, `az acr build`'s log streamer can crash with `UnicodeEncodeError: 'charmap' codec can't encode …`. **The image has almost certainly been built and pushed already** — only the client-side log printer died. The script passes `--no-logs` to avoid this, but if you run the command by hand:

```powershell
az acr task list-runs --registry <registry> --top 1 -o table   # look for Succeeded
az acr task logs --registry <registry> --run-id <id>
```

`PYTHONIOENCODING=utf-8` does **not** fix it; colorama wraps the console handle regardless.

### If the cluster will not create: "VM size … is not allowed in your subscription"

Step 4 can fail with `(BadRequest) The VM size of Standard_D2s_v3 is not allowed in your subscription in location '<region>'`, followed by a very long list of sizes that *are* allowed. This is an Azure Policy or SKU restriction on the subscription, not a quota problem and not a fault in the script — the resource group, registry and image from steps 1–3 were all created successfully, so you only need to re-run with a permitted size.

Pick a 2-vCPU size from the list the error printed and pass it:

```powershell
.\scripts\aks-up.ps1 -ResourceGroup <resource-group> -NodeSize Standard_D2as_v5
```

`Standard_D2as_v5` and `Standard_D2s_v4` are the usual stand-ins for the `Standard_D2s_v3` default. The demo is a single pod of five small containers, so anything with 2 vCPU and 8 GB is ample. To see what a subscription permits before deploying:

```powershell
az vm list-skus --location <region> --size Standard_D2 --query "[?!restrictions[0]].name" -o tsv
```

### What it costs

Roughly **$0.10–0.12 per hour** while it is up: one `Standard_D2s_v3` node (~$70/month), a Basic registry (~$5/month), and a load-balancer public IP. The AKS control plane is free tier. Leaving it running for a week costs more than the talk is worth — see R18 and tear it down.

### Resetting the ledger between rehearsals

`WEB_ALLOW_RESET` is `0` in the cloud, deliberately. The state directory is an `emptyDir`, so restarting the pod is the reset:

```powershell
kubectl -n refund-demo rollout restart deploy/refund-demo
kubectl -n refund-demo rollout status deploy/refund-demo
```

Give it a few seconds after `rollout status` returns before probing — the pod reports ready slightly before it is answering.

### The shape of the deployment, and why

**One pod, five containers, one `emptyDir`.**

That looks wrong until you remember the ledger is SQLite. One writer is a hard constraint, so the only real question is where the other four containers go. Putting them in the same pod means they share a network namespace and reach each other on `localhost` — the identical configuration that runs on a laptop — and there is no `ReadWriteMany` storage class and no SQLite-over-SMB locking to go wrong.

It is a demo, not a reference architecture for hosting MCP servers. The talk says that out loud; the manifest should not quietly contradict it.

```mermaid
flowchart LR
    I([Internet]) -->|":80 → :8080"| SVC["Service<br/>LoadBalancer"]
    SVC --> W
    subgraph POD["Pod — one replica, shared localhost"]
        W["web<br/>:8080"]
        A["mcp-a<br/>:8801"]
        B["mcp-b<br/>:8802"]
        U["upstream<br/>:8803"]
        D["devidp<br/>:8800"]
        V[("emptyDir<br/>/app/.local")]
    end
    W --> A
    W --> B
    A --> U
    A --> D
    U --> V

    classDef ext fill:#3f1d1d,stroke:#f87171,color:#fee2e2
    classDef in fill:#1f2937,stroke:#60a5fa,color:#e5e7eb
    class I,SVC ext
    class W,A,B,U,D,V in
```

**Only `web` is exposed.** `devidp` mints tokens for anyone who asks. Putting a development issuer on a public address would undercut the entire point of the talk, so the Service selects port 8080 and nothing else.

### Why the evidence still says `localhost`, and how the audience can tell

On AKS, a `no-token` result reports its challenge exactly as it does on a laptop:

```
WWW-Authenticate: Bearer error="invalid_token", …
                  resource_metadata="http://localhost:8801/.well-known/oauth-protected-resource"
```

That is correct, and it is deliberately not rewritten. `MCP_A_PUBLIC_URL` is three things at once: the address the client dials, the identifier Resource A publishes in its metadata, and an audience it will accept in a token. The four internal containers bind `127.0.0.1` and no Service selects them, so `http://localhost:8801` really is Resource A's only address — there is no external one to advertise. Substituting the load balancer's hostname for display would publish a discovery document pointing at a port nothing answers, and break audience validation for every scenario that passes. A talk about resource binding should not fake a resource identifier.

The real problem was never the URL. It was that a projector showed nothing to distinguish a cluster from a laptop. So the UI states where it is running instead:

- A **badge in the header** — `Kubernetes`, with the pod name beside it in dimmer type, outlined in green; grey `Docker Compose` under Compose, and `Local` when neither. Hovering adds the node name.
- A **line under "Last result"** that explains the loopback addresses in terms of the platform that is actually hosting them.

`web` learns its pod and node from the downward API (`POD_NAME`, `NODE_NAME` in `k8s/deployment.yaml`); Kubernetes itself is detected from `KUBERNETES_SERVICE_HOST`, not the service-account token, because this pod sets `automountServiceAccountToken: false`. Nothing in the badge reaches the API server, and it reads no Secret.

On stage, point at the badge once and move on. It is the difference between claiming this is running on AKS and showing it.

### Security posture

| Control | Setting |
| --- | --- |
| Access key | Generated per deployment and stored in a Secret; printed once in the final URL |
| Reset endpoint | Off (`WEB_ALLOW_RESET=0` in the ConfigMap) |
| User | Non-root uid 10001, `runAsNonRoot: true`, `fsGroup: 10001` |
| Filesystem | `readOnlyRootFilesystem: true`; writes confined to the mounted state and `/tmp` |
| Capabilities | All dropped; `allowPrivilegeEscalation: false`; `seccompProfile: RuntimeDefault` |
| API access | `automountServiceAccountToken: false` |
| Limits | CPU and memory requests and limits on every container |
| Exposure | `devidp`, `mcp-a`, `mcp-b`, `upstream` stay inside the pod |

Pass `--no-access-key` / `-NoAccessKey` to leave the UI ungated. Only do that for a cluster nobody else can reach.

### Optional: a live model, and a control you do not own

```powershell
.\scripts\aks-up.ps1 -ResourceGroup <resource-group> `
    -FoundryEndpoint https://<resource>.cognitiveservices.azure.com/ `
    -FoundryDeployment <deployment-name>
```

```bash
./scripts/aks-up.sh --resource-group <resource-group> \
    --foundry-endpoint https://<resource>.cognitiveservices.azure.com/ \
    --foundry-deployment <deployment-name>
```

Both settings go into the `refund-demo-foundry` **Secret**, not the ConfigMap — including the endpoint and deployment name, which are not secrets in the cryptographic sense but do name a resource in someone's subscription. The ConfigMap is read by all five containers; this Secret is mounted by `mcp-a` alone, because `assess_refund` is the only caller. One object, one lifecycle, one blast radius. Leave the flags off and the tool returns a labelled offline assessment, so the demo still runs with no model and no network.

`-FoundryApiVersion` / `--foundry-api-version` is optional and goes into the same Secret. Omit it and the cluster uses the `FOUNDRY_API_VERSION` baked into the ConfigMap. Pass it when a deployment needs a newer API version than that default, so the cluster matches the `FOUNDRY_API_VERSION` in your local `demo/.env` instead of silently diverging from it.

Credentials, in order of preference:

1. **Workload identity** (nothing to pass). The pod's managed identity needs the *Cognitive Services OpenAI User* role on the Foundry resource, and the cluster needs OIDC issuer + workload identity enabled. `aks-up` does not wire this, and it has never been run this way — see §7.
2. **`-FoundryApiKey` / `--foundry-api-key`**, which puts the key in the same Secret. A static credential, so prefer option 1 for anything longer-lived than a conference. This is what the verified deployment uses.

Getting the key, if the resource already exists:

```powershell
$key = az cognitiveservices account keys list --name <resource> --resource-group <rg> --query key1 -o tsv
```

What it buys on stage: running `prompt-injection` shows `assessment_was_blocked_by_content_filter: True` and `handled_by: platform content filter`. That is a control living in the **platform**, not in this app and not in MCP — and the forced refund is denied identically whether it fires or not.

Verified in the running pod: `mcp-a` reports `live: true` with real token counts on a benign order, and it is the only container whose environment contains `FOUNDRY_API_KEY`.

All fixtures are synthetic. There is no real customer, order, or credential anywhere in this deployment, and there must never be.

### Tear it down

```powershell
.\scripts\aks-down.ps1
```

Deletes the whole resource group — cluster, registry, load balancer, public IP, managed identity — and removes the stale kubeconfig entry. It lists what it is about to delete and requires you to type the resource group name.

**A demo cluster left running over a conference weekend is a real bill.** Tear it down the same day.

---

## 5. When the image build cannot reach PyPI

`docker compose build` can fail like this:

```
SSLError(SSLError(1, '[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] ...'))
  host='files.pythonhosted.org'
```

This is the network, not the Dockerfile. Some corporate networks allow `pypi.org` (the index) but block `files.pythonhosted.org` (the CDN that serves the actual wheels), so dependency resolution begins and then dies on the first download.

It was reproduced on the machine this demo was built on — from the host **and** inside the build, identically — and then it cleared on its own a day later, at which point the image built first time. Treat it as a property of the room you are in, not of the repository. Check it before you rely on mode 3 at an event, because it can come back.

Three ways through it:

1. **Deploy to AKS instead.** `az acr build` builds server-side, where PyPI is reachable. The cloud path is unaffected by this block — that is not a coincidence, it is why the image is built by ACR Tasks rather than pushed from a laptop.
2. **Point the build at an internal mirror.** The Dockerfile takes build arguments for exactly this:

   ```bash
   docker compose -f docker/docker-compose.yml build \
     --build-arg PIP_INDEX_URL=https://pkgs.example.com/pypi/simple \
     --build-arg PIP_TRUSTED_HOST=pkgs.example.com
   ```

3. **Use mode 1 or 2.** The operator scripts need no image at all, and they are the rehearsed path regardless.

Confirming it is the network rather than your setup takes one command:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://pypi.org/simple/              # 200
curl -sS -o /dev/null -w '%{http_code}\n' https://files.pythonhosted.org/simple/ # 404 = reachable
```

A `404` from the second URL is the **good** answer: that path does not exist, so the CDN is answering you. A TLS error is the bad one.

---

## 6. Configuration reference

Every setting is an environment variable; containers set them through the Compose `environment` block or the Kubernetes ConfigMap.

| Variable | Default | Purpose |
| --- | --- | --- |
| `AUTH_MODE` | `devidp` | `devidp` or `entra` |
| `BIND_HOST` | *(unset)* | Overrides the listen address. **Containers must set `0.0.0.0`** — `devidp` binds loopback by default, which is right on a laptop and wrong in a container |
| `DEVIDP_ISSUER` | `http://localhost:8800` | Issuer identifier, and the base for JWKS and metadata |
| `MCP_A_PUBLIC_URL` | `http://localhost:8801` | Resource A identifier as advertised in metadata |
| `MCP_B_PUBLIC_URL` | `http://localhost:8802` | Resource B identifier |
| `UPSTREAM_API_URL` | `http://localhost:8803` | Upstream refund API |
| `WEB_PORT` | `8080` | Web UI port |
| `WEB_ALLOW_RESET` | `0` | Enables `POST /api/reset`. Still refused in `entra` mode |
| `WEB_ACCESS_KEY` | *(unset)* | Shared secret for every route except `/health` |
| `MCP_ALLOWED_HOSTS` | *(unset)* | Extra `Host` header values the MCP transport accepts, comma separated (`mcp-a:*,mcp-b:*`). Loopback is always allowed |
| `POD_NAME` | *(unset)* | Display only. Set from the downward API on AKS so the header badge can name the pod |
| `NODE_NAME` | *(unset)* | Display only. Set from the downward API on AKS; shown in the badge tooltip |

Issuer and resource URLs must stay consistent with each other. If a token says `aud=http://mcp-a:8801` and Resource A believes it is `http://localhost:8801`, every call fails audience validation — correctly, and confusingly.

### Two things that only break in containers

Both were found by running the stack, not by reading it, and both now have tests.

**`421 Misdirected Request` from an MCP server.** The MCP SDK turns on DNS rebinding protection whenever the server is built for a loopback host, and then accepts only `localhost` / `127.0.0.1` / `[::1]` in the `Host` header. On a laptop you never notice. Under Compose the Host header is the service name — `mcp-a:8801` — and every tool call is rejected *after* a completely successful OAuth handshake, which makes it look like a token problem when it is not. `MCP_ALLOWED_HOSTS` extends the allowlist; the protection stays on, because switching it off in a talk about authorization would be a poor look. A single pod on AKS does not need it: there, the containers really are talking over loopback.

**The test suite fails while Compose is up.** The integration tests bind their own services on 8800–8803, so if the containers already hold those ports you get a wall of `httpx.ConnectError`. Run `scripts/compose-down.ps1` first. Nothing is wrong.

---

## 7. What is verified, and what is not

Said plainly, because a talk about authorization should not overclaim.

**Verified by execution:**

- Modes 1 and 2, in PowerShell and bash: 221 tests, 14 scenarios, `READY` from `check`.
- The web API end to end against live services: health, scenario listing, a real run, ledger digest, audit tail, and `403` on reset.
- **Mode 3 end to end.** The image builds, all five containers report healthy, and **all 14 scenarios pass inside Compose** with the ledger moving only on the scenario that is supposed to move it.
- **Mode 4 end to end, twice.** A real AKS cluster was created, the image was built by ACR Tasks, the pod rolled out with 5/5 containers ready and zero restarts, and **all 14 scenarios passed against the public IP**. The second run proved the security hardening below.
- The clean-ledger digest is **identical in all three environments** — laptop, Compose and AKS (`211597d92491…`) — and a full scenario run lands on `a24b01f92f67` on both the laptop and the cluster.
- The access-key gate on a public address: `401` without a key, `200` with one, and `/health` deliberately exempt so the Kubernetes probes keep working.
- **A live Foundry model behind `assess_refund`, from inside the cluster.** The verified cloud deployment calls a real `gpt-5.6-sol` deployment using an API key held in a Kubernetes Secret: a benign order returned model text with real token counts (~6.5 s), and the injected order was refused by the platform content filter and reported as `filtered: true` rather than as an outage. All 14 scenarios pass with it configured.
- **Secret containment, checked by reading the environment of every container in the running pod.** Only `mcp-a` has `FOUNDRY_API_KEY`; the other four see the empty ConfigMap defaults and nothing else.
- **The hardening in §8, proven against the live public endpoint:** deleting the Secret returns `503` on every route instead of serving anonymously, `/health` still answers, and `devidp` refuses connections on the pod IP (`curl: (7)`) while still answering on loopback.
- `readOnlyRootFilesystem: true` **does** hold in practice — the pod ran with no restarts, including with `exec` probes.
- Image layout: source lands at `/app/src`, `.local` resolves to `/app/.local`, `.venv` and `tests` are excluded, and the non-root user can write the state directory.
- Compose file syntax via `docker compose config`; Dockerfile lint via `docker build --check` (no warnings).
- Manifest structure and cross-file agreement, via 64 tests that fail if Compose, Kubernetes and the Dockerfile stop describing the same demo.
- Teardown behaviour on a non-existent resource group, in both shells, and identical registry-name derivation between them.

**Not verified:**

- **`AUTH_MODE=entra` has never been executed**, in any mode.
- **`demo/infra` Bicep has never been deployed.** It compiles; that is the whole claim. Note that this is a *separate* artifact from `k8s/` — the AKS path above does not use it.
- **The bash deploy script has never driven a real deployment.** `aks-up.sh` is syntax-checked and mirrors the PowerShell logic command for command, but both verified runs were `aks-up.ps1`.
- **There is no TLS.** The cloud mode serves plain HTTP, so the access key is readable by anyone on the network path. See §8.
- **Workload identity has never been used.** The verified cloud run authenticates to Foundry with an API key in a Secret, because the account that built this holds *Foundry User* on the model resource and therefore cannot create role assignments on it. Key-free authentication is the better answer and the code already supports it — `DefaultAzureCredential` is what the laptop uses — but `aks-up` does not wire the federated credential, and nobody has run it that way.
- **Nothing has been observed over more than a few hours of uptime**, or under more than one user at a time.

---

## 8. Security posture of the cloud mode

The cloud mode puts a demo on a public IP. A security review of that exposure found five issues; four are fixed, one is inherent to the design and is stated here instead.

**Fixed, and verified against a live endpoint:**

| Was | Now |
| --- | --- |
| An empty `WEB_ACCESS_KEY` meant *no gate*, so a missing or mis-keyed Secret silently served the whole app to the internet with the pod still healthy | `WEB_REQUIRE_ACCESS_KEY=1` on the public deployment makes an empty key return **503**. Laptop and Compose runs are unchanged. `/health` still answers so probes survive the mistake |
| `BIND_HOST: "0.0.0.0"` in the ConfigMap put **all five** services on the pod IP, including the dev issuer that mints a token for any audience to anyone who asks | `BIND_HOST` is per container: `127.0.0.1` for the four internal ones, `0.0.0.0` only for `web`. Their probes are `exec` curl against localhost, because a kubelet `httpGet` targets the pod IP |
| `/authorize` interpolated `client_id`, `scope` and `resource` into HTML unescaped, and accepted any `redirect_uri` | `html.escape()` on all three, and `redirect_uri` restricted to loopback callbacks per RFC 8252 |
| The access key was compared with `==` | `hmac.compare_digest` |

**Not fixed — know this before you share a link:**

> **The endpoint is plain HTTP and the key travels in the URL.** Anyone on the network path — conference Wi-Fi, a hotel, any transit hop, any proxy log — can read it from a single request and then has the whole app: they can run scenarios, move the ledger digest you are about to show on stage, and read the audit trail. It reaches nothing real and cannot pivot into Azure (`automountServiceAccountToken: false`), but it can embarrass you.
>
> Mitigations, in increasing order of effort: treat the link as **single-session and disposable**, and redeploy for a clean ledger; add `loadBalancerSourceRanges` to `k8s/service.yaml` scoped to your egress IP; make the Service internal and use `kubectl port-forward`; or front it with an HTTPS ingress. **Do not leave it running unattended** — see R18.

**Known and accepted:** there is no rate limiting, and `/health` is anonymous. A determined visitor can grow `audit.jsonl` on the pod's `emptyDir` until the container hits its 512Mi limit and restarts. That costs you the ledger, not a compromise.


---

## See also

- [SETUP.md](SETUP.md) — prerequisites, bootstrap, configuration, troubleshooting
- [RUNBOOK.md](RUNBOOK.md) — timed presenter schedule and recovery
