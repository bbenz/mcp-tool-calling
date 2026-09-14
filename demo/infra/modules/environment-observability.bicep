@description('Azure region for Container Apps Environment and observability resources.')
param location string

@description('Container Apps Environment name.')
param containerAppsEnvironmentName string

@description('Log Analytics workspace name.')
param logAnalyticsWorkspaceName string

@description('Workspace-based Application Insights component name.')
param applicationInsightsName string

@description('Tags applied to all resources in this module.')
param tags object

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerAppsEnvironmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

@description('Container Apps Environment resource ID.')
output containerAppsEnvironmentId string = environment.id

@description('Container Apps Environment default DNS domain.')
output containerAppsEnvironmentDefaultDomain string = environment.properties.defaultDomain

@description('Application Insights resource ID.')
output applicationInsightsResourceId string = appInsights.id

@description('Application Insights resource name.')
output applicationInsightsName string = appInsights.name

@description('Application Insights connection string for wiring into Container App environment variables. This is not output from main.bicep.')
@secure()
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
