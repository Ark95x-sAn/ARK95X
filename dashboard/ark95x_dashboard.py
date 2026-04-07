"""
ARK95X SOVEREIGN COMMAND CENTER - 6-Panel Streamlit Dashboard
Deploy: streamlit run dashboard/ark95x_dashboard.py
Requires: pip install streamlit requests httpx
"""
import streamlit as st
import requests
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# === CONFIG ===
N8N_URL = os.getenv("N8N_URL", "https://ark95x.app.n8n.cloud")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
COMET_ROUTER_URL = os.getenv("COMET_ROUTER_URL", "http://localhost:8000")
GITHUB_REPO = "Ark95x-sAn/ARK95X"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
TOAST_WEBHOOK_LOG = Path(os.getenv("TOAST_LOG", "C:/ARK95X_SHARED/logs/toast_webhook.json"))
REFRESH_INTERVAL = 30  # seconds

# === HEALTH CHECKS ===
def check_service(url, timeout=5):
    try:
        r = requests.get(url, timeout=timeout)
        return "GREEN" if r.status_code == 200 else "YELLOW"
    except:
        return "RED"

def check_n8n():
    if not N8N_API_KEY:
        return "YELLOW", "No API key"
    try:
        r = requests.get(f"{N8N_URL}/api/v1/workflows",
                        headers={"X-N8N-API-KEY": N8N_API_KEY}, timeout=5)
        if r.status_code == 200:
            workflows = r.json().get("data", [])
            active = sum(1 for w in workflows if w.get("active"))
            return "GREEN", f"{active} active workflows"
        return "YELLOW", f"HTTP {r.status_code}"
    except Exception as e:
        return "RED", str(e)[:50]

def check_ollama():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            models = r.json().get("models", [])
            names = [m.get("name", "?") for m in models[:5]]
            return "GREEN", f"{len(models)} models: {', '.join(names)}"
        return "YELLOW", f"HTTP {r.status_code}"
    except:
        return "RED", "Ollama offline"

def check_comet_router():
    try:
        r = requests.get(f"{COMET_ROUTER_URL}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return "GREEN", f"Up {data.get('uptime_seconds', 0):.0f}s, Ollama: {data.get('ollama_reachable')}"
        return "YELLOW", f"HTTP {r.status_code}"
    except:
        return "RED", "Router offline"

def check_github():
    headers = {}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/commits",
                        headers=headers, timeout=5, params={"per_page": 1})
        if r.status_code == 200:
            commit = r.json()[0]
            msg = commit["commit"]["message"][:40]
            date = commit["commit"]["author"]["date"][:10]
            return "GREEN", f"{date}: {msg}"
        return "YELLOW", f"HTTP {r.status_code}"
    except:
        return "RED", "GitHub unreachable"

def get_toast_latest():
    try:
        if TOAST_WEBHOOK_LOG.exists():
            data = json.loads(TOAST_WEBHOOK_LOG.read_text())
            return "GREEN", f"Last: {data.get('date', '?')} | Net: ${data.get('net_food_sales', 0):,.2f}"
        return "YELLOW", "No webhook data yet"
    except:
        return "RED", "Error reading Toast log"

# === POWER SCORE ===
def calculate_power_score():
    score_file = Path("C:/ARK95X_SHARED/logs/power_score.json")
    if score_file.exists():
        try:
            data = json.loads(score_file.read_text())
            return data.get("total", 0), data.get("delta", 0)
        except:
            pass
    return 28200, 7500  # defaults from last session

