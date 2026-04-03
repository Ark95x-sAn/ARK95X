"""
ARK95X Agent Orchestrator - Dual IT Team Protocol
Self-learning, self-upgrading agent system with passback/handoff
Patterns learned from COMET-01 session data
"""
import json, asyncio, httpx, time, os
from datetime import datetime
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

class AgentRole(Enum):
    ALPHA_LEAD = "alpha_lead"       # Primary orchestrator (Comet)
    BRAVO_CODE = "bravo_code"       # Code gen (ChatGPT Pro)
    CHARLIE_VISUAL = "charlie_vis"  # Visuals/maps (Gemini Pro)
    DELTA_RESEARCH = "delta_res"    # Research/verify (BlackBox)
    ECHO_MONITOR = "echo_mon"       # Health/scale monitor
    FOXTROT_RECOVER = "fox_recover" # Error recovery specialist

class TaskStatus(Enum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    PASSBACK = "passback"        # Failed, needs re-route
    COMPLETE = "complete"
    ESCALATED = "escalated"      # Dual-team takeover

@dataclass
class AgentState:
    role: AgentRole
    node: str  # amara or arcx
    endpoint: str
    model: str
    busy: bool = False
    error_count: int = 0
    tasks_done: int = 0
    last_error: str = ""
    specialties: list = field(default_factory=list)

@dataclass
class Task:
    id: str
    content: str
    status: TaskStatus = TaskStatus.QUEUED
    assigned_to: Optional[AgentRole] = None
    backup_agent: Optional[AgentRole] = None
    retries: int = 0
    max_retries: int = 3
    result: str = ""
    error_log: list = field(default_factory=list)
    created: str = field(default_factory=lambda: datetime.now().isoformat())

# === LEARNED PATTERNS FROM SESSION ===
ERROR_PATTERNS = {
    "thinking_loop": {"trigger": "agent stuck in thinking", "fix": "switch_mode_instant", "learned_from": "chatgpt_thinking_bug"},
    "popup_block": {"trigger": "popup/overlay blocks action", "fix": "escape_then_retry", "learned_from": "gemini_monica_popups"},
    "click_miss": {"trigger": "wrong element clicked", "fix": "use_ref_not_coords", "learned_from": "github_commit_link_overlap"},
    "content_lost": {"trigger": "form content not saved", "fix": "restore_or_retype", "learned_from": "github_unsaved_changes"},
    "nav_redirect": {"trigger": "navigation went wrong page", "fix": "back_then_ref_click", "learned_from": "github_learn_more_link"},
    "stale_ref": {"trigger": "element ref no longer valid", "fix": "reread_page_get_new_refs", "learned_from": "page_reload_stale_dom"},
    "timeout": {"trigger": "action took too long", "fix": "reduce_payload_retry", "learned_from": "large_form_input_timeout"},
}

PASSBACK_STRATEGIES = {
    "parallel_retry": "Send same task to backup agent while primary recovers",
    "decompose": "Break failed task into smaller subtasks",
    "escalate_dual": "Both teams work the problem simultaneously",
    "model_swap": "Switch to different AI model for the task",
    "node_failover": "Move task from AMARA to ARCX or vice versa",
}

class DualTeamOrchestrator:
    def __init__(self, config_path="C:/ARK95X/config/agents.json"):
        self.config_path = config_path
        self.task_queue: list[Task] = []
        self.completed: list[Task] = []
        self.agents: dict[AgentRole, AgentState] = {}
        self.pattern_db = ERROR_PATTERNS.copy()
        self.metrics = {"tasks_total": 0, "passbacks": 0, "recoveries": 0, "upgrades": 0}
        self._init_agents()

    def _init_agents(self):
        self.agents = {
            AgentRole.ALPHA_LEAD: AgentState(
                role=AgentRole.ALPHA_LEAD, node="amara", endpoint="http://ark95x-amara:8000",
                model="comet-01", specialties=["orchestration","dispatch","dashboard"]
            ),
            AgentRole.BRAVO_CODE: AgentState(
                role=AgentRole.BRAVO_CODE, node="amara", endpoint="http://ark95x-amara:8000/api/chatgpt",
                model="chatgpt-pro", specialties=["powershell","python","json","bootstrap"]
            ),
            AgentRole.CHARLIE_VISUAL: AgentState(
                role=AgentRole.CHARLIE_VISUAL, node="amara", endpoint="http://ark95x-amara:8000/api/gemini",
                model="gemini-pro", specialties=["mindmap","visuals","charts","verification"]
            ),
            AgentRole.DELTA_RESEARCH: AgentState(
                role=AgentRole.DELTA_RESEARCH, node="arcx", endpoint="http://ark95x-arcx:8000/api/blackbox",
                model="blackbox-ai", specialties=["research","verification","web_search"]
            ),
            AgentRole.ECHO_MONITOR: AgentState(
                role=AgentRole.ECHO_MONITOR, node="arcx", endpoint="http://ark95x-arcx:11434",
                model="mistral", specialties=["health","monitoring","alerts","scaling"]
            ),
            AgentRole.FOXTROT_RECOVER: AgentState(
                role=AgentRole.FOXTROT_RECOVER, node="arcx", endpoint="http://ark95x-arcx:11434",
                model="codellama", specialties=["error_recovery","passback","retry_logic"]
            ),
        }

    def match_agent(self, task: Task) -> tuple[AgentRole, AgentRole]:
        """Dual-team matching: primary + backup based on task content"""
        scores = {}
        for role, agent in self.agents.items():
            score = sum(1 for s in agent.specialties if s in task.content.lower())
            score -= agent.error_count * 0.5
            score += agent.tasks_done * 0.1
            if agent.busy: score -= 2
            scores[role] = score
        ranked = sorted(scores, key=scores.get, reverse=True)
        return ranked[0], ranked[1]  # primary, backup

    async def dispatch(self, task: Task):
        primary, backup = self.match_agent(task)
        task.assigned_to = primary
        task.backup_agent = backup
        task.status = TaskStatus.DISPATCHED
        agent = self.agents[primary]
        agent.busy = True
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(f"{agent.endpoint}/task", json={"task": task.content, "model": agent.model})
                if resp.status_code == 200:
                    task.result = resp.json().get("result", "")
                    task.status = TaskStatus.COMPLETE
                    agent.tasks_done += 1
                    self.metrics["tasks_total"] += 1
                else:
                    raise Exception(f"HTTP {resp.status_code}")
        except Exception as e:
            task.error_log.append({"time": datetime.now().isoformat(), "error": str(e), "agent": primary.value})
            task.status = TaskStatus.PASSBACK
            agent.error_count += 1
            self.metrics["passbacks"] += 1
            await self._passback(task)
        finally:
            agent.busy = False

    async def _passback(self, task: Task):
        """PASSBACK PROTOCOL: learned from session error patterns"""
        error_str = str(task.error_log[-1]["error"]).lower() if task.error_log else ""
        strategy = self._match_error_pattern(error_str)
        if task.retries >= task.max_retries:
            task.status = TaskStatus.ESCALATED
            await self._escalate_dual_team(task)
            return
        task.retries += 1
        if strategy == "model_swap":
            backup = self.agents[task.backup_agent]
            task.assigned_to = task.backup_agent
            await self.dispatch(task)
        elif strategy == "decompose":
            subtasks = self._decompose_task(task)
            for st in subtasks:
                self.task_queue.append(st)
        elif strategy == "node_failover":
            current_node = self.agents[task.assigned_to].node
            target = "arcx" if current_node == "amara" else "amara"
            for role, agent in self.agents.items():
                if agent.node == target and not agent.busy:
                    task.assigned_to = role
                    await self.dispatch(task)
                    break
        else:
            await asyncio.sleep(2 ** task.retries)
            await self.dispatch(task)
        self.metrics["recoveries"] += 1

    def _match_error_pattern(self, error: str) -> str:
        for name, pattern in self.pattern_db.items():
            if any(word in error for word in pattern["trigger"].split()):
                return pattern["fix"]
        return "parallel_retry"

    async def _escalate_dual_team(self, task: Task):
        """Both teams work simultaneously - the session pattern that solved hard problems"""
        results = await asyncio.gather(
            self._try_agent(task, AgentRole.BRAVO_CODE),
            self._try_agent(task, AgentRole.DELTA_RESEARCH),
            return_exceptions=True
        )
        for r in results:
            if not isinstance(r, Exception) and r:
                task.result = r
                task.status = TaskStatus.COMPLETE
                return
        task.status = TaskStatus.ESCALATED

    async def _try_agent(self, task, role):
        agent = self.agents[role]
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(f"{agent.endpoint}/task", json={"task": task.content})
            return resp.json().get("result", "")

    def _decompose_task(self, task: Task) -> list[Task]:
        parts = task.content.split(";") if ";" in task.content else [task.content]
        return [Task(id=f"{task.id}_sub{i}", content=p.strip()) for i, p in enumerate(parts)]

    def learn_pattern(self, trigger: str, fix: str, source: str):
        """Self-upgrade: add new error patterns from runtime"""
        name = f"learned_{len(self.pattern_db)}"
        self.pattern_db[name] = {"trigger": trigger, "fix": fix, "learned_from": source}
        self.metrics["upgrades"] += 1
        self._save_patterns()

    def _save_patterns(self):
        Path("C:/ARK95X/config").mkdir(parents=True, exist_ok=True)
        with open("C:/ARK95X/config/learned_patterns.json", "w") as f:
            json.dump(self.pattern_db, f, indent=2)

    async def run_queue(self):
        while self.task_queue:
            task = self.task_queue.pop(0)
            await self.dispatch(task)
            if task.status == TaskStatus.COMPLETE:
                self.completed.append(task)

    def status_report(self) -> dict:
        return {
            "timestamp": datetime.now().isoformat(),
            "agents": {r.value: {"busy": a.busy, "errors": a.error_count, "done": a.tasks_done} for r, a in self.agents.items()},
            "metrics": self.metrics,
            "patterns_learned": len(self.pattern_db),
            "queue_depth": len(self.task_queue),
        }

if __name__ == "__main__":
    orch = DualTeamOrchestrator()
    print(json.dumps(orch.status_report(), indent=2))
