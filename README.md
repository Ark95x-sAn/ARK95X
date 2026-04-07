# ARK95X NEUROLINK

**Intelligence Gathering System - Multi-Agent Orchestration Platform**

Dual-PC AI orchestration system running 6 browser agents across two Windows 11 machines connected via Tailscale mesh VPN and SMB shared storage.

## Architecture

```
AMARA (MagAce 2080)           ARCX (GM700 / RTX 5070 Ti)
+-------------------+         +-------------------+
| Browser Agents    |         | Ollama (llama3.1) |
| Comet, ChatGPT    |  TCP    | comet_router.py   |
| Gemini, BlackBox  |<------->| n8n orchestrator  |
| Mistral, Groq     |  VPN    | Watchdog monitor  |
+-------------------+         +-------------------+
        |                              |
        +------ Z:\ SMB Share ---------+
                ARK95X_SHARED
```

## Hardware

| Node | Machine | GPU | Role |
|------|---------|-----|------|
| AMARA | MagAce 2080 | RTX 2080 | Browser Agent Hub / Operator Console |
| ARCX | GM700 | RTX 5070 Ti | AI Inference Server / Orchestration |

## Network Stack

| Layer | Protocol | Port |
|-------|----------|------|
| L0 Physical | MWB 15100 | 15100 |
| L1 VPN | Tailscale Mesh | - |
| L3 Transport | TCP | 445, 8000, 11434, 5678 |
| L5 Application | SMB/Ollama/FastAPI/n8n | - |
| L7 Mission Control | Dashboards/SOPs | - |

## Quick Deploy

**ARCX first (server):**
```powershell
irm https://raw.githubusercontent.com/Ark95x-sAn/ARK95X/main/scripts/ark95x_bootstrap_arcx.ps1 | iex
```

**AMARA second (client):**
```powershell
irm https://raw.githubusercontent.com/Ark95x-sAn/ARK95X/main/scripts/ark95x_bootstrap_amara.ps1 | iex
```

**Validate both:**
```powershell
C:\ARK95X\repo\scripts\ark95x_validate.ps1
```

## Repository Structure

```
ARK95X/
  agents/
    ark95x_agent_orchestrator.py   # 6-agent dual-IT team with passback
    agent_config.json              # Agent definitions + error patterns
    agent_passback.py              # Self-learning recovery engine
  docs/
    dashboard.md                   # System overview + health monitoring
    deployment.md                  # Step-by-step deployment guide
    cosmic_reading.md              # Mission alignment (Aug 11 1993)
  scripts/
    ark95x_bootstrap_amara.ps1     # 12-phase AMARA installer
    ark95x_bootstrap_arcx.ps1      # 15-phase ARCX installer
    ark95x_validate.ps1            # Full stack validation
    ark95x_scale.ps1               # Dual-node health + load balancer
  services/
    comet_router.py                # FastAPI broker (AMARA <> Ollama)
  workflows/
    n8n_ark95x_orchestrator.json   # 8-node n8n pipeline
  staging/                         # Agent passback staging area
  production/                      # Approved code from passback
  logs/                            # System logs
  outbox/                          # Agent output
```

## Agent Roster

| Callsign | Agent | Node | Role |
|----------|-------|------|------|
| ALPHA-1 | Comet/Perplexity | AMARA | Commander / Primary Orchestrator |
| BRAVO-2 | xAI/Grok | AMARA | Intelligence & Analysis |
| CHARLIE-3 | Gemini Pro | ARCX | Google Workspace / Visuals |
| DELTA-4 | ChatGPT Pro | ARCX | Protocol Design / Code Gen |
| ECHO-5 | BlackBox AI | AMARA | Code Generation / Research |
| FOXTROT-6 | Mistral/Groq | ARCX | Fast Inference |

## Key Services

- **comet_router.py** - FastAPI proxy on port 8000, routes AMARA browser requests to Ollama on ARCX
- **n8n orchestrator** - 8-node workflow with webhook triggers, health checks, task dispatch
- **Watchdog** - Auto-restart on service failure, disk/memory/GPU alerts
- **Agent Passback** - Self-learning error recovery with pattern matching and confidence scoring

## Passback Protocol

Async file-system state machine for agent code review:
1. Agent-A writes code + meta.json to `Z:\ARK95X_SHARED\staging\`
2. n8n watches staging folder, triggers Agent-B review
3. Agent-B outputs approved/rejected JSON
4. n8n routes: approved -> production, rejected -> feedback loop
5. Audit trail in filesystem, observable, crash-recoverable

## Validation

After deployment, verify all 4 checks:
```
ping ARCX_IP
curl http://ARCX_IP:8000/health
curl http://ARCX_IP:11434/api/tags
dir Z:\ARK95X_SHARED\
```
All 4 GREEN = **NEUROLINK ACTIVE**

## Status

- **GitHub Repo:** 16 files deployed
- **Google Drive:** 5 documents (dashboard, deployment, cosmic, scripts, task list)
- **Points:** 100 | Tasks: 25 complete
- **Status:** AWAITING HARDWARE DEPLOYMENT

---
*ALPHA-1 ACTUAL // BLACK OPS COMET-01*


## Quick Start - Docker Deployment

### Prerequisites
- Docker & Docker Compose v2+
- NVIDIA GPU with drivers (for Ollama)
- Git

### Clone & Deploy
```bash
git clone https://github.com/Ark95x-sAn/ARK95X.git
cd ARK95X
cp .env.example .env
# Edit .env with your settings
docker compose up -d
```

### Services
| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 8501 | Streamlit 6-panel UI |
| Ollama | 11434 | Local LLM server |
| n8n | 5678 | Workflow automation |
| Toast Audit | - | POS sales audit engine |
| Watchdog | - | System health monitor |
| Benchmark | - | Model performance tester |

### Pull Ollama Models
```bash
docker exec ark95x-ollama ollama pull gemma4
docker exec ark95x-ollama ollama pull llama3
docker exec ark95x-ollama ollama pull mistral
```

### Run Benchmark (optional)
```bash
docker compose --profile benchmark up benchmark
```

### Toast POS Audit
Export CSVs from Toast Back Office > Reporting, place in `data/toast/`, then:
```bash
python services/toast_audit.py --csv data/toast/sales.csv data/toast/voids.csv data/toast/comps.csv
```

### n8n Workflows
Import `workflows/toast_monitor.json` into n8n at http://localhost:5678 for automated 6-hour Toast monitoring with webhook alerts.

## Project Structure
```
ARK95X/
├── agents/           # AI agent configs
├── dashboard/        # Streamlit dashboard
├── scripts/          # Benchmark & utility scripts
├── services/         # Core services (audit, watchdog, router)
├── workflows/        # n8n workflow definitions
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```
