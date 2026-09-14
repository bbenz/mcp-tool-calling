targetScope = 'subscription'

@description('Azure region for all regional demo resources. Verify Microsoft Foundry model availability in this region before deployment.')
param location string = 'canadacentral'

@description('Name of the demo-owned resource group to create or update. Teardown scripts refuse to operate unless this resource group has the demo tag.')
param resourceGroupName string

@description('Tag key used to scope demo-owned resources and teardown safety checks.')
param demoTagName string = 'mcp-auth-demo'

@description('Tag value used to scope demo-owned resources and teardown safety checks.')
param demoTagValue string = 'true'

@description('Short lowercase prefix used in resource names. Use letters and numbers only where possible.')
param namePrefix string = 'mcpauthdemo'

@description('Container Apps Environment name.')
param containerAppsEnvironmentName string = '${namePrefix}-cae'

@description('Log Analytics workspace name.')
param logAnalyticsWorkspaceName string = '${namePrefix}-law'

@description('Workspace-based Application Insights component name.')
param applicationInsightsName string = '${namePrefix}-appi'

@description('Azure Container Registry name. Must be globally unique, 5-50 lowercase alphanumeric characters.')
param acrName string

@description('User-assigned managed identity name used by the Container Apps.')
param managedIdentityName string = '${namePrefix}-uami'

@description('Key Vault name for storing the MCP server confidential-client credential reference. Must be globally unique.')
param keyVaultName string

@description('Whether to deploy Container Apps. deploy.ps1/deploy.sh use false for bootstrap, build images to ACR, then true for the final deployment.')
param deployContainerApps bool = true

@description('Container image for MCP Resource A.')
param mcpServerImage string

@description('Container image for MCP Resource B.')
param resourceBImage string

@description('Container image for upstream refund API.')
param upstreamApiImage string

@description('Container App name for MCP Resource A.')
param mcpServerAppName string = 'mcp-server'

@description('Container App name for MCP Resource B.')
param resourceBAppName string = 'resource-b'

@description('Container App name for the upstream refund API.')
param upstreamApiAppName string = 'upstream-api'

@description('Microsoft Entra tenant ID that issues demo tokens.')
param entraTenantId string

@description('Microsoft Entra authority URL, normally https://login.microsoftonline.com/<tenant-id>/v2.0.')
param entraAuthority string

@description('Application/client ID of the MCP Resource A app registration.')
param mcpAClientId string

@description('Audience / Application ID URI accepted by MCP Resource A, for example api://<app-id-a>.')
param mcpAAudience string

@description('Key Vault secret URI for MCP Resource A client credential. The secret value is not created by Bicep.')
param mcpAClientSecretKeyVaultSecretUri string

@description('Audience / Application ID URI accepted by MCP Resource B. Must differ from mcpAAudience.')
param mcpBAudience string

@description('Audience / Application ID URI accepted by the upstream refund API.')
param upstreamApiAudience string

@description('Delegated scope MCP Resource A requests in the on-behalf-of exchange, for example api://<app-id-upstream>/Ledger.Refund.')
param upstreamApiScope string

@description('Comma-separated Microsoft Entra client IDs allowed to call the MCP tools.')
param allowedClientIds string

@description('Per-call refund limit in minor currency units.')
param refundPerCallLimitMinor string = '25000'

@description('Runtime policy version surfaced in logs and authorization decisions.')
param policyVersion string = 'phase4-demo-2026-10-06'

@description('Container-local audit log path. Use an attached volume for production; this demo uses container filesystem logging plus App Insights.')
param auditLogPath string = '/app/audit/audit.log'

@description('Foundry/Azure AI endpoint. Leave empty when createFoundryAccount is true and use the created endpoint output after deployment, or pass an existing project/account endpoint.')
param foundryEndpoint string = ''

@description('Foundry model deployment name to call from assess_refund. Deployment availability is regional; check Azure AI Foundry model catalog before using.')
param foundryDeployment string = 'refund-assessor'

@description('Foundry inference API version used by the app.')
param foundryApiVersion string = '2024-10-21'

@description('Set true to create an Azure AI Services account suitable for Azure AI Foundry-style model deployments. Set false to reference an existing endpoint/scope.')
param createFoundryAccount bool = false

@description('Name of the optional Azure AI Services account created when createFoundryAccount is true, or an existing same-resource-group account for RBAC.')
param foundryAccountName string = '${namePrefix}-ai'

@description('Set true to create a model deployment under the optional Azure AI Services account. Requires modelName/modelVersion/modelFormat to be checked for regional availability.')
param createFoundryDeployment bool = false

@description('Model format for optional Azure AI deployment, for example OpenAI. Parameterized intentionally; do not assume all regions support the same models.')
param foundryModelFormat string = 'OpenAI'

@description('Model name for optional Azure AI deployment. Placeholder only; verify in Azure AI Foundry model catalog for the selected region before deployment.')
param foundryModelName string = 'REPLACE_WITH_REGIONALLY_AVAILABLE_MODEL'

@description('Model version for optional Azure AI deployment. Placeholder only; verify in Azure AI Foundry model catalog for the selected region before deployment.')
param foundryModelVersion string = 'REPLACE_WITH_MODEL_VERSION'

@description('SKU name for optional Azure AI model deployment.')
param foundryDeploymentSkuName string = 'GlobalStandard'

@description('Capacity for optional Azure AI model deployment.')
param foundryDeploymentCapacity int = 1

