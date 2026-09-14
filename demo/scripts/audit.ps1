<#
.SYNOPSIS
  Show the most recent audit records, formatted for a projector.
.EXAMPLE
  .\scripts\audit.ps1 -Last 3
#>
[CmdletBinding()]
param([int]$Last = 5, [switch]$Raw)

$demo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $demo '.venv\Scripts\python.exe'
Push-Location $demo
try {
    if ($Raw) { & $py -c "import json;from refund_demo import audit;[print(json.dumps(r,indent=2)) for r in audit.read_all($Last)]" }
    else { & $py -m refund_demo.audit_view --last $Last }
} finally { Pop-Location }