# === MAIN DASHBOARD ===
st.set_page_config(
    page_title="ARK95X Command Center",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""<style>
    .stMetric {background: #1a1a2e; border-radius: 10px; padding: 10px;}
    .green {color: #00ff00;} .yellow {color: #ffff00;} .red {color: #ff0000;}
</style>""", unsafe_allow_html=True)

st.title("ARK95X SOVEREIGN COMMAND CENTER")
st.caption(f"Commander: Ben Nordskog | Leland, Iowa | {datetime.now().strftime('%Y-%m-%d %H:%M:%S CDT')}")

# === PANEL 1: SERVICE HEALTH ===
st.header("Panel 1: Service Health")
c1, c2, c3, c4 = st.columns(4)

with c1:
    status, detail = check_n8n()
    st.metric("n8n Cloud", status, help=detail)
with c2:
    status, detail = check_ollama()
    st.metric("Ollama Local", status, help=detail)
with c3:
    status, detail = check_comet_router()
    st.metric("Comet Router", status, help=detail)
with c4:
    status, detail = check_github()
    st.metric("GitHub Repo", status, help=detail)

# === PANEL 2: AGENT SWARM ===
st.header("Panel 2: Agent Swarm Tracker")
agents = {
    "ALPHA-1 (Comet)": {"node": "AMARA", "role": "Commander", "status": "Active"},
    "BRAVO-2 (Grok)": {"node": "AMARA", "role": "Intel & Analysis", "status": "Active"},
    "CHARLIE-3 (Gemini)": {"node": "ARCX", "role": "Visuals/Workspace", "status": "Active"},
    "DELTA-4 (ChatGPT)": {"node": "ARCX", "role": "Protocol/Code", "status": "Active"},
    "ECHO-5 (BlackBox)": {"node": "AMARA", "role": "Code/Research", "status": "Active"},
    "FOXTROT-6 (Mistral)": {"node": "ARCX", "role": "Fast Inference", "status": "Active"},
}
for name, info in agents.items():
    st.text(f"{name} | {info['node']} | {info['role']} | {info['status']}")

# === PANEL 3: DAILY POWER SCORE ===
st.header("Panel 3: Daily Power Score")
total, delta = calculate_power_score()
st.metric("Total Points", f"{total:,}", delta=f"+{delta:,} this session")
progress = min(total / 30000, 1.0)
st.progress(progress, text=f"{'PLATINUM' if progress >= 1.0 else 'GOLD'} Tier - {progress*100:.1f}%")

# === PANEL 4: LEGAL CASE TRACKER ===
st.header("Panel 4: EQCV018537 Status")
st.warning("RSB has NOT served Nordskog Properties LLC. Court holding in abeyance (D0008 03/26/2026).")
st.text("Last docket entry: D0008 OTHER ORDER - 03/26/2026")
st.text("Next action: Monitor EDMS daily at 8:30 AM + engage attorney")
st.text("Strongest defense: Modification-to-foreclosure pipeline (13 months) = retaliation")

# === PANEL 5: TOAST POS ===
st.header("Panel 5: Toast POS Monitor")
toast_status, toast_detail = get_toast_latest()
st.metric("Toast Webhook", toast_status, help=toast_detail)
st.text("Thresholds: Void Rate > 3% = ALERT | Comp Rate > 2% = ALERT")
st.text("Audit period: Last 30 days | Food-only sales")

# === PANEL 6: SYSTEM ALERTS ===
st.header("Panel 6: Alerts & Notices")
alerts = [
    f"[{datetime.now().strftime('%H:%M')}] Gemma 4 available on Ollama - pull gemma4:e4b and gemma4:31b",
    f"[{datetime.now().strftime('%H:%M')}] Claude 5 Opus expected Q2-Q3 2026 - monitor Anthropic",
    f"[{datetime.now().strftime('%H:%M')}] GPT-4o fully retired Apr 3, 2026",
    f"[{datetime.now().strftime('%H:%M')}] GitHub Copilot data training opt-out deadline: Apr 24, 2026",
]
for alert in alerts:
    st.info(alert)

# === AUTO-REFRESH ===
st.markdown(f"<meta http-equiv='refresh' content='{REFRESH_INTERVAL}'>", unsafe_allow_html=True)
st.caption(f"Auto-refresh: {REFRESH_INTERVAL}s | Dashboard v2.0 | ARK95X NEUROLINK")
