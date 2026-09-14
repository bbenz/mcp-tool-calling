# Demo Generation Prompt: Who Can Call This MCP Tool?

Use this prompt with a coding agent in this repository to generate and verify the complete demo project before the event. This is a generation prompt, not the on-stage chat script. Generate the on-stage script as a separate deliverable.

## Mission And Source Of Truth

You are a senior Python engineer, MCP security specialist, and technical demo author. Build a runnable, reproducible demonstration for Brian Benz's accepted MCP Dev Summit Toronto 2026 session:

**Who Can Call This MCP Tool? OAuth, Resource Binding, and Runtime Policy**

Read `Events/MCP-Dev-Summit-Toronto-2026-Approved-Proposals.md` first. Its accepted proposal and published description are the authoritative requirements. They describe the same session, not two separate demos. Cover every distinct technical promise, including the attendee takeaways. Do not expand into a general MCP or Azure introduction.

The session is on October 6, 2026, from 15:40 to 16:05, for an intermediate audience. The entire session is **25 minutes, including introduction and Q&A**. Assume attendees understand APIs, basic OAuth, and tool calling, but explain the MCP-specific boundaries in plain language.

Produce working code, infrastructure as code, setup automation, tests, and presenter materials. Do not stop at a plan or pseudocode. Do not claim execution or deployment succeeded without evidence.

## Confirmed Constraints

- Use **Python** for the MCP server, business API, supporting harness, and tests. Use supported, pinned dependencies and the official MCP Python SDK where practical. Use established OAuth/JWT and Microsoft identity libraries, not custom cryptography.
- Configure everything locally and in Azure **before** the session. No package installation, resource provisioning, app registration, consent administration, or substantial code generation on stage.
- Operate prepared demos live using the **GitHub Copilot desktop app and/or VS Code with GitHub Copilot**. The app means the product documented at https://docs.github.com/en/copilot/concepts/agents/github-copilot-app, not GitHub.com chat, Microsoft 365 Copilot, or a synonym for the CLI.
- Make **Microsoft Foundry prominent as the model backend of an MCP tool**. The Copilot client's model and the Foundry model called by the server are separate actors; identify them explicitly.
- Highlight Azure hosting, Microsoft Entra ID, GitHub Copilot, and Azure Monitor/Application Insights through observable behavior, not a product checklist.
- Use only synthetic customers, orders, and money. The refund endpoint mutates a demo ledger and never contacts a payment provider. Treat that mutation as the consequential action in the demonstration.
- Assume Windows with VS Code; provide PowerShell setup commands and WSL/bash equivalents where needed. Verify paths, ports, redirects, and browser authentication on the actual presenter setup.
- Reserve two minutes for introduction, two minutes for Q&A, and include recovery time within the demo segments.

## First Actions And Compatibility Gate

1. Inspect repository instructions and nearby existing work. Preserve user changes and reuse suitable project conventions. Keep all generated demo artifacts in one clearly named subtree unless root-level integration is necessary.
2. Record unresolved environmental inputs in a configuration template: tenant, subscription, resource group, region, public MCP resource URI, app registrations, callback URIs, upstream API audience, Foundry project/endpoint/model deployment, and presenter client versions. Never request secrets in chat or commit them.
3. Consult current official MCP, GitHub, VS Code, Microsoft Entra, Azure, and Foundry documentation. Record the exact MCP revision, SDK versions, client builds, API versions, source links, verification date, and preview dependencies. Do not assume that current SDKs implement every requirement in the latest specification.
4. Verify the selected client's remote HTTP transport, Protected Resource Metadata discovery, authorization-server discovery, client registration, PKCE, resource parameter handling, delegated scopes, and per-call human approval. Check the GitHub Copilot app and VS Code separately; shared CLI foundations do not establish feature parity.
5. Select one rehearsed client as the primary surface and the other as an optional alternative. Prefer the desktop app if all required capabilities work; otherwise use VS Code Copilot. Provide actual supported configuration and setup instructions for each claimed working client. Do not invent settings or silently substitute a static bearer token for interactive OAuth.
6. Verify Entra interoperability early. Distinguish RFC 8707 `resource` parameters from Entra resource-qualified `scope` values and token audience representations. Document the actual mapping and observed behavior; do not claim they are interchangeable. Do not assume dynamic client registration, arbitrary redirect URIs, or client ID metadata documents are supported. Use documented pre-registration when appropriate.
7. If the complete protocol trace cannot be exercised by the primary client, use a small standards-based reference client/harness for that trace and clearly label the client change. If an authorization broker is required, explain its trust boundary, token issuance, and downstream delegation; do not add one casually or claim broker tokens can automatically be used for Entra on-behalf-of exchange.
8. Choose a currently available Foundry model based on regional availability, latency, structured-output support, cost, and the tool's task. Make the deployment name configurable. A direct supported model SDK call is sufficient; do not add an agent orchestration framework merely to call a model once.

