@description('Azure region for the optional Azure AI Services account.')
param location string

@description('Set true to create an Azure AI Services account suitable for Foundry-style inference; false references an existing endpoint/scope.')
param createFoundryAccount bool

@description('Optional Azure AI Services account name, or the existing account name when assigning RBAC in this resource group.')
param foundryAccountName string

@description('Set true to create a model deployment under the optional account. Keep false until modelName/modelVersion are verified for the region.')
param createFoundryDeployment bool

@description('Foundry deployment name used by the demo app.')
param foundryDeploymentName string

@description('Model format for optional deployment, for example OpenAI.')
param modelFormat string

@description('Model name for optional deployment. Placeholder only; check the Azure AI Foundry catalog for regional availability.')
param modelName string

@description('Model version for optional deployment. Placeholder only; check the Azure AI Foundry catalog for regional availability.')
param modelVersion string

@description('SKU name for optional model deployment.')
param deploymentSkuName string

@description('Capacity for optional model deployment.')
param deploymentCapacity int

@description('Existing Foundry/Azure AI endpoint when createFoundryAccount is false.')
param existingFoundryEndpoint string

@description('Existing Foundry/Azure AI resource ID for documentation/operator reference when createFoundryAccount is false.')
param existingFoundryScopeResourceId string

@description('Tags applied to optional resources.')
param tags object

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = if (createFoundryAccount) {
  name: foundryAccountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  tags: tags
  properties: {
    customSubDomainName: foundryAccountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

// Azure AI/Foundry model availability changes by date and region. Keep createFoundryDeployment=false until the operator verifies modelName/modelVersion in the Azure AI Foundry model catalog for the selected region.
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = if (createFoundryAccount && createFoundryDeployment) {
  parent: account
  name: foundryDeploymentName
  sku: {
    name: deploymentSkuName
    capacity: deploymentCapacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

@description('Foundry/Azure AI endpoint to configure on the app.')
output foundryEndpoint string = createFoundryAccount ? account!.properties.endpoint : existingFoundryEndpoint

@description('Foundry/Azure AI account name to use for same-resource-group RBAC assignment. Empty skips that assignment.')
output foundryAccountNameForRbac string = (!empty(foundryAccountName) && (createFoundryAccount || !empty(existingFoundryScopeResourceId))) ? foundryAccountName : ''
