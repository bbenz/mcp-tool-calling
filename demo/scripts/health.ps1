<#
.SYNOPSIS
  Report health for every demo service. Run this before walking on stage.
#>
[CmdletBinding()]
param()

$all = $true
foreach ($s in @(
    @{ n = 'devidp';   p = 8800 }, @{ n = 'mcp-a'; p = 8801 },
    @{ n = 'mcp-b';    p = 8802 }, @{ n = 'upstream'; p = 8803 })) {
    try {
        $r = Invoke-RestMethod "http://localhost:$($s.p)/health" -TimeoutSec 3
        Write-Host ("  OK    {0,-9} {1}" -f $s.n, $r.service) -ForegroundColor Green
    } catch {
        Write-Host ("  DOWN  {0,-9} {1}" -f $s.n, $_.Exception.Message) -ForegroundColor Red
        $all = $false
    }
}
if (-not $all) { exit 1 }