Resolve routine choices independently. Ask only for genuinely blocking configuration or approval to provision resources, change tenant registrations, grant consent, incur costs, or delete resources. When no environment access is available, generate the artifacts and list precisely which cloud checks remain unverified. A replay does not count as a successful live integration.

## One Story: A Refund Assistant With Explicit Trust Boundaries

Use one coherent story throughout: **May this user, through this client, refund this order with these arguments?**

Implement a minimal architecture:

- A Copilot MCP client acting for a signed-in employee.
- A protected, remotely hosted Python MCP server using Streamable HTTP over HTTPS. Do not use stdio as the main authorization demonstration.
- Microsoft Entra ID for user authentication and delegated authorization, subject to the verified compatibility gate.
- A Foundry-backed read-only assessment tool that summarizes synthetic order facts and explains a suggested disposition. Show a real model invocation and correlate its telemetry to the MCP request.
- A separate upstream refund API with its own audience and delegated permissions. It owns the synthetic ledger and independently validates its token and object-level authorization.
- Azure Container Apps as the default host for the server and API, unless an existing supported repository pattern provides a simpler equivalent. Keep the upstream API internal where practical; it must validate authorization regardless of network placement.
- A second minimal protected MCP resource with a **different accepted audience** for the wrong-resource token test. A different hostname alone is not sufficient.
- OpenTelemetry/Application Insights for correlated evidence, with structured local logs available immediately when cloud ingestion is delayed.

Prefer three clear tools: `get_order`, `assess_refund`, and `refund_order`. Make the Foundry invocation occur inside `assess_refund`. The assessment tool has no refund execution capability and no access to bearer tokens, client credentials, or authorization decisions. Its output is untrusted advisory content, not permission to execute.

Keep the tool/API design small. Avoid a custom dashboard, multiple agent frameworks, real payment integrations, or extra services that do not demonstrate a session requirement.

## Required Behavior And Evidence

Create a coverage matrix with one row for every requirement below, mapped to implementation, automated or manual check, on-stage moment, expected evidence, and responsible trust boundary.

### 1. MCP Authorization And Resource Binding

- Show an unauthenticated HTTP request receiving a 401 challenge with the applicable `WWW-Authenticate` metadata reference.
- Fetch and display Protected Resource Metadata, then authorization-server metadata using supported OAuth or OIDC discovery.
- Show the authorization-code flow with PKCE S256 and a resource indicator in both authorization and token requests as required by the selected MCP specification. Show only safe field names and redacted values, never the verifier, code, or bearer token.
- Show requested versus granted delegated scopes and sanitized validated token claims: issuer, audience, user, tenant, client identity, and expiry.
- Validate signatures with trusted issuer metadata/JWKS, allowed algorithms, issuer, tenant, audience, expiry, and applicable time claims. Decoding a JWT is not validation. Reject ID tokens and app-only tokens where delegated user access is required.
- Obtain trusted user and client identity from validated claims, not tool arguments or arbitrary headers. Explain the actual claim names and token version in use.
- Demonstrate that resource binding prevents cross-resource token reuse; it does not prevent all replay of a stolen bearer token at its intended resource.

### 2. Runtime Tool Policy And Business Arguments

- Authenticate before accepting protected MCP operations and enforce authorization again at `tools/call`. Tool listing, tool hiding, schema validation, and prompts are not authorization boundaries.
- Use a small deterministic, deny-by-default policy that maps validated user identity, tenant, calling client, delegated scopes, tool name, and validated arguments to an allow/deny result with a stable reason code and policy version.
- Define named synthetic fixtures and explicit rules: employee-to-order access, allowed client applications, refund eligibility, currency, positive integer minor-unit amounts, remaining refundable balance, and a configurable per-call limit.
- Include a reader and a refund-capable employee, plus an unapproved client or equivalent trustworthy test context. Avoid redundant live sign-ins by preparing supported sessions in advance.
- Demonstrate an allowed read, a missing-scope denial, an argument/business-rule denial, and an allowed refund. Use authoritative order data rather than model-supplied customer or tenant identifiers.
- Implement idempotency and an atomic balance/state update so retries and concurrent calls cannot double-refund. Recheck critical rules in the upstream API at mutation time.
- Distinguish transport authentication failures, insufficient-scope challenges, and tool/business errors according to the pinned MCP SDK/specification. Do not report a rejected call as a successful refund.

