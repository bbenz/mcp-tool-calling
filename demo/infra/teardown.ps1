param(
  [Parameter(Mandatory=$true)][string]$ResourceGroupName,
  [string]$DemoTagName = 'mcp-auth-demo',
  [string]$DemoTagValue = 'true',
  [switch]$Confirm
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if (-not $Confirm) {
  Write-Host 'Dry run only. Re-run with -Confirm to delete the tagged demo resource group.'
  exit 0
}

$tag = az group show --name $ResourceGroupName --query "tags.$DemoTagName" -o tsv
if ($LASTEXITCODE -ne 0) { throw "Could not read resource group $ResourceGroupName" }
if ($tag -ne $DemoTagValue) {
  throw "Refusing to delete $ResourceGroupName because tag $DemoTagName=$DemoTagValue was not found."
}

$answer = Read-Host "Type the resource group name '$ResourceGroupName' to confirm deletion"
if ($answer -ne $ResourceGroupName) {
  throw 'Confirmation did not match; aborting.'
}

Write-Host "+ az group delete --name `"$ResourceGroupName`" --yes"
az group delete --name "$ResourceGroupName" --yes
if ($LASTEXITCODE -ne 0) { throw 'Resource group deletion failed.' }
