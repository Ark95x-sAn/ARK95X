# ====================================================================
# ark95x_validate.ps1
# ARK95X NEUROLINK // FULL STACK VALIDATION
# Run from AMARA after both PCs bootstrapped
# ====================================================================
[CmdletBinding()]
param(
  [string]$ARCX_IP = "100.x.x.2",
  [string]$Token = "REPLACE-WITH-A-LONG-RANDOM-SECRET"
)

function Write-Status($name, $ok) {
  if ($ok) { Write-Host "[GREEN] $name" -ForegroundColor Green }
  else { Write-Host "[RED]   $name" -ForegroundColor Red }
}

Write-Host "============================================================"
Write-Host "ARK95X NEUROLINK // VALIDATION BOARD"
Write-Host "============================================================"
$results = @()

# Port checks
@(@{N="SMB 445";P=445},@{N="Comet Router 8000";P=8000},
  @{N="Ollama 11434";P=11434},@{N="n8n 5678";P=5678},
  @{N="MWB 15100";P=15100}) | ForEach-Object {
  $r = Test-NetConnection -ComputerName $ARCX_IP -Port $_.P -WarningAction SilentlyContinue
  $ok = [bool]$r.TcpTestSucceeded
  Write-Status $_.N $ok
  $results += @{Name=$_.N; OK=$ok}
}

# Health endpoint
try {
  $h = Invoke-RestMethod -Uri "http://${ARCX_IP}:8000/health" -Method GET -TimeoutSec 10
  $ok = $h.status -eq "ok"
  Write-Status "Router /health (ollama_reachable=$($h.ollama_reachable))" $ok
  $results += @{Name="Router Health"; OK=$ok}
} catch {
  Write-Status "Router /health FAILED" $false
  $results += @{Name="Router Health"; OK=$false}
}

# Ollama tags
try {
  $t = Invoke-RestMethod -Uri "http://${ARCX_IP}:11434/api/tags" -Method GET -TimeoutSec 10
  Write-Status "Ollama /api/tags ($($t.models.Count) models)" $true
  $results += @{Name="Ollama Tags"; OK=$true}
} catch {
  Write-Status "Ollama /api/tags FAILED" $false
  $results += @{Name="Ollama Tags"; OK=$false}
}

# SMB test
try {
  $testFile = "Z:\ARK95X_SHARED\logs\validate_$(Get-Date -Format 'yyyyMMdd_HHmmss').tmp"
  "ARK95X VALIDATION TEST" | Out-File $testFile -Force
  Remove-Item $testFile -Force
  Write-Status "SMB read/write" $true
  $results += @{Name="SMB RW"; OK=$true}
} catch {
  Write-Status "SMB read/write FAILED" $false
  $results += @{Name="SMB RW"; OK=$false}
}

# Inference test
try {
  $body = @{model="llama3.1";messages=@(@{role="user";content="Reply OK"});stream=$false} | ConvertTo-Json -Depth 5
  $resp = Invoke-RestMethod -Uri "http://${ARCX_IP}:8000/v1/chat/completions" -Method POST -Body $body -ContentType "application/json" -Headers @{"X-Auth-Token"=$Token} -TimeoutSec 120
  Write-Status "Round-trip inference" $true
  $results += @{Name="Inference"; OK=$true}
} catch {
  Write-Status "Round-trip inference FAILED: $($_.Exception.Message)" $false
  $results += @{Name="Inference"; OK=$false}
}

# Summary
$green = ($results | Where-Object { $_.OK }).Count
$red = ($results | Where-Object { -not $_.OK }).Count
Write-Host ""
Write-Host "============================================================"
if ($red -eq 0) { Write-Host "STATUS: GREEN - ALL SYSTEMS OPERATIONAL" -ForegroundColor Green }
elseif ($green -gt $red) { Write-Host "STATUS: YELLOW - DEGRADED ($red failures)" -ForegroundColor Yellow }
else { Write-Host "STATUS: RED - CRITICAL ($red failures)" -ForegroundColor Red }
Write-Host "============================================================"
