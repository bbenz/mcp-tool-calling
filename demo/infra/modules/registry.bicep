@description('Azure Container Registry name. Must be globally unique, 5-50 lowercase alphanumeric characters.')
param acrName string

@description('Azure region for the registry.')
param location string

@description('Tags applied to the registry.')
param tags object

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: {
    name: 'Basic'
  }
  tags: tags
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    policies: {
      quarantinePolicy: {
        status: 'disabled'
      }
      trustPolicy: {
        type: 'Notary'
        status: 'disabled'
      }
      retentionPolicy: {
        days: 7
        status: 'enabled'
      }
    }
  }
}

@description('ACR resource ID.')
output acrResourceId string = acr.id

@description('ACR login server.')
output acrLoginServer string = acr.properties.loginServer
