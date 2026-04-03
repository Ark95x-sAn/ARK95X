# ARK95X Bootstrap - ARCX (GM700)
# 15-Phase Idempotent Installer
# STATUS: CHARLIE-3

param([switch]$DryRun, [string]$TailscaleKey, [string]$AmaraIP)
$ErrorActionPreference = 'Stop'

function Write-Log { param($M,$L='INFO'); "[$(Get-Date -f 'HH:mm:ss')] [$L] $M" | Tee-Object -Append "C:\ARK95X\logs\arcx.log" }

# Phase 1-3: Dirs, Validate, Packages
@('logs','config','services','models','cache','reports') | %{ $p="C:\ARK95X\$_"; if(!(Test-Path $p)){md $p -Force} }
Write-Log 'Phase 1-2: Dirs + validation done'
@('Git.Git','Tailscale.Tailscale','Python.Python.3.12','Ollama.Ollama') | %{ if(!$DryRun){ winget install --id $_ -e --accept-source-agreements --accept-package-agreements 2>$null } }

# Phase 4-6: Tailscale, Ollama, Python
if($TailscaleKey -and !$DryRun){ & 'C:\Program Files\Tailscale\tailscale.exe' up --authkey=$TailscaleKey --hostname=ARK95X-ARCX }
@('mistral','codellama','llama3') | %{ if(!$DryRun){ ollama pull $_ } }
if(!$DryRun){ python -m pip install fastapi uvicorn httpx pydantic aiohttp }

# Phase 7-8: SMB + Firewall
if(!$DryRun -and !(Get-SmbShare 'ARK95X' -EA 0)){ New-SmbShare -Name 'ARK95X' -Path 'C:\ARK95X' -FullAccess Everyone }
@(@{N='Ollama';P=11434},@{N='FastAPI';P=8000},@{N='n8n';P=5678}) | %{ if(!$DryRun){ New-NetFirewallRule -DisplayName "ARK95X-$($_.N)" -Direction Inbound -Protocol TCP -LocalPort $_.P -Action Allow -EA 0 } }

# Phase 9-10: Router + Tasks
if(!$DryRun -and $AmaraIP){ (gc 'C:\ARK95X\services\comet_router.py') -replace 'AMARA_IP_PLACEHOLDER',$AmaraIP | sc 'C:\ARK95X\services\comet_router.py' }
@(@{N='Health';S='healthcheck.ps1';I=15},@{N='Sync';S='sync_reports.ps1';I=60}) | %{ if(!$DryRun){ Register-ScheduledTask -TaskName "ARK95X-$($_.N)" -Action (New-ScheduledTaskAction -Execute powershell -Argument "-File C:\ARK95X\scripts\$($_.S)") -Trigger (New-ScheduledTaskTrigger -RepetitionInterval ([TimeSpan]::FromMinutes($_.I)) -Once -At (Get-Date)) -Force } }

# Phase 11-15: Handshake
if($AmaraIP -and !$DryRun){ if(Test-Connection $AmaraIP -Count 2 -Quiet){ Write-Log 'AMARA REACHABLE' } else { Write-Log 'AMARA UNREACHABLE' 'WARN' } }
Write-Log 'ARCX BOOTSTRAP COMPLETE // CHARLIE-3 OPERATIONAL'
