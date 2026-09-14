using './main.bicep'

param location = 'canadacentral'
param resourceGroupName = 'rg-mcp-auth-demo-PLACEHOLDER'
param demoTagName = 'mcp-auth-demo'
param demoTagValue = 'true'
param namePrefix = 'mcpauthdemoPLACEHOLDER'
param acrName = 'mcpauthdemoacrPLACEHOLDER'
param keyVaultName = 'kv-mcp-auth-PLACEHOLDER'
param deployContainerApps = true

param mcpServerImage = 'mcpauthdemoacrPLACEHOLDER.azurecr.io/mcp-server:PLACEHOLDER_TAG'
param resourceBImage = 'mcpauthdemoacrPLACEHOLDER.azurecr.io/resource-b:PLACEHOLDER_TAG'
param upstreamApiImage = 'mcpauthdemoacrPLACEHOLDER.azurecr.io/upstream-api:PLACEHOLDER_TAG'

param entraTenantId = '00000000-0000-0000-0000-000000000000'
param entraAuthority = 'https://login.microsoftonline.com/00000000-0000-0000-0000-000000000000/v2.0'
param mcpAClientId = '11111111-1111-1111-1111-111111111111'
param mcpAAudience = 'api://11111111-1111-1111-1111-111111111111'
param mcpAClientSecretKeyVaultSecretUri = 'https://kv-mcp-auth-PLACEHOLDER.vault.azure.net/secrets/mcp-a-client-credential'
param mcpBAudience = 'api://22222222-2222-2222-2222-222222222222'
param upstreamApiAudience = 'api://33333333-3333-3333-3333-333333333333'
param upstreamApiScope = 'api://33333333-3333-3333-3333-333333333333/Ledger.Refund'
param allowedClientIds = '44444444-4444-4444-4444-444444444444'

param foundryEndpoint = 'https://REPLACE_WITH_EXISTING_FOUNDRY_ENDPOINT'
param foundryDeployment = 'refund-assessor'
param foundryApiVersion = '2024-10-21'
param createFoundryAccount = false
param existingFoundryScopeResourceId = '/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg-existing-ai/providers/Microsoft.CognitiveServices/accounts/REPLACE_WITH_ACCOUNT'
