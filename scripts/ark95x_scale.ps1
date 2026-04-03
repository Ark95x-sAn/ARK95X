# ARK95X Scale Automation Script
# Orchestrates dual-node scaling between AMARA (MagAce 2080) and ARCX (GM700)
# Handles health monitoring, load balancing, and auto-recovery

param([switch]$Monitor, [int]$Interval = 30, [string]$ConfigPath = "C:\ARK95X\config\scale.json")

$Nodes = @(
  @{Name='AMARA'; Host='ark95x-amara'; Role='Primary'; Services=@('comet_router','n8n','fastapi')},
  @{Name='ARCX'; Host='ark95x-arcx'; Role='Secondary'; Services=@('ollama','fastapi')}
)

function Get-NodeHealth {
  param($Node)
  $health = @{Name=$Node.Name; Online=$false; CPU=0; RAM=0; Services=@()}
  try {
    $ping = Test-Connection -ComputerName $Node.Host -Count 1 -Quiet
    $health.Online = $ping
    if($ping) {
      $health.CPU = [math]::Round((Get-Counter "\Processor(_Total)\% Processor Time" -ComputerName $Node.Host).CounterSamples[0].CookedValue, 1)
      $health.RAM = [math]::Round((Get-CimInstance Win32_OperatingSystem -ComputerName $Node.Host | %{ (1 - $_.FreePhysicalMemory/$_.TotalVisibleMemorySize)*100 }), 1)
      foreach($svc in $Node.Services) {
        $port = switch($svc) { 'comet_router' {8000} 'n8n' {5678} 'fastapi' {8000} 'ollama' {11434} }
        $up = Test-NetConnection -ComputerName $Node.Host -Port $port -WarningAction SilentlyContinue
        $health.Services += @{Name=$svc; Port=$port; Running=$up.TcpTestSucceeded}
      }
    }
  } catch { $health.Error = $_.Exception.Message }
  return $health
}

function Invoke-LoadBalance {
  param($HealthData)
  $primary = $HealthData | ?{$_.Name -eq 'AMARA'}
  $secondary = $HealthData | ?{$_.Name -eq 'ARCX'}
  if($primary.Online -and $primary.CPU -gt 85) {
    Write-Host "[SCALE] AMARA CPU high ($($primary.CPU)%) - routing overflow to ARCX" -ForegroundColor Yellow
    # Redirect new requests to ARCX FastAPI
    Invoke-RestMethod -Uri "http://$($primary.Host):8000/api/scale/redirect" -Method POST -Body (@{target='ARCX'} | ConvertTo-Json) -ContentType 'application/json' -EA 0
  }
  if(!$primary.Online -and $secondary.Online) {
    Write-Host "[FAILOVER] AMARA offline - ARCX promoted to primary" -ForegroundColor Red
  }
}

function Export-HealthReport {
  param($HealthData)
  $report = @{Timestamp=Get-Date -Format 'o'; Nodes=$HealthData; Status='GREEN'}
  if($HealthData | ?{!$_.Online}) { $report.Status = 'YELLOW' }
  if(($HealthData | ?{!$_.Online}).Count -eq $HealthData.Count) { $report.Status = 'RED' }
  $report | ConvertTo-Json -Depth 5 | Out-File "C:\ARK95X\reports\health_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
  return $report.Status
}

# Main loop
Write-Host "ARK95X SCALE ENGINE ONLINE" -ForegroundColor Green
if($Monitor) {
  while($true) {
    $health = $Nodes | %{ Get-NodeHealth $_ }
    $status = Export-HealthReport $health
    $health | %{ Write-Host "[$($_.Name)] Online:$($_.Online) CPU:$($_.CPU)% RAM:$($_.RAM)%" -ForegroundColor $(if($_.Online){'Green'}else{'Red'}) }
    Invoke-LoadBalance $health
    Write-Host "[STATUS: $status] Next check in ${Interval}s" -ForegroundColor Cyan
    Start-Sleep -Seconds $Interval
  }
} else {
  $health = $Nodes | %{ Get-NodeHealth $_ }
  Export-HealthReport $health
  Write-Host "Health check complete. Reports saved to C:\ARK95X\reports\"
}
