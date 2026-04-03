# ============================================
# ARK95X NEUROLINK // WATCHDOG MONITOR
# Deploy on ARCX: Runs as scheduled task
# Monitors: Ollama, Comet Router, n8n
# Alerts: Disk, Memory, GPU Temperature
# ============================================

param(
  [int]$IntervalSeconds = 60,
  [string]$LogDir = "C:\ARK95X\logs",
  [string]$ReportDir = "C:\ARK95X\reports",
  [string]$CometRouterPort = "8000",
  [string]$OllamaPort = "11434",
  [string]$N8nPort = "5678",
  [int]$DiskThreshold = 90,
  [int]$MemoryThreshold = 92,
  [int]$GpuTempThreshold = 85,
  [switch]$SingleRun
)

$ErrorActionPreference = "Continue"

# === LOGGING ===
function Write-Log {
  param([string]$Message, [string]$Level = "INFO")
  $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
  $line = "[$ts] [$Level] $Message"
  Write-Host $line
  $logFile = Join-Path $LogDir "watchdog.log"
  if (!(Test-Path $LogDir)) { New-Item -Path $LogDir -ItemType Directory -Force | Out-Null }
  $line | Out-File -FilePath $logFile -Append -Encoding utf8
}

function Write-Alert {
  param([string]$Message)
  Write-Log $Message "ALERT"
  $alertFile = Join-Path $ReportDir "alerts.log"
  if (!(Test-Path $ReportDir)) { New-Item -Path $ReportDir -ItemType Directory -Force | Out-Null }
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | $Message" | Out-File -FilePath $alertFile -Append -Encoding utf8
}

# === SERVICE CHECKS ===
function Test-TcpService {
  param([string]$Name, [string]$Host = "127.0.0.1", [int]$Port)
  try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($Host, $Port)
    $tcp.Close()
    return @{ Name = $Name; Status = "GREEN"; Port = $Port }
  } catch {
    return @{ Name = $Name; Status = "RED"; Port = $Port }
  }
}

function Test-HttpEndpoint {
  param([string]$Name, [string]$Url)
  try {
    $resp = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    if ($resp.StatusCode -eq 200) {
      return @{ Name = $Name; Status = "GREEN"; Url = $Url }
    }
    return @{ Name = $Name; Status = "YELLOW"; Url = $Url }
  } catch {
    return @{ Name = $Name; Status = "RED"; Url = $Url }
  }
}

# === RESOURCE CHECKS ===
function Get-DiskUsage {
  $disk = Get-PSDrive C
  $usedPct = [math]::Round(($disk.Used / ($disk.Used + $disk.Free)) * 100, 1)
  return @{ UsedPct = $usedPct; FreeGB = [math]::Round($disk.Free / 1GB, 1) }
}

function Get-MemoryUsage {
  $os = Get-CimInstance Win32_OperatingSystem
  $usedPct = [math]::Round((($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / $os.TotalVisibleMemorySize) * 100, 1)
  return @{ UsedPct = $usedPct; TotalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1) }
}

function Get-GpuTemp {
  try {
    $gpu = & nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>$null
    if ($gpu) { return [int]$gpu.Trim() }
  } catch {}
  return -1
}

# === AUTO-RESTART ===
function Restart-Service-If-Down {
  param([string]$Name, [string]$Status, [string]$TaskName)
  if ($Status -eq "RED") {
    Write-Alert "$Name is DOWN - attempting restart via scheduled task: $TaskName"
    try {
      Start-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 5
      Write-Log "$Name restart triggered via $TaskName"
    } catch {
      Write-Alert "FAILED to restart $Name - manual intervention required"
    }
  }
}

