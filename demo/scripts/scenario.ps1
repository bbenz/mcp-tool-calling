<#
.SYNOPSIS
  Run one named scenario and print its protocol trace.
.EXAMPLE
  .\scripts\scenario.ps1 wrong-audience
  .\scripts\scenario.ps1 -All       # every scenario, in stage order
  .\scripts\scenario.ps1            # lists the available scenarios
#>
[CmdletBinding()]
param([Parameter(Position = 0)][string]$Name, [switch]$All)

$demo = Split-Path -Parent $PSScriptRoot
$py = Join-Path $demo '.venv\Scripts\python.exe'
Push-Location $demo
try {
    if ($All) { & $py -m refund_demo.scenarios run-all }
    elseif (-not $Name) { & $py -m refund_demo.scenarios list }
    else { & $py -m refund_demo.scenarios run $Name }
} finally { Pop-Location }
