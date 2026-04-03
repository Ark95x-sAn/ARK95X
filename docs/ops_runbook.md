# ARK95X NEUROLINK - Operations Runbook

Quick reference for common operations and troubleshooting.

## Daily Operations

### Check System Health
```powershell
# Run watchdog single check
C:\ARK95X\services\ark95x_watchdog.ps1 -SingleRun

# Check latest health report
Get-Content (Get-ChildItem C:\ARK95X\reports\health_*.json | Sort-Object -Descending | Select-Object -First 1)

# Check alerts
Get-Content C:\ARK95X\reports\alerts.log -Tail 20
```

### Check Service Status
```powershell
# Ollama
curl http://127.0.0.1:11434/api/tags

# Comet Router
curl http://127.0.0.1:8000/health

# n8n
curl http://127.0.0.1:5678/healthz
```

### Pull Latest Code
```powershell
cd C:\ARK95X\repo
git pull origin main
```

## Troubleshooting

### Ollama Not Responding
```powershell
# Check if process is running
Get-Process ollama -ErrorAction SilentlyContinue

# Restart Ollama
taskkill /f /im ollama.exe 2>$null
Start-Sleep 2
ollama serve &

# Verify models available
ollama list

# Re-pull model if missing
ollama pull llama3.1
```

### Comet Router Down
```powershell
# Check if running
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*comet_router*" }

# Restart manually
cd C:\ARK95X\services
python comet_router.py

# Or trigger scheduled task
Start-ScheduledTask -TaskName "ARK95X-comet_router"

# Check logs
Get-Content C:\ARK95X_SHARED\logs\router.log -Tail 30
```

### n8n Not Running
```powershell
# Check process
Get-Process node -ErrorAction SilentlyContinue

# Restart
Start-ScheduledTask -TaskName "ARK95X-n8n"

# Or manually
npx n8n start --tunnel
```

### SMB Share Not Accessible
```powershell
# From AMARA - test connection
Test-Path Z:\

# If drive not mapped
net use Z: \\ARCX_IP\ARK95X_SHARED /persistent:yes

# From ARCX - check share exists
Get-SmbShare | Where-Object Name -eq "ARK95X_SHARED"

# Recreate share if needed
New-SmbShare -Name "ARK95X_SHARED" -Path "C:\ARK95X_SHARED" -FullAccess "Everyone"
```

### Tailscale Connection Lost
```powershell
# Check status
tailscale status

# Reconnect
tailscale up

# Get IP addresses
tailscale ip
```

### GPU Issues
```powershell
# Check GPU status
nvidia-smi

# Check temperature
nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader

# Check memory usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader

# If GPU memory full - restart Ollama
taskkill /f /im ollama.exe
Start-Sleep 5
ollama serve &
```

### Disk Space Low
```powershell
# Check disk usage
Get-PSDrive C | Select-Object Used, Free

# Clean temp files
Remove-Item C:\ARK95X\tmp\* -Recurse -Force

# Clean old health reports (keep last 100)
Get-ChildItem C:\ARK95X\reports\health_*.json | Sort-Object CreationTime | Select-Object -SkipLast 100 | Remove-Item

# Clean old logs (keep last 50MB)
# Manual review recommended before deletion
```

### Agent Passback Stuck
```powershell
# Check staging folder
Get-ChildItem Z:\ARK95X_SHARED\staging\

# Check for rejected items
Get-ChildItem Z:\ARK95X_SHARED\staging\*rejected*

# Move stuck items back for retry
Move-Item Z:\ARK95X_SHARED\staging\*.rejected Z:\ARK95X_SHARED\staging\ -Force

# Check production for completed items
Get-ChildItem Z:\ARK95X_SHARED\production\
```

## Emergency Procedures

### Full System Restart (ARCX)
```powershell
# Stop all services
taskkill /f /im ollama.exe 2>$null
taskkill /f /im python.exe 2>$null
taskkill /f /im node.exe 2>$null
Start-Sleep 5

# Restart via scheduled tasks
Start-ScheduledTask -TaskName "ARK95X-comet_router"
Start-ScheduledTask -TaskName "ARK95X-n8n"
Start-ScheduledTask -TaskName "ARK95X-watchdog"
Start-Sleep 10

# Start Ollama
ollama serve &
Start-Sleep 5

# Validate
C:\ARK95X\repo\scripts\ark95x_validate.ps1
```

### Full Redeploy from Scratch
```powershell
# Nuke and reinstall (ARCX)
Remove-Item C:\ARK95X -Recurse -Force
irm https://raw.githubusercontent.com/Ark95x-sAn/ARK95X/main/scripts/ark95x_bootstrap_arcx.ps1 | iex

# Nuke and reinstall (AMARA)
Remove-Item C:\ARK95X -Recurse -Force
net use Z: /delete /yes
irm https://raw.githubusercontent.com/Ark95x-sAn/ARK95X/main/scripts/ark95x_bootstrap_amara.ps1 | iex
```

## Port Reference

| Port | Service | Node |
|------|---------|------|
| 8000 | comet_router.py | ARCX |
| 11434 | Ollama API | ARCX |
| 5678 | n8n | ARCX |
| 445 | SMB Share | ARCX |
| 15100 | MWB (Mouse Without Borders) | Both |

## Environment Variables

| Variable | Value | Node |
|----------|-------|------|
| OLLAMA_HOST | 0.0.0.0:11434 | ARCX |
| ARCX_IP | (Tailscale IP) | AMARA |
| ARK95X_HOME | C:\ARK95X | Both |
| COMET_ROUTER_TOKEN | (set during deploy) | ARCX |

---
*ARK95X NEUROLINK // OPS RUNBOOK v1.0*
