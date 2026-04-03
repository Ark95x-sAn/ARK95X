# ARK95X Deployment Guide

## Prerequisites
- Windows 11 on both AMARA (client) and ARCX (server)
- Internet connection for initial setup
- Admin privileges on both machines

## Architecture: Option E - Hybrid (Git + winget + PowerShell)
Git repo as source of truth, winget for idempotent installs, PowerShell for orchestration.

## Step 1: Deploy ARCX Server
```powershell
# Run as Administrator on ARCX machine
irm https://raw.githubusercontent.com/Ark95x-sAn/ARK95X/main/scripts/ark95x_bootstrap_arcx.ps1 | iex
```
15-phase installer: dirs, Git, Tailscale, Ollama, Python, NodeJS, n8n, SMB share, firewall, scheduled tasks, validation.

## Step 2: Deploy AMARA Client
```powershell
# Run as Administrator on AMARA machine
irm https://raw.githubusercontent.com/Ark95x-sAn/ARK95X/main/scripts/ark95x_bootstrap_amara.ps1 | iex
```
12-phase installer: dirs, Git, Tailscale, Python, Obsidian, SMB mapping, env vars, scheduled sync.

## Step 3: Validate
```powershell
.\scripts\ark95x_validate.ps1
```
Full stack validation with GREEN/YELLOW/RED status.

## Step 4: Start Services
- comet_router.py runs on ARCX:8000 (scheduled task)
- n8n runs on ARCX:5678 (scheduled task)
- Health monitor via ark95x_scale.ps1

## Network Ports
| Port | Service | Node |
|------|---------|------|
| 8000 | Comet Router (FastAPI) | ARCX |
| 11434 | Ollama API | ARCX |
| 5678 | n8n Workflow | ARCX |
| 445 | SMB Share | ARCX |
| 15100 | Watchdog | ARCX |

## Passback Protocol (Agent Collaboration)
- staging/ folder: Agent-A writes code + meta.json
- n8n monitors staging, triggers review by Agent-B
- production/ folder: Approved code deployed
- Audit trail maintained in filesystem

---
*ARK95X NEUROLINK // DEPLOYMENT PACKAGE*
