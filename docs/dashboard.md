# ARK95X NEUROLINK Status Dashboard

## System Overview
- **Architecture**: Dual-PC (AMARA client + ARCX server)
- **Network**: Tailscale mesh VPN
- **AI Engine**: Ollama (llama3.1 + nomic-embed-text) on ARCX
- **Router**: FastAPI comet_router.py on ARCX:8000
- **Orchestration**: n8n workflow on ARCX:5678

## Agent Team
| Agent | Platform | Node | Role |
|-------|----------|------|------|
| COMET-01 | Comet Browser | AMARA | Primary Orchestrator |
| ChatGPT-Pro | OpenAI | AMARA | Code Generation |
| Gemini-Pro | Google | AMARA | Analysis/SIM |
| BlackBox | BlackBox AI | ARCX | Code Review |
| Mistral | Mistral AI | ARCX | Documentation |
| CodeLlama | Ollama Local | ARCX | Local Inference |

## Health Monitoring
- Ollama TCP check: port 11434
- Comet Router: port 8000 /health
- n8n: port 5678
- SMB Share: Z:\ mount validation
- Auto-restart on service failure
- Alerts: Disk >90%, Memory >92%, GPU temp >85C

## Passback Protocol
1. Agent-A writes code + meta.json to Z:\ARK95X_SHARED\staging\
2. n8n watches staging folder, triggers Agent-B review
3. Agent-B outputs approved/rejected JSON
4. n8n routes: approved -> production, rejected -> feedback loop

## Status: GREEN // ALL SYSTEMS OPERATIONAL

---
*ALPHA-1 ACTUAL // ARK95X NEUROLINK*
