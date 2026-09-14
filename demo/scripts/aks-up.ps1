<#
.SYNOPSIS
  Deploy the demo to Azure Kubernetes Service.
.DESCRIPTION
  Optional path. The script-based demo is unchanged and is still the rehearsed
  stage path; this exists for a remote audience, for a room with unreliable
  laptop projection, and for the "what would this look like hosted" question.

  Creates a resource group, an Azure Container Registry, and a small AKS
  cluster, builds the image with ACR Tasks, and applies k8s/.

  The image is built by ACR, not locally, so this works from a network that
  blocks the PyPI wheel CDN -- which is exactly the situation that makes
  docker compose build fail. See docs/DEPLOYMENT.md.

  This creates billable Azure resources. It asks first unless -Yes is passed,
  and scripts/aks-down.ps1 removes everything.
.PARAMETER ResourceGroup
  Resource group name. Created if missing.
.PARAMETER Location
  Azure region.
.PARAMETER ClusterName
  AKS cluster name.
.PARAMETER RegistryName
  ACR name. Must be globally unique; derived from the subscription id if unset.
.PARAMETER NodeCount
  Node count. One is enough: the whole demo is a single pod.
.PARAMETER NodeSize
  VM size for the node pool.
.PARAMETER NoAccessKey
  Leave the web UI ungated. Only sensible for a cluster nobody else can reach.
.PARAMETER Yes
  Skip the confirmation prompt.
.EXAMPLE
  .\scripts\aks-up.ps1
.EXAMPLE
  .\scripts\aks-up.ps1 -Location westeurope -Yes
#>
[CmdletBinding()]
param(
    [string]$ResourceGroup = 'rg-mcp-refund-demo',
    [string]$Location      = 'eastus',
    [string]$ClusterName   = 'aks-mcp-refund-demo',
    [string]$RegistryName  = '',
    [int]$NodeCount        = 1,
    [string]$NodeSize      = 'Standard_D2s_v3',
    [switch]$NoAccessKey,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
$demo = Split-Path -Parent $PSScriptRoot

function Invoke-Az {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    $out = & az @Args 2>&1
    if ($LASTEXITCODE -ne 0) {
        $out | ForEach-Object { Write-Host $_ }
        throw "az $($Args -join ' ') failed with exit code $LASTEXITCODE"
    }
    return $out
}

foreach ($tool in 'az', 'kubectl') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool not found on PATH. See docs/DEPLOYMENT.md for prerequisites."
    }
}

$account = & az account show -o json 2>$null | ConvertFrom-Json
if (-not $account) { throw "Not signed in. Run: az login" }
$subId = $account.id

if (-not $RegistryName) {
    # ACR names are globally unique and alphanumeric only. Derive one from the
    # subscription so repeat runs land on the same registry.
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = ($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($subId)) |
             ForEach-Object { $_.ToString('x2') }) -join ''
    $RegistryName = "acrrefunddemo$($hash.Substring(0,8))"
}

$tag = "v$(Get-Date -Format 'yyyyMMddHHmmss')"

Write-Host ""
Write-Host "  subscription   $($account.name)  ($subId)"
Write-Host "  resource group $ResourceGroup"
Write-Host "  location       $Location"
Write-Host "  registry       $RegistryName"
Write-Host "  cluster        $ClusterName  ($NodeCount x $NodeSize)"
Write-Host "  image tag      $tag"
Write-Host ""
Write-Host "  This creates billable Azure resources." -ForegroundColor Yellow
Write-Host "  Remove them with: .\scripts\aks-down.ps1 -ResourceGroup $ResourceGroup" -ForegroundColor Yellow
Write-Host ""

if (-not $Yes) {
    $answer = Read-Host "Continue? (y/N)"
    if ($answer -notmatch '^(y|yes)$') { Write-Host "Cancelled."; exit 1 }
}

Write-Host "[1/6] resource group ..." -ForegroundColor Cyan
Invoke-Az group create --name $ResourceGroup --location $Location --tags purpose=conference-demo data=synthetic -o none

Write-Host "[2/6] container registry ..." -ForegroundColor Cyan
& az acr show --name $RegistryName --resource-group $ResourceGroup -o none 2>$null
$acrExists = ($LASTEXITCODE -eq 0)
if (-not $acrExists) {
    Invoke-Az acr create --name $RegistryName --resource-group $ResourceGroup --sku Basic --location $Location -o none
}

