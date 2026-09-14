<#
.SYNOPSIS
  Reset the ledger, the audit log, and the local signing key to a known state.
.DESCRIPTION
  Operator-only. Scoped to DATA_DIR, and refuses to run when AUTH_MODE=entra
  unless ALLOW_RESET=1 is set. Never exposed as an MCP tool.
#>
[CmdletBinding()]
param([switch]$KeepKey)

$demo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $demo '.venv\Scripts\python.exe'

Push-Location $demo
try {
    if ($KeepKey) { & $py -m refund_demo.reset --keep-key } else { & $py -m refund_demo.reset }
    exit $LASTEXITCODE
} finally { Pop-Location }
