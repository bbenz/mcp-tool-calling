<#
.SYNOPSIS
  Create the virtual environment and install pinned dependencies.
.DESCRIPTION
  Run once per machine. Requires Python 3.10+ already on PATH.
#>
[CmdletBinding()]
param([string]$Python = 'python')

$ErrorActionPreference = 'Stop'
$demo = Split-Path -Parent $PSScriptRoot
Push-Location $demo
try {
    $version = & $Python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
    Write-Host "using Python $version"
    if (-not (Test-Path '.venv')) { & $Python -m venv .venv }
    $py = Join-Path $demo '.venv\Scripts\python.exe'
    & $py -m pip install --quiet --upgrade pip
    & $py -m pip install --quiet -r requirements.txt
    & $py -m pip install --quiet -e .
    if (-not (Test-Path '.env')) {
        Copy-Item '.env.example' '.env'
        Write-Host "created .env from .env.example (AUTH_MODE=devidp needs no further edits)"
    }
    & $py -c "from refund_demo import ledger; ledger.initialize(reset=True); print('ledger ready')"
    Write-Host "`nbootstrap complete - next: .\scripts\start-all.ps1" -ForegroundColor Green
} finally { Pop-Location }