### 3. Delegation To The Upstream API

- Preserve the human user's identity when the MCP server calls the separate refund API using a documented delegated flow, preferably Entra on-behalf-of when supported by the selected token chain.
- Acquire a new access token for the upstream API's audience. Never pass through the incoming MCP token, use a broad application token as a silent fallback, or trust a user ID carried in a header as delegation.
- Show sanitized evidence that the upstream audience differs while the validated user identity is preserved. The upstream API must enforce its own tenant, scope, and order-access rules.
- Use managed identity for appropriate application-to-Azure access, such as Foundry inference and telemetry. Clearly distinguish that workload identity from the delegated user identity used for refunds.

### 4. Annotations And Human Approval

- Declare accurate tool annotations, including read-only/destructive and idempotency hints where supported, and explain that annotations are descriptive hints, not access control.
- Demonstrate that altering an annotation cannot turn a denied operation into an allowed operation.
- Configure the chosen Copilot client for explicit approval of the consequential refund call with its exact arguments. Disable broad auto-approval for the demo; do not use unattended/autopilot operation for the refund workflow.
- Show cancellation with no mutation, then approval followed by normal server policy checks. User approval must not override a server denial.
- Explain that the client owns this human interaction. A tool argument such as `approved=true` is not proof of human approval, and MCP does not inherently give the server a signed approval receipt.
- Do not claim the server can observe a canceled request that never reaches it. Correlate client-side approval evidence with server evidence only when the client actually exposes that information; otherwise mark it as client-only evidence.

### 5. Three Distinct Adversarial Checks

Keep all adversarial fixtures restricted to this synthetic, presenter-owned environment. Generate executable checks with expected outcomes, not just narrative warnings.

| Check | Setup And Attempt | Required Evidence |
| --- | --- | --- |
| Prompt injection selecting an unintended tool | Put a clearly labeled instruction in untrusted order notes or model-visible content attempting to induce an unauthorized `refund_order` call during an assessment task. | Record what the model actually does. Whether it follows the injection or not, force the same candidate call through a deterministic harness and prove server policy denies the unauthorized action with no ledger change. Do not present model refusal as the security boundary. |
| Confused-deputy request | Use a valid token for the correct MCP resource and attempt to make the server exercise broader authority than the user/client has, such as refunding another employee's restricted order. | Identify the deputy, authority mismatch, and request. Show denial at the relevant object/client/delegation boundary and prove no broad service credential or token passthrough bypass exists. If illustrating the MCP OAuth proxy consent variant, separately show per-client consent and bind it to the requesting client; do not conflate it with this runtime case. |
| Token reuse against the wrong MCP server | Obtain a valid token for resource A and submit it unchanged to resource B, which trusts the issuer but requires a distinct audience. Keep the token in process memory or secure storage. | A succeeds as a control; B returns an authentication rejection before tool execution because of audience mismatch. Include a valid B-token control so a broken endpoint cannot masquerade as protection. |

Keep the live attack sequence short and deterministic. Model behavior is nondeterministic, even with conservative sampling settings. A harness replay must be labeled as a harness replay, not as a fresh model attack.

### 6. Audit Evidence And Attendee Control Map

- Produce a structured record tying a `tools/call` to timestamp, trace/correlation ID, MCP request ID, authenticated pseudonymous user, tenant, client, resource/audience, tool, sanitized argument summary, policy ID/version, decision/reason, upstream outcome, and final result.
- Link Foundry model invocation metadata to the same trace where applicable: deployment, latency, usage if available, and outcome. Do not log full prompts or customer content by default.
- Record only identity claims that were validated. For rejected tokens, mark identity as untrusted/unknown instead of attributing verified identity from unvalidated claims.
- Never log credentials, authorization codes, PKCE verifiers, raw access/refresh tokens, or full sensitive claims. Avoid logging tokens even in attack scripts and terminal history.
- Keep client approval evidence separate when no trusted server-visible signal exists. Do not fabricate an approval field in the server record.
- Supply a working Application Insights/Log Analytics query matching the generated telemetry schema, plus an immediate local JSON trace view for on-stage reliability.
- Provide an MCP-specific control map showing owner, inputs, enforcement point, denial behavior, evidence, and limitations for client, authorization server, MCP server, upstream API, and Foundry-backed assessment.
- Do not claim ordinary application logs are immutable or tamper-proof audit storage.