@description('Role definition ID to grant the app identity on the Foundry/Azure AI scope. Default is Cognitive Services OpenAI User; verify against current Foundry RBAC for your resource type.')
param foundryInferenceRoleDefinitionId string = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

@description('Existing Foundry/Azure AI resource scope for operator reference when createFoundryAccount is false. For automatic RBAC, foundryAccountName must name a Cognitive Services account in the demo resource group.')
param existingFoundryScopeResourceId string = ''

var tags = {
  '${demoTagName}': demoTagValue
  workload: 'mcp-auth-conference-demo'
  phase: '4'
  event: 'MCP Dev Summit Toronto 2026'
}

// Microsoft Entra application registrations and service principals are directory objects, not Azure Resource Manager resources.
// Bicep intentionally does NOT create them. Run ../identity/setup-entra.ps1 or setup-entra.sh after reviewing its dry-run output.

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  scope: rg
  params: {
    acrName: acrName
    location: location
    tags: tags
  }
}

module observability 'modules/environment-observability.bicep' = {
  name: 'environment-observability'
  scope: rg
  params: {
    location: location
    containerAppsEnvironmentName: containerAppsEnvironmentName
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
    tags: tags
  }
}

module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  scope: rg
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: tags
  }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  scope: rg
  params: {
    location: location
    createFoundryAccount: createFoundryAccount
    foundryAccountName: foundryAccountName
    createFoundryDeployment: createFoundryDeployment
    foundryDeploymentName: foundryDeployment
    modelFormat: foundryModelFormat
    modelName: foundryModelName
    modelVersion: foundryModelVersion
    deploymentSkuName: foundryDeploymentSkuName
    deploymentCapacity: foundryDeploymentCapacity
    existingFoundryEndpoint: foundryEndpoint
    existingFoundryScopeResourceId: existingFoundryScopeResourceId
    tags: tags
  }
}

module identityRbac 'modules/identity-rbac.bicep' = {
  name: 'identity-rbac'
  scope: rg
  params: {
    managedIdentityName: managedIdentityName
    location: location
    acrResourceId: registry.outputs.acrResourceId
    keyVaultResourceId: keyvault.outputs.keyVaultResourceId
    applicationInsightsResourceId: observability.outputs.applicationInsightsResourceId
    foundryAccountNameForRbac: foundry.outputs.foundryAccountNameForRbac
    foundryInferenceRoleDefinitionId: foundryInferenceRoleDefinitionId
    tags: tags
  }
}

module apps 'modules/containerapps.bicep' = if (deployContainerApps) {
  name: 'containerapps'
  scope: rg
  params: {
    location: location
    environmentId: observability.outputs.containerAppsEnvironmentId
    environmentDefaultDomain: observability.outputs.containerAppsEnvironmentDefaultDomain
    acrLoginServer: registry.outputs.acrLoginServer
    managedIdentityId: identityRbac.outputs.managedIdentityResourceId
    managedIdentityClientId: identityRbac.outputs.managedIdentityClientId
    applicationInsightsConnectionString: observability.outputs.applicationInsightsConnectionString
    mcpServerAppName: mcpServerAppName
    resourceBAppName: resourceBAppName
    upstreamApiAppName: upstreamApiAppName
    mcpServerImage: mcpServerImage
    resourceBImage: resourceBImage
    upstreamApiImage: upstreamApiImage
    entraTenantId: entraTenantId
    entraAuthority: entraAuthority
    mcpAClientId: mcpAClientId
    mcpAAudience: mcpAAudience
    mcpAClientSecretKeyVaultSecretUri: mcpAClientSecretKeyVaultSecretUri
    mcpBAudience: mcpBAudience
    upstreamApiAudience: upstreamApiAudience
    upstreamApiScope: upstreamApiScope
    allowedClientIds: allowedClientIds
    foundryEndpoint: empty(foundry.outputs.foundryEndpoint) ? foundryEndpoint : foundry.outputs.foundryEndpoint
    foundryDeployment: foundryDeployment
    foundryApiVersion: foundryApiVersion
    refundPerCallLimitMinor: refundPerCallLimitMinor
    policyVersion: policyVersion
    auditLogPath: auditLogPath
    tags: tags
  }
}

@description('Public FQDN of MCP Resource A. Empty when deployContainerApps=false.')
output mcpServerFqdn string = deployContainerApps ? apps!.outputs.mcpServerFqdn : ''

@description('Public FQDN of MCP Resource B. Empty when deployContainerApps=false.')
output resourceBFqdn string = deployContainerApps ? apps!.outputs.resourceBFqdn : ''

@description('Internal FQDN of upstream-api. Empty when deployContainerApps=false.')
output upstreamApiFqdn string = deployContainerApps ? apps!.outputs.upstreamApiFqdn : ''

@description('ACR login server.')
output acrLoginServer string = registry.outputs.acrLoginServer

@description('User-assigned managed identity client ID.')
output managedIdentityClientId string = identityRbac.outputs.managedIdentityClientId

@description('User-assigned managed identity principal ID.')
output managedIdentityPrincipalId string = identityRbac.outputs.managedIdentityPrincipalId

@description('Application Insights resource name. Read the connection string from Azure if needed; it is intentionally not emitted as an output.')
output applicationInsightsName string = observability.outputs.applicationInsightsName

@description('Key Vault name.')
output keyVaultName string = keyvault.outputs.keyVaultName

@description('Foundry/Azure AI endpoint selected or created for assess_refund.')
output foundryEndpoint string = empty(foundry.outputs.foundryEndpoint) ? foundryEndpoint : foundry.outputs.foundryEndpoint
