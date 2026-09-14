# Phase 4 Azure infrastructure deliverables

This folder contains generated Bicep and scripts for the MCP authorization conference demo. The files are safe to review; do not run the deployment scripts until the presenter has filled placeholders and approved Azure changes.

## Critical boundary

Bicep deploys Azure Resource Manager resources only. It **does not and cannot create Microsoft Entra app registrations, delegated scopes, pre-authorized clients, client secrets, or admin consent grants**. Those directory objects are handled separately by `..\identity\setup-entra.ps1` or `..\identity\setup-entra.sh`.

## Resources

- Demo-owned resource group tagged `mcp-auth-demo=true`
- Azure Container Registry
- Log Analytics workspace
- Workspace-based Application Insights
- Azure Container Apps Environment
- Three Azure Container Apps:
  - `mcp-server` external HTTPS, port 8801
  - `resource-b` external HTTPS, port 8802, different audience
  - `upstream-api` internal ingress, port 8803
- User-assigned managed identity
- Azure Key Vault with RBAC; app identity receives only Key Vault Secrets User
- Optional Azure AI Services / Foundry account and optional model deployment, or references to an existing Foundry endpoint/resource

## Parameters

Start from `main.bicepparam`. It intentionally contains placeholder tenant IDs, app IDs, registry names, Key Vault names, image tags, and Foundry values. Replace every `PLACEHOLDER`, all-zero GUID, and `REPLACE_WITH_*` value before running deployment.

Important values from Entra setup:

- `mcpAAudience = api://<mcp-resource-a-client-id>`
- `mcpBAudience = api://<mcp-resource-b-client-id>` and it must differ from `mcpAAudience`
- `upstreamApiAudience = api://<upstream-api-client-id>`
- `upstreamApiScope = api://<upstream-api-client-id>/Ledger.Refund`
- `allowedClientIds` is a comma-separated list of approved public MCP client app IDs

## Foundry notes

The default uses an existing Foundry/Azure AI endpoint. To create an Azure AI Services account, set `createFoundryAccount=true`. Keep `createFoundryDeployment=false` until the model name/version are verified in the Azure AI Foundry model catalog for the selected region. The Bicep comments note that the default RBAC role is `Cognitive Services OpenAI User`; verify whether current project-scoped Foundry roles are required for your resource shape.

## Build and deploy flow

The scripts are generated for operator review and are not run by this agent.

PowerShell:

```powershell
cd C:\githublocal\mcp-tool-calling\demo\infra
.\deploy.ps1 -ResourceGroupName rg-mcp-auth-demo -Location canadacentral -AcrName <uniqueacr> -KeyVaultName <unique-kv> -Tag <image-tag> -Confirm
```

Bash:

```bash
cd demo/infra
./deploy.sh --resource-group rg-mcp-auth-demo --location canadacentral --acr-name <uniqueacr> --key-vault-name <unique-kv> --tag <image-tag> --yes
```

The scripts:

1. Echo every command.
2. Bootstrap the resource group, ACR, environment, identity, Key Vault, and observability with `deployContainerApps=false`.
3. Build and push the three images with `az acr build`.
4. Redeploy with `deployContainerApps=true` and the final image names.

## Outputs

`main.bicep` emits:

- Public FQDN for MCP Resource A
- Public FQDN for MCP Resource B
- Internal FQDN for upstream API
- ACR login server
- Managed identity client ID and principal ID
- Application Insights resource name, not connection string
- Key Vault name
- Foundry endpoint

The Application Insights connection string is passed to apps but not emitted from the top-level deployment output; read it from the resource if needed.

## Cost drivers

- Container Apps min replicas are set to 1 to avoid cold starts during the timed talk. This costs more than scale-to-zero; scale down after the event.
- Log Analytics ingestion and retention.
- Application Insights telemetry volume.
- ACR storage/build usage.
- Azure AI/Foundry model deployment throughput and token usage.

## Teardown

Use the teardown scripts only for demo-owned resource groups. They require confirmation and refuse to delete unless the target resource group has the expected tag.

```powershell
.\teardown.ps1 -ResourceGroupName rg-mcp-auth-demo -Confirm
```

```bash
./teardown.sh --resource-group rg-mcp-auth-demo --yes
```