## Mandatory 25-Minute Run Of Show

Preserve this total budget. Put setup details and deeper implementation discussion in the appendix, not the live path.

| Time | Duration | Prepared Live Moment |
| --- | --- | --- |
| 00:00-02:00 | 2 min | State the refund question and show one annotated trust-boundary diagram. Explain authentication versus authorization versus approval. |
| 02:00-07:00 | 5 min | Trace challenge, resource metadata, discovery, PKCE, resource indicators, scopes, and audience-bound token. Use safe trace evidence alongside the working client; avoid a prolonged sign-in. |
| 07:00-11:00 | 4 min | Read an order and call the Foundry-backed assessment tool. Show the model trace, then contrast scope and argument-policy denials with advisory model output. |
| 11:00-15:00 | 4 min | Show annotation limitations, cancel then approve a permitted refund, and follow delegated identity to the upstream API and ledger change. |
| 15:00-20:00 | 5 min | Execute the three distinct adversarial checks, showing the policy/audience reason and unchanged ledger for each denied mutation. |
| 20:00-23:00 | 3 min | Follow one allowed and one denied request through audit evidence; recap the control map and point to reproducible artifacts. Include recovery buffer here. |
| 23:00-25:00 | 2 min | Q&A with the control map visible. |

For every segment, generate exact presenter actions, short narration, Copilot chat prompts, expected tool selection, expected safe output, code locations to open, a one-command or equivalent rehearsed action, and a fallback. Explain in advance which trace fields are recorded rather than emitted live. Keep screen switching minimal and project well at conference font sizes.

Provide two or three optional Q&A answers covering why scopes are insufficient, why a confirmation dialog is not server authorization, and why an incoming MCP token cannot be forwarded to another API.

## Implementation And Setup Deliverables

Generate the following, adapting names to repository conventions:

1. **Runnable Python project:** MCP server, Foundry assessment integration, separate refund API, minimal second resource, deterministic fixtures, policy module, structured telemetry, and secure configuration loading. Include a dependency lock and supported Python version.
2. **Infrastructure as code:** Prefer Bicep for the selected Azure host, image registry if needed, Foundry resources/model deployment or documented existing-resource references, managed identities, least-privilege role assignments, and observability. Supply parameters, build/deploy steps, outputs, cost considerations, and teardown scoped to demo-owned resources. Do not pretend ordinary ARM/Bicep resources create Entra app registrations; handle directory setup through a supported separate mechanism.
3. **Identity setup:** Repeatable scripts or precise documented manual steps for client/resource/API registrations, exposed delegated scopes, consent, authorized clients, API permissions, credentials/certificates where required, and exact callback URIs. State required directory roles and expected token audiences. No public-client secret and no undocumented insecure authentication bypass.
4. **Presenter client configuration:** Supported, secret-free MCP configuration for the verified Copilot surface(s), trust/authentication setup, per-call approval instructions, and safe reset of sessions/caches when required. Merge rather than overwrite existing client settings.
5. **Operator commands:** Bootstrap, configure, deploy, seed, start locally, check health, verify auth, run individual scenarios, run all checks, reset fixtures, inspect traces, and teardown. Keep reset capability outside agent-callable tools, scoped to demo data, and protected from accidental production use.
6. **Tests and evidence:** Unit checks for policy and argument validation; integration checks for discovery, audience validation, scopes, user/client boundaries, delegation, upstream enforcement, idempotency, and all three adversarial cases. Include a manual client approval checklist, since a direct API test cannot prove the Copilot approval UI worked.
7. **Presenter runbook:** The timed schedule above, exact chat prompts, expected outputs, code bookmarks, recovery paths, and a rehearsal checklist. Live chat prompts should operate prepared tools and inspect evidence, not ask Copilot to rewrite or redeploy the project.
8. **Attendee materials:** Concise setup README, architecture/trust-boundary diagram, protocol sequence diagram, coverage matrix, control map, sanitized example audit records, and a clearly labeled appendix for deeper topics and sources.

