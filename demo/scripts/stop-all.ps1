<#
.SYNOPSIS
  Stop the demo services started by start-all.ps1.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'SilentlyContinue'
$demo = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $demo '.local\services.json'
if (-not (Test-Path $pidFile)) { Write-Host 'no recorded services'; exit 0 }

foreach ($s in (Get-Content $pidFile -Raw | ConvertFrom-Json)) {
    $proc = Get-Process -Id $s.pid -ErrorAction SilentlyContinue
    if ($proc) { Stop-Process -Id $s.pid -Force; Write-Host "stopped $($s.name) (pid $($s.pid))" }
}
Remove-Item $pidFile -Force