# === HEALTH REPORT ===
function Write-HealthReport {
  param($Services, $Disk, $Memory, $GpuTemp)
  if (!(Test-Path $ReportDir)) { New-Item -Path $ReportDir -ItemType Directory -Force | Out-Null }
  $reportFile = Join-Path $ReportDir "health_$(Get-Date -Format 'yyyyMMdd_HHmmss').json"
  $report = @{
    timestamp = (Get-Date).ToString("o")
    hostname = $env:COMPUTERNAME
    services = $Services
    disk = $Disk
    memory = $Memory
    gpu_temp_c = $GpuTemp
    overall = if ($Services | Where-Object { $_.Status -eq "RED" }) { "DEGRADED" } else { "HEALTHY" }
  }
  $report | ConvertTo-Json -Depth 3 | Out-File -FilePath $reportFile -Encoding utf8
  Write-Log "Health report saved: $reportFile"
}

# === MAIN LOOP ===
function Invoke-WatchdogCycle {
  Write-Log "=== WATCHDOG CYCLE START ==="

  # Service checks
  $svcOllama = Test-TcpService -Name "Ollama" -Port $OllamaPort
  $svcComet = Test-TcpService -Name "CometRouter" -Port $CometRouterPort
  $svcN8n = Test-TcpService -Name "n8n" -Port $N8nPort

  # HTTP endpoint checks
  $httpHealth = Test-HttpEndpoint -Name "CometHealth" -Url "http://127.0.0.1:${CometRouterPort}/health"
  $httpOllama = Test-HttpEndpoint -Name "OllamaAPI" -Url "http://127.0.0.1:${OllamaPort}/api/tags"

  $allServices = @($svcOllama, $svcComet, $svcN8n, $httpHealth, $httpOllama)

  foreach ($svc in $allServices) {
    $icon = if ($svc.Status -eq "GREEN") { "[OK]" } elseif ($svc.Status -eq "YELLOW") { "[WARN]" } else { "[FAIL]" }
    Write-Log "$icon $($svc.Name): $($svc.Status)"
  }

  # Auto-restart downed services
  Restart-Service-If-Down -Name "CometRouter" -Status $svcComet.Status -TaskName "ARK95X-comet_router"
  Restart-Service-If-Down -Name "n8n" -Status $svcN8n.Status -TaskName "ARK95X-n8n"

  # Resource checks
  $disk = Get-DiskUsage
  $memory = Get-MemoryUsage
  $gpuTemp = Get-GpuTemp

  Write-Log "Disk: $($disk.UsedPct)% used ($($disk.FreeGB) GB free)"
  Write-Log "Memory: $($memory.UsedPct)% used ($($memory.TotalGB) GB total)"
  if ($gpuTemp -ge 0) { Write-Log "GPU Temp: ${gpuTemp}C" }

  # Threshold alerts
  if ($disk.UsedPct -ge $DiskThreshold) {
    Write-Alert "DISK CRITICAL: $($disk.UsedPct)% used - threshold ${DiskThreshold}%"
  }
  if ($memory.UsedPct -ge $MemoryThreshold) {
    Write-Alert "MEMORY CRITICAL: $($memory.UsedPct)% used - threshold ${MemoryThreshold}%"
  }
  if ($gpuTemp -ge $GpuTempThreshold) {
    Write-Alert "GPU TEMP CRITICAL: ${gpuTemp}C - threshold ${GpuTempThreshold}C"
  }

  # Generate health report
  Write-HealthReport -Services $allServices -Disk $disk -Memory $memory -GpuTemp $gpuTemp

  Write-Log "=== WATCHDOG CYCLE END ==="
}

# === ENTRY POINT ===
Write-Log "ARK95X Watchdog starting - interval ${IntervalSeconds}s"
Write-Log "Monitoring: Ollama:${OllamaPort}, CometRouter:${CometRouterPort}, n8n:${N8nPort}"

if ($SingleRun) {
  Invoke-WatchdogCycle
} else {
  while ($true) {
    Invoke-WatchdogCycle
    Start-Sleep -Seconds $IntervalSeconds
  }
}
