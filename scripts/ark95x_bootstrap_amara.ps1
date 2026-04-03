# ====================================================================
# ark95x_bootstrap_amara.ps1
# ARK95X NEUROLINK // AMARA BOOTSTRAP
# Role: Browser Agent Hub / Operator Console
# MagAce 2080 | RTX 2080 | Win11 Pro
# ====================================================================
[CmdletBinding()]
param(
  [string]$AMARA_IP = "100.x.x.1",
  [string]$ARCX_IP  = "100.x.x.2",
  [string]$ShareName = "ARK95X_SHARED",
  [string]$DriveLetter = "Z",
  [switch]$SkipPackageInstall
)
$ErrorActionPreference = "Stop"

function Write-Phase($msg) {
  Write-Host ""
  Write-Host "============================================================" -ForegroundColor Cyan
  Write-Host $msg -ForegroundColor Cyan
  Write-Host "============================================================" -ForegroundColor Cyan
}
function Write-Ok($msg) { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Require-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p = New-Object Security.Principal.WindowsPrincipal($id)
  if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as Administrator."
  }
}

function Add-ArkRule {
  param([string]$DisplayName,[string]$Direction,[string]$Protocol,
        [string]$LocalPort="",[string]$RemoteAddress="")
  Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue |
    Remove-NetFirewallRule -ErrorAction SilentlyContinue | Out-Null
  $params = @{ DisplayName=$DisplayName; Direction=$Direction; Action="Allow";
               Profile="Private,Domain"; Enabled="True"; Protocol=$Protocol }
  if ($LocalPort) { $params["LocalPort"] = $LocalPort }
  if ($RemoteAddress) { $params["RemoteAddress"] = $RemoteAddress }
  New-NetFirewallRule @params | Out-Null
  Write-Ok "Firewall rule: $DisplayName"
}

Require-Admin
Write-Phase "ARK95X NEUROLINK // AMARA BOOTSTRAP START"

# --- PACKAGES ---
if (-not $SkipPackageInstall) {
  Write-Phase "PACKAGE INSTALL"
  winget install --id Tailscale.Tailscale --exact --accept-source-agreements --accept-package-agreements --silent
  winget install --id Python.Python.3.12 --exact --accept-source-agreements --accept-package-agreements --silent
  winget install --id Microsoft.PowerToys --exact --accept-source-agreements --accept-package-agreements --silent
}

# --- FOLDERS ---
Write-Phase "FOLDER STRUCTURE"
$root = "C:\ARK95X"
@($root,"$root\bin","$root\config","$root\logs","$root\scripts",
  "$root\temp","$root\inbox","$root\outbox","$root\runbooks") |
  ForEach-Object { if (-not (Test-Path $_)) { New-Item -ItemType Directory -Force -Path $_ | Out-Null }; Write-Ok "Dir: $_" }

# --- FIREWALL ---
Write-Phase "FIREWALL DEPLOYMENT // AMARA"
Add-ArkRule -DisplayName "ARK95X-AMARA-IN-Tailscale-UDP41641" -Direction Inbound -Protocol UDP -LocalPort "41641" -RemoteAddress $ARCX_IP
Add-ArkRule -DisplayName "ARK95X-AMARA-IN-MWB-TCP15100-15101" -Direction Inbound -Protocol TCP -LocalPort "15100-15101" -RemoteAddress $ARCX_IP
Add-ArkRule -DisplayName "ARK95X-AMARA-OUT-AllServices" -Direction Outbound -Protocol TCP -LocalPort "Any" -RemoteAddress $ARCX_IP
Add-ArkRule -DisplayName "ARK95X-AMARA-OUT-Tailscale-UDP" -Direction Outbound -Protocol UDP -LocalPort "Any" -RemoteAddress $ARCX_IP

# --- SMB MAP ---
Write-Phase "MAP SMB SHARE"
$target = "\\$ARCX_IP\$ShareName"
try { cmd /c "net use ${DriveLetter}: /delete /y" 2>$null } catch {}
try {
  cmd /c "net use ${DriveLetter}: $target /persistent:yes"
  Write-Ok "Mapped ${DriveLetter}: to $target"
} catch { Write-Warn "Drive map failed - credentials may be needed" }

# --- CONNECTIVITY ---
Write-Phase "CONNECTIVITY TESTS"
@(@{N="SMB";P=445},@{N="Router";P=8000},@{N="Ollama";P=11434},@{N="n8n";P=5678},@{N="MWB";P=15100}) |
  ForEach-Object {
    $r = Test-NetConnection -ComputerName $ARCX_IP -Port $_.P -WarningAction SilentlyContinue
    if ($r.TcpTestSucceeded) { Write-Ok "$($_.N) port $($_.P) OPEN" }
    else { Write-Warn "$($_.N) port $($_.P) CLOSED" }
  }

Write-Phase "AMARA BOOTSTRAP COMPLETE"
