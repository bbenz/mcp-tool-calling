<#
.SYNOPSIS
  Start all four demo services and wait until every one answers /health.
.DESCRIPTION
  Short command, no arguments to type on stage. Windows uses this; the cloud
  path uses Container Apps and does not need it.
#>
[CmdletBinding()]
param([switch]$Reset)

$ErrorActionPreference = 'Stop'
$demo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $demo '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "venv missing - run scripts\bootstrap.ps1 first" }

if ($Reset) { & (Join-Path $PSScriptRoot 'reset.ps1') }

$services = @(
    @{ Name = 'devidp';   Module = 'refund_demo.devidp.server';   Port = 8800 },
    @{ Name = 'upstream'; Module = 'refund_demo.upstream_api.app'; Port = 8803 },
    @{ Name = 'mcp-a';    Module = 'refund_demo.mcp_server.app';   Port = 8801 },
    @{ Name = 'mcp-b';    Module = 'refund_demo.resource_b.app';   Port = 8802 }
)

$logDir = Join-Path $demo '.local\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$pidFile = Join-Path $demo '.local\services.json'
$started = @()

foreach ($s in $services) {
    $proc = Start-Process -FilePath $py -ArgumentList @('-m', $s.Module) `
        -WorkingDirectory $demo -PassThru -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDir "$($s.Name).out.log") `
        -RedirectStandardError  (Join-Path $logDir "$($s.Name).err.log")
    $started += [pscustomobject]@{ name = $s.Name; port = $s.Port; pid = $proc.Id }
    Write-Host ("starting {0,-9} pid {1}" -f $s.Name, $proc.Id)
}
$started | ConvertTo-Json | Set-Content -Path $pidFile -Encoding utf8

$deadline = (Get-Date).AddSeconds(45)
foreach ($s in $services) {
    $ok = $false
    while (-not $ok -and (Get-Date) -lt $deadline) {
        try {
            Invoke-RestMethod "http://localhost:$($s.Port)/health" -TimeoutSec 2 | Out-Null
            $ok = $true
        } catch { Start-Sleep -Milliseconds 400 }
    }
    if ($ok) { Write-Host "  healthy  $($s.Name)  http://localhost:$($s.Port)" -ForegroundColor Green }
    else {
        Write-Host "  FAILED   $($s.Name) - see $logDir\$($s.Name).err.log" -ForegroundColor Red
        exit 1
    }
}
Write-Host "`nall services healthy" -ForegroundColor Green