Write-Host "[3/6] building image in ACR (this is where the pip install happens) ..." -ForegroundColor Cyan
# Built server-side on purpose: ACR Tasks can reach PyPI even when the laptop
# cannot, and the build machine matches the cluster architecture.
Invoke-Az acr build --registry $RegistryName --image "refund-demo:$tag" --file docker/Dockerfile $demo -o none

$loginServer = (Invoke-Az acr show --name $RegistryName --resource-group $ResourceGroup --query loginServer -o tsv).Trim()
$image = "$loginServer/refund-demo:$tag"

Write-Host "[4/6] AKS cluster (first run takes several minutes) ..." -ForegroundColor Cyan
& az aks show --name $ClusterName --resource-group $ResourceGroup -o none 2>$null
$aksExists = ($LASTEXITCODE -eq 0)
if (-not $aksExists) {
    Invoke-Az aks create --name $ClusterName --resource-group $ResourceGroup `
        --node-count $NodeCount --node-vm-size $NodeSize `
        --enable-managed-identity --attach-acr $RegistryName `
        --network-plugin azure --network-plugin-mode overlay `
        --tier free --generate-ssh-keys -o none
} else {
    Invoke-Az aks update --name $ClusterName --resource-group $ResourceGroup --attach-acr $RegistryName -o none
}

Invoke-Az aks get-credentials --name $ClusterName --resource-group $ResourceGroup --overwrite-existing -o none

Write-Host "[5/6] applying manifests ..." -ForegroundColor Cyan
kubectl apply -f (Join-Path $demo 'k8s\namespace.yaml')
if ($LASTEXITCODE -ne 0) { throw "kubectl apply failed" }

$accessKey = ''
if (-not $NoAccessKey) {
    # The Service gets a public IP. An unauthenticated page that can move a
    # ledger should not sit on one, even with synthetic data.
    $bytes = [byte[]]::new(24)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    $accessKey = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    kubectl -n refund-demo create secret generic refund-demo-secret `
        --from-literal=web-access-key=$accessKey --dry-run=client -o yaml | kubectl apply -f -
    if ($LASTEXITCODE -ne 0) { throw "creating the access-key secret failed" }
} else {
    kubectl -n refund-demo delete secret refund-demo-secret --ignore-not-found | Out-Null
}

kubectl apply -f (Join-Path $demo 'k8s\configmap.yaml')
if ($LASTEXITCODE -ne 0) { throw "kubectl apply failed" }

(Get-Content (Join-Path $demo 'k8s\deployment.yaml') -Raw).Replace('IMAGE_PLACEHOLDER', $image) |
    kubectl apply -f -
if ($LASTEXITCODE -ne 0) { throw "kubectl apply failed" }

kubectl apply -f (Join-Path $demo 'k8s\service.yaml')
if ($LASTEXITCODE -ne 0) { throw "kubectl apply failed" }

Write-Host "[6/6] waiting for rollout and public address ..." -ForegroundColor Cyan
kubectl -n refund-demo rollout status deploy/refund-demo --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "Rollout did not complete. Inspect with:" -ForegroundColor Red
    Write-Host "  kubectl -n refund-demo get pods"
    Write-Host "  kubectl -n refund-demo describe pod -l app.kubernetes.io/name=refund-demo"
    exit 1
}

$ip = ''
$deadline = (Get-Date).AddMinutes(5)
while (-not $ip -and (Get-Date) -lt $deadline) {
    $ip = (kubectl -n refund-demo get svc refund-demo-web -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null)
    if (-not $ip) { Start-Sleep -Seconds 5 }
}

Write-Host ""
if ($ip) {
    $url = if ($accessKey) { "http://$ip/?k=$accessKey" } else { "http://$ip/" }
    Write-Host "Demo is up." -ForegroundColor Green
    Write-Host "  $url"
    if ($accessKey) {
        Write-Host ""
        Write-Host "  The access key is in that URL. Open it once and bookmark the tab;"
        Write-Host "  the page forwards the key to its own API calls."
    }
} else {
    Write-Host "Deployed, but the load balancer has not been assigned an address yet." -ForegroundColor Yellow
    Write-Host "  kubectl -n refund-demo get svc refund-demo-web -w"
}
Write-Host ""
Write-Host "Tear down with: .\scripts\aks-down.ps1 -ResourceGroup $ResourceGroup"
