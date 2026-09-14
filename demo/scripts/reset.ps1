<#
.SYNOPSIS
  Reset the ledger and the audit log to a known state.
.DESCRIPTION
  Operator-only. Scoped to the demo data directory, and refuses to run when
  AUTH_MODE=entra unless ALLOW_RESET=1 is set. Never exposed as an MCP tool.

  The local signing key is preserved, so this is safe to run between segments
  with the services still up. Pass -NewKey to rotate it; that is refused while
  devidp is listening, because running services would keep serving the old JWKS.
#>
[CmdletBinding()]
param([switch]$NewKey)

$demo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $demo '.venv\Scripts\python.exe'

Push-Location $demo
try {
    if ($NewKey) { & $py -m refund_demo.reset --new-key } else { & $py -m refund_demo.reset }
    exit $LASTEXITCODE
} finally { Pop-Location }
