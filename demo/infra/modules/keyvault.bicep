@description('Key Vault name. Must be globally unique.')
param keyVaultName string

@description('Azure region for the Key Vault.')
param location string

@description('Tags applied to the Key Vault.')
param tags object

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

@description('Key Vault resource ID.')
output keyVaultResourceId string = vault.id

@description('Key Vault name.')
output keyVaultName string = vault.name

@description('Key Vault URI.')
output keyVaultUri string = vault.properties.vaultUri
