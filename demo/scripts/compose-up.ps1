<#
.SYNOPSIS
  Start the whole demo in Docker containers.
.DESCRIPTION
  Optional path. The script-based demo (start-all.ps1) is unchanged and is
  still the rehearsed stage path; this is for handing the demo to someone who
  has Docker and nothing else, and for testing the topology that the AKS
  manifests deploy.

  Builds the image, brings up five containers, and waits for the web container
  to report healthy before printing the URL.
.PARAMETER NoBuild
  Reuse the existing refund-demo:local image instead of rebuilding.
.PARAMETER TimeoutSeconds
  How long to wait for all containers to become healthy.
.EXAMPLE
  .\scripts\compose-up.ps1
.EXAMPLE
  .\scripts\compose-up.ps1 -NoBuild
#>
[CmdletBinding()]
param(
    [switch]$NoBuild,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
$demo = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $demo 'docker\docker-compose.yml'

Push-Location $demo
try {
    docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker Compose not available. Install Docker Desktop and make sure it is running."
    }

    if (-not $NoBuild) {
        Write-Host "Building refund-demo:local ..." -ForegroundColor Cyan
        docker compose -f $compose build
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Build failed. If the failure is a TLS or connection error against" -ForegroundColor Yellow
            Write-Host "files.pythonhosted.org, this network blocks the PyPI wheel CDN." -ForegroundColor Yellow
            Write-Host "See docs/DEPLOYMENT.md, 'When the image build cannot reach PyPI'." -ForegroundColor Yellow
            exit 1
        }
    }

    Write-Host "Starting containers ..." -ForegroundColor Cyan
    docker compose -f $compose up -d
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    # Compose returns as soon as the containers are created; healthchecks are
    # what actually tell us the services are answering.
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $expected = 5
    while ((Get-Date) -lt $deadline) {
        $ids = docker compose -f $compose ps -q
        $healthy = 0
        foreach ($id in $ids) {
            if (-not $id) { continue }
            $state = docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $id 2>$null
            if ($state -eq 'healthy') { $healthy++ }
        }
        if ($healthy -ge $expected) {
            Write-Host ""
            Write-Host "All $expected containers healthy." -ForegroundColor Green
            Write-Host "  Web UI    http://localhost:8080"
            Write-Host "  devidp    http://localhost:8800/.well-known/openid-configuration"
            Write-Host "  MCP A     http://localhost:8801/.well-known/oauth-protected-resource"
            Write-Host "  MCP B     http://localhost:8802/.well-known/oauth-protected-resource"
            Write-Host ""
            Write-Host "Stop with: .\scripts\compose-down.ps1"
            exit 0
        }
        Start-Sleep -Seconds 3
    }

    Write-Host "Timed out waiting for containers to become healthy." -ForegroundColor Red
    docker compose -f $compose ps
    Write-Host "Logs: docker compose -f docker/docker-compose.yml logs"
    exit 1
}
finally { Pop-Location }
