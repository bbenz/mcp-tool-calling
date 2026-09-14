<#
.SYNOPSIS
  Delete everything aks-up.ps1 created.
.DESCRIPTION
  Deletes the whole resource group, which is the only way to be confident the
  cluster, the registry, the load balancer, the public IP and the managed
  identity all went with it. A demo cluster left running over a conference
  weekend is a real bill.
.PARAMETER ResourceGroup
  The resource group to delete.
.PARAMETER ClusterName
  Cluster name, used only to clean the stale kubeconfig entry afterwards.
.PARAMETER Wait
  Block until the delete finishes instead of returning immediately.
.PARAMETER Yes
  Skip the confirmation prompt.
.EXAMPLE
  .\scripts\aks-down.ps1
#>
[CmdletBinding()]
param(
    [string]$ResourceGroup = 'rg-mcp-refund-demo',
    [string]$ClusterName   = 'aks-mcp-refund-demo',
    [switch]$Wait,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command az -ErrorAction SilentlyContinue)) { throw "az not found on PATH." }

& az group show --name $ResourceGroup -o none 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Resource group '$ResourceGroup' does not exist. Nothing to do."
    exit 0
}

Write-Host ""
Write-Host "  About to delete resource group '$ResourceGroup' and everything in it." -ForegroundColor Yellow
& az resource list --resource-group $ResourceGroup --query "[].{name:name,type:type}" -o table
Write-Host ""

if (-not $Yes) {
    $answer = Read-Host "Type the resource group name to confirm"
    if ($answer -ne $ResourceGroup) { Write-Host "Cancelled."; exit 1 }
}

if ($Wait) {
    az group delete --name $ResourceGroup --yes
} else {
    az group delete --name $ResourceGroup --yes --no-wait
    Write-Host "Delete started. Check with: az group show --name $ResourceGroup" -ForegroundColor Green
}

# The kubeconfig entry outlives the cluster and will otherwise sit there as a
# broken current-context, which is a confusing thing to hit later.
kubectl config delete-context $ClusterName 2>$null | Out-Null
kubectl config delete-cluster $ClusterName 2>$null | Out-Null
exit 0
