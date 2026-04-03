"""
ARK95X NEUROLINK // COMET ROUTER
FastAPI broker between AMARA browser agents and Ollama on ARCX
Deploy on ARCX: python comet_router.py
"""
import os, json, time, uuid, logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional
import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

APP_NAME = "ARK95X Comet Router"
APP_VERSION = "1.0.0"
ROUTER_BIND_HOST = os.getenv("COMET_ROUTER_HOST", "0.0.0.0")
ROUTER_BIND_PORT = int(os.getenv("COMET_ROUTER_PORT", "8000"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
ROUTER_AUTH_TOKEN = os.getenv("COMET_ROUTER_TOKEN", "CHANGE-ME-NOW")
LOG_DIR = Path(os.getenv("COMET_LOG_DIR", r"C:\ARK95X_SHARED\logs"))
LOG_FILE = LOG_DIR / "router.log"
UPSTREAM_TIMEOUT = float(os.getenv("COMET_ROUTER_TIMEOUT", "300"))

def setup_logging():
    logger = logging.getLogger("comet_router")
    logger.setLevel(logging.INFO)
    if logger.handlers: return logger
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(fh)
    except Exception:
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(ch)
    return logger

logger = setup_logging()
app = FastAPI(title=APP_NAME, version=APP_VERSION)
startup_time = time.time()

class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    uptime_seconds: float
    ollama_reachable: bool

def validate_token(x_auth_token, authorization):
    bearer = None
    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            bearer = parts[1].strip()
    presented = x_auth_token or bearer
    if not presented or presented != ROUTER_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

async def check_ollama():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except: return False

@app.get("/health", response_model=HealthResponse)
async def health():
    reachable = await check_ollama()
    uptime = round(time.time() - startup_time, 2)
    return HealthResponse(status="ok" if reachable else "degraded",
                          app=APP_NAME, version=APP_VERSION,
                          uptime_seconds=uptime, ollama_reachable=reachable)

@app.get("/status")
async def status(x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
                 authorization: Optional[str] = Header(default=None, alias="Authorization")):
    validate_token(x_auth_token, authorization)
    return {"status": "online", "app": APP_NAME, "version": APP_VERSION,
            "uptime_seconds": round(time.time() - startup_time, 2),
            "ollama_base_url": OLLAMA_BASE_URL, "log_file": str(LOG_FILE)}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request,
    x_auth_token: Optional[str] = Header(default=None, alias="X-Auth-Token"),
    authorization: Optional[str] = Header(default=None, alias="Authorization")):
    validate_token(x_auth_token, authorization)
    rid = str(uuid.uuid4())
    try: payload = await request.json()
    except: raise HTTPException(400, "Invalid JSON")
    model = payload.get("model", "unknown")
    logger.info(f"PROXY_START | rid={rid} | model={model}")
    url = f"{OLLAMA_BASE_URL}/v1/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
        logger.info(f"PROXY_END | rid={rid} | status={resp.status_code}")
        return JSONResponse(status_code=resp.status_code,
                            content=json.loads(resp.content.decode("utf-8")),
                            headers={"X-Request-ID": rid})
    except httpx.ReadTimeout:
        raise HTTPException(504, "Ollama timeout")
    except httpx.ConnectError:
        raise HTTPException(503, "Cannot connect to Ollama")
    except Exception as e:
        logger.exception(f"ERROR | rid={rid} | {repr(e)}")
        raise HTTPException(500, "Router failure")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("comet_router:app", host=ROUTER_BIND_HOST, port=ROUTER_BIND_PORT)
