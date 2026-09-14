<#
.SYNOPSIS
  Run every check: unit tests, end-to-end tests, and all stage scenarios.
.DESCRIPTION
  This is the pre-flight command. Run it the morning of the talk and again
  before walking on stage. Non-zero exit means do not present.
#>
[CmdletBinding()]
param([switch]$SkipTests)

$ErrorActionPreference = 'Stop'
$demo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $demo '.venv\Scripts\python.exe'
Push-Location $demo
try {
    & (Join-Path $PSScriptRoot 'health.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'services are not healthy' }

    if (-not $SkipTests) {
        Write-Host "`n== test suite ==" -ForegroundColor Cyan
        & $py -m pytest tests/ -q
        if ($LASTEXITCODE -ne 0) { throw 'tests failed' }
    }

    Write-Host "`n== stage scenarios ==" -ForegroundColor Cyan
    & $py -m refund_demo.scenarios run-all
    if ($LASTEXITCODE -ne 0) { throw 'scenarios failed' }

    Write-Host "`nREADY" -ForegroundColor Green
} finally { Pop-Location }
