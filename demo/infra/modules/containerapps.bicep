@description('Azure region for Container Apps.')
param location string

@description('Container Apps Environment resource ID.')
param environmentId string

@description('Container Apps Environment default domain.')
param environmentDefaultDomain string

@description('ACR login server.')
param acrLoginServer string

@description('User-assigned managed identity resource ID.')
param managedIdentityId string

@description('User-assigned managed identity client ID.')
param managedIdentityClientId string

@description('Application Insights connection string for app telemetry.')
@secure()
param applicationInsightsConnectionString string

@description('Container App name for MCP Resource A.')
param mcpServerAppName string

@description('Container App name for MCP Resource B.')
param resourceBAppName string

@description('Container App name for upstream refund API.')
param upstreamApiAppName string

@description('Container image for MCP Resource A.')
param mcpServerImage string

@description('Container image for MCP Resource B.')
param resourceBImage string

@description('Container image for upstream refund API.')
param upstreamApiImage string

@description('Microsoft Entra tenant ID.')
param entraTenantId string

@description('Microsoft Entra authority URL.')
param entraAuthority string

@description('Application/client ID of MCP Resource A app registration.')
param mcpAClientId string

@description('Audience accepted by MCP Resource A.')
param mcpAAudience string

@description('Key Vault secret URI for MCP Resource A client credential.')
param mcpAClientSecretKeyVaultSecretUri string

@description('Audience accepted by MCP Resource B. Must differ from MCP Resource A.')
param mcpBAudience string

@description('Audience accepted by upstream refund API.')
param upstreamApiAudience string

@description('Delegated upstream API scope used for OBO.')
param upstreamApiScope string

@description('Comma-separated list of authorized public client IDs.')
param allowedClientIds string

@description('Foundry/Azure AI endpoint.')
param foundryEndpoint string

@description('Foundry deployment name.')
param foundryDeployment string

@description('Foundry API version.')
param foundryApiVersion string

@description('Per-call refund limit in minor units.')
param refundPerCallLimitMinor string

@description('Runtime policy version.')
param policyVersion string

@description('Container-local audit log path.')
param auditLogPath string

@description('Tags applied to Container Apps.')
param tags object

var mcpAPublicUrl = 'https://${mcpServerAppName}.${environmentDefaultDomain}'
var mcpBPublicUrl = 'https://${resourceBAppName}.${environmentDefaultDomain}'
var upstreamApiUrl = 'https://${upstreamApiAppName}.${environmentDefaultDomain}'

var commonEnv = [
  { name: 'AUTH_MODE', value: 'entra' }
  { name: 'ENTRA_TENANT_ID', value: entraTenantId }
  { name: 'ENTRA_AUTHORITY', value: entraAuthority }
  { name: 'MCP_A_PUBLIC_URL', value: mcpAPublicUrl }
  { name: 'MCP_A_AUDIENCE', value: mcpAAudience }
  { name: 'MCP_A_CLIENT_ID', value: mcpAClientId }
  { name: 'MCP_A_PORT', value: '8801' }
  { name: 'MCP_B_PUBLIC_URL', value: mcpBPublicUrl }
  { name: 'MCP_B_AUDIENCE', value: mcpBAudience }
  { name: 'MCP_B_PORT', value: '8802' }
  { name: 'UPSTREAM_API_URL', value: upstreamApiUrl }
  { name: 'UPSTREAM_API_AUDIENCE', value: upstreamApiAudience }
  { name: 'UPSTREAM_API_SCOPE', value: upstreamApiScope }
  { name: 'UPSTREAM_API_PORT', value: '8803' }
  { name: 'ALLOWED_CLIENT_IDS', value: allowedClientIds }
  { name: 'FOUNDRY_ENDPOINT', value: foundryEndpoint }
  { name: 'FOUNDRY_DEPLOYMENT', value: foundryDeployment }
  { name: 'FOUNDRY_API_VERSION', value: foundryApiVersion }
  { name: 'AZURE_CLIENT_ID', value: managedIdentityClientId }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: applicationInsightsConnectionString }
  { name: 'REFUND_PER_CALL_LIMIT_MINOR', value: refundPerCallLimitMinor }
  { name: 'POLICY_VERSION', value: policyVersion }
  { name: 'AUDIT_LOG_PATH', value: auditLogPath }
]

var registryConfig = [
  {
    server: acrLoginServer
    identity: managedIdentityId
  }
]

resource mcpServer 'Microsoft.App/containerApps@2024-03-01' = {
  name: mcpServerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8801
        transport: 'http'
        allowInsecure: false
      }
      registries: registryConfig
      secrets: [
        {
          name: 'mcp-a-client-secret'
          keyVaultUrl: mcpAClientSecretKeyVaultSecretUri
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp-server'
          image: mcpServerImage
          env: concat(commonEnv, [
            { name: 'MCP_A_CLIENT_SECRET', secretRef: 'mcp-a-client-secret' }
          ])
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      // Keep minReplicas at 1 for the timed conference demo to avoid cold starts. This costs more; scale back down after the event.
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

resource resourceB 'Microsoft.App/containerApps@2024-03-01' = {
  name: resourceBAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8802
        transport: 'http'
        allowInsecure: false
      }
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'resource-b'
          image: resourceBImage
          env: commonEnv
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      // Keep minReplicas at 1 for the timed conference demo to avoid cold starts. This costs more; scale back down after the event.
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

resource upstreamApi 'Microsoft.App/containerApps@2024-03-01' = {
  name: upstreamApiAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 8803
        transport: 'http'
        allowInsecure: false
      }
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'upstream-api'
          image: upstreamApiImage
          env: commonEnv
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      // Keep minReplicas at 1 for the timed conference demo to avoid cold starts. This costs more; scale back down after the event.
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

@description('Public FQDN of MCP Resource A.')
output mcpServerFqdn string = mcpServer.properties.configuration.ingress.fqdn

@description('Public FQDN of MCP Resource B.')
output resourceBFqdn string = resourceB.properties.configuration.ingress.fqdn

@description('Internal FQDN of upstream-api.')
output upstreamApiFqdn string = upstreamApi.properties.configuration.ingress.fqdn