For cloud deployment, generate the complete infrastructure and configuration steps now, but ask for explicit approval before provisioning or modifying the tenant/subscription. Use placeholders only for environment-specific values and credentials, never as substitutes for required business logic or security checks.

## Reliability And Safety

- Use a dedicated demo resource group and least-privilege identities. Include quotas, model availability, deployment latency, expected cost drivers, and cleanup guidance in preflight.
- Use managed identity/standard credential chains where supported; keep necessary confidential-client credentials in approved secret storage. Never put secrets into Copilot prompts, source files, logs, command arguments, or screenshots.
- Prebuild, deploy, consent, warm services, seed data, test conference connectivity, and rehearse all logins before stage time. Avoid scale-to-zero cold starts during the session and document the temporary cost tradeoff.
- Apply bounded timeouts and retry policies. Do not retry consequential mutations without an idempotency guarantee. Bound model input/output size and never let a model response change policy.
- Provide a resettable dataset with independently runnable scenarios so one failed step does not prevent the next. Rehearse successive runs without manual data repair.
- Provide explicit fallback tiers: cloud live; local service execution with actual reachable identity/model dependencies; then sanitized recorded traces or a clearly labeled offline simulation. Offline mode cannot demonstrate live Entra authorization or live Foundry inference.
- Provide the commands to capture replay artifacts during a successful rehearsal. Do not fabricate recordings or present fixture output as observed cloud behavior.
- Keep fail-open switches and intentionally vulnerable endpoints out of the deployed demo. Negative cases should fail against the secure implementation.

## Verification And Completion Contract

Build incrementally and run focused checks after each meaningful change. Complete all feasible local validation. With authorized cloud access, run deployment validation and a full rehearsal against the real environment.

The project is ready only when:

- Every proposal point maps to an implementation, evidence, and a moment within the 25-minute schedule.
- The primary Copilot client actually discovers and invokes the protected remote MCP tools, and its approval behavior is manually verified.
- Foundry actually runs behind `assess_refund`; its model invocation is visible and never acts as the authorization authority.
- The OAuth trace is supported by observed evidence, including the resource/scopes/audience mapping and any explicitly disclosed compatibility limitations.
- One permitted refund succeeds exactly once, and missing-scope, invalid-argument, wrong-user/client, confused-deputy, and wrong-audience cases fail at their intended boundaries without changing the ledger.
- The upstream API receives its own audience-bound delegated token and proves preserved user identity. A missing delegated flow is a blocker, not permission to substitute application authority.
- The annotation and approval demonstrations accurately separate hints, human choice, and server enforcement.
- Audit evidence identifies the request, user, client, resource, policy, and result without leaking secrets or claiming unavailable client-side evidence.
- Local checks pass, cloud checks are either evidenced or explicitly marked unverified, the reset path works, and the presenter has rehearsed the 25-minute flow.

Finish with a concise handoff: generated file locations, commands executed and outcomes, coverage status, remaining environment-specific actions, estimated stage timing versus actual rehearsal timing, limitations, and links to the runbook and attendee control map. Never call the demo ready when a required security boundary has only been mocked.

## Authoritative Starting References

Recheck these and their relevant linked pages at implementation time; the event is in October 2026 and product behavior can change. Prefer dated/versioned sources in the generated compatibility record.

- Session requirements: `Events/MCP-Dev-Summit-Toronto-2026-Approved-Proposals.md`
- MCP authorization: https://modelcontextprotocol.io/specification/latest/basic/authorization
- MCP documentation index: https://modelcontextprotocol.io/llms.txt
- GitHub Copilot app: https://docs.github.com/en/copilot/concepts/agents/github-copilot-app
- VS Code MCP support: https://code.visualstudio.com/docs/copilot/customization/mcp-servers
- Microsoft Entra identity platform: https://learn.microsoft.com/en-us/entra/identity-platform/
- Microsoft Foundry documentation: https://learn.microsoft.com/en-us/azure/ai-foundry/
- Azure Container Apps: https://learn.microsoft.com/en-us/azure/container-apps/
- Azure Monitor/Application Insights: https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview

Start by reporting the selected architecture and any true compatibility blockers briefly, then implement and verify the project. Keep the live demo centered on the question: **Who can call this tool, for this resource, with these arguments, and where is that decision enforced?**