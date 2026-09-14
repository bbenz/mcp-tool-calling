<#
.SYNOPSIS
  Stop the containerised demo.
.DESCRIPTION
  Stops and removes the five containers. The shared state volume is kept by
  default so the ledger survives a restart; pass -Volumes to drop it, which is
  the container equivalent of reset.ps1 -NewKey.
.PARAMETER Volumes
  Also delete the demo-state volume (ledger, audit log, signing key).
.EXAMPLE
  .\scripts\compose-down.ps1
.EXAMPLE
  .\scripts\compose-down.ps1 -Volumes
#>
[CmdletBinding()]
param([switch]$Volumes)

$ErrorActionPreference = 'Stop'
$demo = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $demo 'docker\docker-compose.yml'

Push-Location $demo
try {
    if ($Volumes) {
        Write-Host "Removing containers and the demo-state volume ..." -ForegroundColor Yellow
        docker compose -f $compose down --volumes
    } else {
        docker compose -f $compose down
    }
    exit $LASTEXITCODE
}
finally { Pop-Location }
