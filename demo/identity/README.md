# Microsoft Entra identity setup

These scripts configure directory objects for the MCP authorization demo. They are separate from Bicep because Azure Resource Manager/Bicep cannot create or manage Entra app registrations, delegated scopes, pre-authorized client applications, or admin consent.

## Required roles

The operator typically needs Application Administrator or Cloud Application Administrator to create/update app registrations. Granting tenant-wide admin consent requires a role allowed to consent for the organization, such as Cloud Application Administrator, Application Administrator, Privileged Role Administrator, or Global Administrator depending on tenant policy.

## What the scripts create

1. **Upstream Refund API** app registration
   - Application ID URI: `api://<upstream-app-id>`
   - Delegated scope: `Ledger.Refund`
   - Access token version: 2
2. **MCP Resource A**
   - Application ID URI: `api://<mcp-a-app-id>`
   - Delegated scopes: `Refunds.Read`, `Refunds.Write`
   - Confidential client for on-behalf-of; use a certificate where practical or create a temporary client secret and store it in Key Vault
   - Delegated API permission to Upstream `Ledger.Refund`
   - Pre-authorizes the MCP public client for Resource A scopes
3. **MCP Resource B**
   - Application ID URI: `api://<mcp-b-app-id>`
   - Delegated scope: `Probe.Read`
   - This audience must differ from Resource A
4. **MCP client**
   - Public/native client
   - No secret; public clients must not be issued or configured with a client secret
   - Redirect URIs require final verification, see below

## Redirect URI status

Verified from current VS Code source/docs on 2026-09-14:

- VS Code's dynamic authentication provider uses `https://vscode.dev/redirect` as the OAuth redirect URI in the authorization request.
- VS Code also constructs an internal callback URI of the form `<app-uri-scheme>://dynamicauthprovider/<authorization-server>/authorize?...` and routes through `vscode.env.asExternalUri`.

A separate redirect URI for a standalone "GitHub Copilot app" outside VS Code could not be confirmed from public documentation, and **it should not be guessed**. To establish it for your own tenant: trigger the OAuth flow once in the real client, read the reply URL back out of the Entra `AADSTS50011` mismatch error, and add exactly that value to the public client's redirect URI list.

## RFC 8707 resource vs Entra v2 scopes

MCP authorization requires clients to send RFC 8707 `resource=<canonical MCP server URL>` to bind the requested token to the target resource server. Entra v2 app registrations, however, primarily select API audiences by resource-qualified `scope` values such as:

- `api://<mcp-a-app-id>/Refunds.Read`
- `api://<mcp-a-app-id>/Refunds.Write`
- `api://<upstream-app-id>/Ledger.Refund`

The RFC 8707 `resource` parameter and Entra resource-qualified `scope` strings are related but **not interchangeable**. For Entra v2, do not use a bare v1-style `resource` parameter as a substitute for `scope`. The demo should observe that requested Entra scopes determine the JWT `aud`; MCP resource metadata/runtime policy still validates the canonical resource binding and accepted audience.

## Expected token claims

All API app registrations set `accessTokenAcceptedVersion` / `requestedAccessTokenVersion` to 2. Expected access token claims include:

- `aud`: `api://<app-id>` of Resource A, Resource B, or Upstream API
- `iss`: `https://login.microsoftonline.com/<tenant-id>/v2.0`
- `tid`: tenant ID
- `oid`: user object ID for delegated user tokens
- `sub`: pairwise subject
- `scp`: delegated scopes (`Refunds.Read`, `Refunds.Write`, `Ledger.Refund`, or `Probe.Read`)
- `azp` in v2 tokens for the authorized party/client app; some libraries and v1 tokens use `appid`

## On-behalf-of rule

On-behalf-of requires that the MCP server be a **confidential client with a credential** and that the incoming token's `aud` be MCP Resource A. Never forward the incoming Resource A access token to the upstream API. MCP Resource A must exchange it for a new upstream token with `aud=api://<upstream-app-id>` and `scp=Ledger.Refund`.

## Running the scripts

PowerShell dry run:

```powershell
cd demo\identity
.\setup-entra.ps1 -TenantId <tenant-guid> -Prefix mcp-auth-demo
```

PowerShell apply:

```powershell
.\setup-entra.ps1 -TenantId <tenant-guid> -Prefix mcp-auth-demo -Confirm
```

Bash dry run:

```bash
cd demo/identity
./setup-entra.sh --tenant-id <tenant-guid> --prefix mcp-auth-demo
```

Bash apply:

```bash
./setup-entra.sh --tenant-id <tenant-guid> --prefix mcp-auth-demo --yes
```

To create a temporary secret for Resource A, add `-CreateClientSecret` or `--create-client-secret`, then immediately store the printed value in Key Vault as `mcp-a-client-credential`. Prefer certificate credentials for non-demo use.

## Manual portal fallback

1. Open Microsoft Entra admin center > App registrations > New registration.
2. Create `mcp-auth-demo-upstream-refund-api`, single tenant.
3. In Expose an API, set Application ID URI to `api://<upstream-app-id>`, add delegated scope `Ledger.Refund`, admin consent only, and set accepted token version to 2 in the manifest (`accessTokenAcceptedVersion`: 2).
4. Create `mcp-auth-demo-mcp-resource-a`. Set Application ID URI to `api://<mcp-a-app-id>`, add delegated scopes `Refunds.Read` and `Refunds.Write`, and set token version 2.
5. For Resource A, add API permission to the upstream API delegated scope `Ledger.Refund`.
6. Add a certificate or secret credential to Resource A. Store only the resulting secret value/certificate material needed by the app in Key Vault; do not put it in source.
7. Create `mcp-auth-demo-mcp-resource-b`. Set Application ID URI to `api://<mcp-b-app-id>`, add delegated scope `Probe.Read`, and set token version 2.
8. Create `mcp-auth-demo-mcp-public-client`. Configure it as a mobile/desktop public client, add verified redirect URIs, and enable public client flows if required.
9. On the public client, add delegated API permissions to Resource A (`Refunds.Read`, `Refunds.Write`).
10. On Resource A, pre-authorize the public client for Resource A scopes.
11. Grant admin consent for Resource A's upstream permission and the public client's Resource A permissions.
12. Copy the app IDs, Application ID URIs, and scope strings into `..\infra\main.bicepparam`.
