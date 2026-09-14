param(
  [Parameter(Mandatory=$true)][string]$TenantId,
  [string]$Prefix = 'mcp-auth-demo',
  [string[]]$RedirectUris = @('https://vscode.dev/redirect'),
  [switch]$CreateClientSecret,
  [switch]$Confirm
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-AzJson {
  param([string[]]$Args)
  $json = & az @Args -o json
  if ($LASTEXITCODE -ne 0) { throw "az $($Args -join ' ') failed" }
  if ([string]::IsNullOrWhiteSpace($json)) { return $null }
  return $json | ConvertFrom-Json
}

function Get-AppByName {
  param([string]$DisplayName)
  $apps = Invoke-AzJson @('ad','app','list','--display-name',$DisplayName)
  if ($apps.Count -gt 1) { throw "More than one app named $DisplayName; rename or clean up duplicates." }
  return $apps | Select-Object -First 1
}

function New-OrGetApp {
  param([string]$DisplayName)
  $app = Get-AppByName $DisplayName
  if ($app) { return $app }
  if (-not $Confirm) { Write-Host "Would create app registration: $DisplayName"; return $null }
  return Invoke-AzJson @('ad','app','create','--display-name',$DisplayName,'--sign-in-audience','AzureADMyOrg')
}

function ScopeObject {
  param($ExistingApi, [string]$Value, [string]$AdminConsentDisplayName, [string]$AdminConsentDescription)
  $existing = @($ExistingApi.oauth2PermissionScopes) | Where-Object { $_.value -eq $Value } | Select-Object -First 1
  $id = if ($existing) { $existing.id } else { [guid]::NewGuid().ToString() }
  return @{
    id = $id
    value = $Value
    type = 'Admin'
    isEnabled = $true
    adminConsentDisplayName = $AdminConsentDisplayName
    adminConsentDescription = $AdminConsentDescription
  }
}

function Patch-Application {
  param([string]$ObjectId, [hashtable]$Body)
  $json = $Body | ConvertTo-Json -Depth 20 -Compress
  if (-not $Confirm) { Write-Host "Would PATCH application $ObjectId with $json"; return }
  & az rest --method PATCH --url "https://graph.microsoft.com/v1.0/applications/$ObjectId" --headers "Content-Type=application/json" --body $json | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Graph PATCH failed for $ObjectId" }
}

Write-Host "Tenant: $TenantId"
Write-Host "Prefix: $Prefix"
Write-Host "Redirect URIs: $($RedirectUris -join ', ')"
Write-Host "Plan: create/update Upstream Refund API, MCP Resource A, MCP Resource B, and public MCP client."
Write-Host "No changes are made unless -Confirm is supplied."

$upstream = New-OrGetApp "$Prefix-upstream-refund-api"
$mcpA = New-OrGetApp "$Prefix-mcp-resource-a"
$mcpB = New-OrGetApp "$Prefix-mcp-resource-b"
$client = New-OrGetApp "$Prefix-mcp-public-client"

if (-not $Confirm) { exit 0 }

$upstream = Get-AppByName "$Prefix-upstream-refund-api"
$mcpA = Get-AppByName "$Prefix-mcp-resource-a"
$mcpB = Get-AppByName "$Prefix-mcp-resource-b"
$client = Get-AppByName "$Prefix-mcp-public-client"

$ledgerScope = ScopeObject $upstream.api 'Ledger.Refund' 'Refund ledger' 'Allows refund mutations in the synthetic demo ledger.'
$readScope = ScopeObject $mcpA.api 'Refunds.Read' 'Read refund data' 'Allows reading order and refund assessment data from MCP Resource A.'
$writeScope = ScopeObject $mcpA.api 'Refunds.Write' 'Write refunds' 'Allows invoking refund_order through MCP Resource A.'
$probeScope = ScopeObject $mcpB.api 'Probe.Read' 'Probe Resource B' 'Allows wrong-audience probe calls to MCP Resource B.'

Patch-Application $upstream.id @{
  identifierUris = @("api://$($upstream.appId)")
  api = @{ requestedAccessTokenVersion = 2; oauth2PermissionScopes = @($ledgerScope) }
}

Patch-Application $mcpA.id @{
  identifierUris = @("api://$($mcpA.appId)")
  api = @{
    requestedAccessTokenVersion = 2
    oauth2PermissionScopes = @($readScope, $writeScope)
    preAuthorizedApplications = @(@{ appId = $client.appId; delegatedPermissionIds = @($readScope.id, $writeScope.id) })
  }
  requiredResourceAccess = @(@{ resourceAppId = $upstream.appId; resourceAccess = @(@{ id = $ledgerScope.id; type = 'Scope' }) })
}

Patch-Application $mcpB.id @{
  identifierUris = @("api://$($mcpB.appId)")
  api = @{ requestedAccessTokenVersion = 2; oauth2PermissionScopes = @($probeScope) }
}

Patch-Application $client.id @{
  isFallbackPublicClient = $true
  publicClient = @{ redirectUris = $RedirectUris }
  requiredResourceAccess = @(@{ resourceAppId = $mcpA.appId; resourceAccess = @(@{ id = $readScope.id; type = 'Scope' }, @{ id = $writeScope.id; type = 'Scope' }) })
}

if ($CreateClientSecret) {
  Write-Host 'Creating MCP Resource A client secret. Store the value in Key Vault; it is printed once by Azure CLI.'
  & az ad app credential reset --id $mcpA.appId --display-name 'phase4-demo-obo' --years 1
  if ($LASTEXITCODE -ne 0) { throw 'Secret creation failed.' }
} else {
  Write-Host 'No secret created. Preferred production path: add a certificate credential to MCP Resource A and put only a reference/credential material in Key Vault as appropriate for the app.'
}

Write-Host ''
Write-Host 'Expected values for infra parameters:'
Write-Host "mcpAClientId=$($mcpA.appId)"
Write-Host "mcpAAudience=api://$($mcpA.appId)"
Write-Host "mcpBAudience=api://$($mcpB.appId)"
Write-Host "upstreamApiAudience=api://$($upstream.appId)"
Write-Host "upstreamApiScope=api://$($upstream.appId)/Ledger.Refund"
Write-Host "allowedClientIds=$($client.appId)"
Write-Host ''
Write-Host 'Admin consent commands/URLs:'
Write-Host "+ az ad app permission admin-consent --id $($mcpA.appId)"
Write-Host "+ az ad app permission admin-consent --id $($client.appId)"
Write-Host "https://login.microsoftonline.com/$TenantId/adminconsent?client_id=$($client.appId)&redirect_uri=https%3A%2F%2Fvscode.dev%2Fredirect"
