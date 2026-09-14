param(
  [Parameter(Mandatory=$true)][string]$ResourceGroupName,
  [Parameter(Mandatory=$true)][string]$Location,
  [Parameter(Mandatory=$true)][string]$AcrName,
  [Parameter(Mandatory=$true)][string]$KeyVaultName,
  [string]$NamePrefix = 'mcpauthdemo',
  [string]$Tag = 'demo',
  [switch]$Confirm
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Confirm) {
  Write-Host 'Dry run only. Re-run with -Confirm to execute Azure CLI commands.'
  exit 0
}

function Invoke-Echo {
  param([Parameter(Mandatory=$true)][string]$Command)
  Write-Host "+ $Command"
  Invoke-Expression $Command
  if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE: $Command" }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$srcRoot = Join-Path $repoRoot 'demo\src'
$mcpImage = "$AcrName.azurecr.io/mcp-server:$Tag"
$bImage = "$AcrName.azurecr.io/resource-b:$Tag"
$upstreamImage = "$AcrName.azurecr.io/upstream-api:$Tag"

Invoke-Echo "az deployment sub create --location `"$Location`" --template-file `"$PSScriptRoot\main.bicep`" --parameters `"$PSScriptRoot\main.bicepparam`" resourceGroupName=`"$ResourceGroupName`" location=`"$Location`" namePrefix=`"$NamePrefix`" acrName=`"$AcrName`" keyVaultName=`"$KeyVaultName`" deployContainerApps=false mcpServerImage=`"$mcpImage`" resourceBImage=`"$bImage`" upstreamApiImage=`"$upstreamImage`""

Invoke-Echo "az acr build --registry `"$AcrName`" --image `"mcp-server:$Tag`" `"$srcRoot\mcp-server`""
Invoke-Echo "az acr build --registry `"$AcrName`" --image `"resource-b:$Tag`" `"$srcRoot\resource-b`""
Invoke-Echo "az acr build --registry `"$AcrName`" --image `"upstream-api:$Tag`" `"$srcRoot\upstream-api`""

Invoke-Echo "az deployment sub create --location `"$Location`" --template-file `"$PSScriptRoot\main.bicep`" --parameters `"$PSScriptRoot\main.bicepparam`" resourceGroupName=`"$ResourceGroupName`" location=`"$Location`" namePrefix=`"$NamePrefix`" acrName=`"$AcrName`" keyVaultName=`"$KeyVaultName`" deployContainerApps=true mcpServerImage=`"$mcpImage`" resourceBImage=`"$bImage`" upstreamApiImage=`"$upstreamImage`""
