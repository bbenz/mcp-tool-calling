<#
.SYNOPSIS
  Serve the web front end against the locally running services.
.DESCRIPTION
  Optional. The four services must already be up (start-all.ps1); this only
  adds a browser view over them, and it makes no authorization decision of its
  own -- every verdict it renders came from the MCP server.

  Runs in the foreground. Ctrl+C stops it. Nothing else about the demo changes.
.PARAMETER Port
  Port to listen on.
.PARAMETER AllowReset
  Expose the reset button. Off by default, and still refused in entra mode.
.EXAMPLE
  .\scripts\web.ps1
#>
[CmdletBinding()]
param(
    [int]$Port = 8080,
    [switch]$AllowReset
)

$demo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $demo '.venv\Scripts\python.exe'

if (-not (Test-Path $py)) {
    Write-Error "venv missing - run .\scripts\bootstrap.ps1 first"
    exit 1
}

$env:WEB_PORT = $Port
if ($AllowReset) { $env:WEB_ALLOW_RESET = '1' }

Write-Host "web UI  http://localhost:$Port" -ForegroundColor Green
Write-Host "Ctrl+C to stop." -ForegroundColor DarkGray

Push-Location $demo
try {
    & $py -m refund_demo.web.app
    exit $LASTEXITCODE
} finally { Pop-Location }
