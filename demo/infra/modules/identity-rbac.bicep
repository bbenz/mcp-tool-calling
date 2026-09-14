@description('User-assigned managed identity name.')
param managedIdentityName string

@description('Azure region for the managed identity.')
param location string

@description('ACR resource ID for AcrPull assignment.')
param acrResourceId string

@description('Key Vault resource ID for Key Vault Secrets User assignment.')
param keyVaultResourceId string

@description('Application Insights resource ID for optional Monitoring Metrics Publisher assignment.')
param applicationInsightsResourceId string

@description('Foundry/Azure AI account name in this resource group for inference RBAC. Empty skips assignment.')
param foundryAccountNameForRbac string

@description('Role definition ID for Foundry/Azure AI inference. Default in main.bicep is Cognitive Services OpenAI User; verify if using Foundry project-scoped roles.')
param foundryInferenceRoleDefinitionId string

@description('Tags applied to the managed identity.')
param tags object

var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var keyVaultSecretsUserRoleDefinitionId = '4633458b-17de-408a-b874-0445c86b69e6'
var monitoringMetricsPublisherRoleDefinitionId = '3913510d-42f4-4e42-8a64-420c390055eb'

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
  tags: tags
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrResourceId, '/'))
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: last(split(keyVaultResourceId, '/'))
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: last(split(applicationInsightsResourceId, '/'))
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = if (!empty(foundryAccountNameForRbac)) {
  name: foundryAccountNameForRbac
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, managedIdentityName, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
  }
}

resource keyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentityName, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleDefinitionId)
  }
}

// Application Insights connection strings are not secrets, but this role is useful if the SDK emits custom metrics directly. Remove if telemetry is log-only.
resource monitoringMetricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(appInsights.id, managedIdentityName, monitoringMetricsPublisherRoleDefinitionId)
  scope: appInsights
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringMetricsPublisherRoleDefinitionId)
  }
}

// Least privilege depends on the exact Foundry resource shape. For Azure OpenAI/Azure AI Services inference, Cognitive Services OpenAI User is narrower than Azure AI Developer.
resource foundryInference 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(foundryAccountNameForRbac)) {
  name: guid(foundryAccount.id, managedIdentityName, foundryInferenceRoleDefinitionId)
  scope: foundryAccount
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryInferenceRoleDefinitionId)
  }
}

@description('Managed identity resource ID.')
output managedIdentityResourceId string = identity.id

@description('Managed identity client ID.')
output managedIdentityClientId string = identity.properties.clientId

@description('Managed identity principal ID.')
output managedIdentityPrincipalId string = identity.properties.principalId
