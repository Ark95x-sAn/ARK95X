"""
ARK95X Agent Passback & Handoff Protocol
Advanced error recovery with dual-team escalation
Learns from every failure to prevent recurrence
"""
import json, time, asyncio, httpx
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

@dataclass
class PassbackEvent:
    task_id: str
    error_type: str
    error_msg: str
    agent_from: str
    agent_to: str
    strategy: str
    success: bool = False
    resolution_time: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

class PassbackEngine:
    def __init__(self):
        self.history: list[PassbackEvent] = []
        self.pattern_db = self._load_patterns()
        self.strategy_scores = {
            "parallel_retry": 0.7, "model_swap": 0.6, "decompose": 0.5,
            "node_failover": 0.8, "escalate_dual": 0.9, "reduce_payload": 0.65
        }

    def _load_patterns(self) -> dict:
        p = Path("C:/ARK95X/config/learned_patterns.json")
        if p.exists():
            return json.loads(p.read_text())
        return {
            "thinking_loop": {"trigger": "stuck thinking", "fix": "switch_mode_instant", "hits": 0},
            "popup_block": {"trigger": "overlay blocks", "fix": "escape_then_retry", "hits": 0},
            "click_miss": {"trigger": "wrong element", "fix": "use_ref_not_coords", "hits": 0},
            "content_lost": {"trigger": "content not saved", "fix": "restore_or_retype", "hits": 0},
            "nav_redirect": {"trigger": "wrong page", "fix": "back_then_ref_click", "hits": 0},
            "stale_ref": {"trigger": "ref invalid", "fix": "reread_page", "hits": 0},
            "timeout": {"trigger": "took too long", "fix": "reduce_payload", "hits": 0},
        }

    def diagnose(self, error_msg: str) -> tuple[str, str, float]:
        """Returns (pattern_name, fix_strategy, confidence)"""
        error_lower = error_msg.lower()
        best_match = None
        best_score = 0
        for name, pattern in self.pattern_db.items():
            words = pattern["trigger"].split()
            matches = sum(1 for w in words if w in error_lower)
            score = matches / len(words) if words else 0
            score += pattern.get("hits", 0) * 0.01  # boost patterns that worked before
            if score > best_score:
                best_score = score
                best_match = name
        if best_match and best_score > 0.3:
            fix = self.pattern_db[best_match]["fix"]
            return best_match, fix, best_score
        return "unknown", "parallel_retry", 0.1

    def select_strategy(self, error_type: str, retry_count: int, agent_node: str) -> str:
        """Pick best recovery strategy based on error + history"""
        if retry_count >= 3:
            return "escalate_dual"
        # Check what worked before for this error type
        similar = [e for e in self.history if e.error_type == error_type and e.success]
        if similar:
            best = max(similar, key=lambda e: 1/max(e.resolution_time, 0.1))
            return best.strategy
        # Score-based selection
        if "timeout" in error_type or "too long" in error_type:
            return "reduce_payload"
        if "node" in error_type or "unreachable" in error_type:
            return "node_failover"
        if retry_count == 1:
            return "model_swap"
        if retry_count == 2:
            return "decompose"
        return "parallel_retry"

    async def execute_passback(self, task_id, error_msg, agent_from, available_agents, dispatch_fn):
        """Execute the full passback protocol"""
        start = time.time()
        pattern, fix, confidence = self.diagnose(error_msg)
        strategy = self.select_strategy(pattern, 0, agent_from)
        # Pick target agent (different from source)
        target = next((a for a in available_agents if a != agent_from), available_agents[0])
        event = PassbackEvent(
            task_id=task_id, error_type=pattern, error_msg=error_msg,
            agent_from=agent_from, agent_to=target, strategy=strategy
        )
        try:
            result = await dispatch_fn(task_id, target, strategy)
            event.success = True
            event.resolution_time = time.time() - start
            # Boost the pattern that worked
            if pattern in self.pattern_db:
                self.pattern_db[pattern]["hits"] = self.pattern_db[pattern].get("hits", 0) + 1
            # Update strategy scores
            self.strategy_scores[strategy] = min(1.0, self.strategy_scores.get(strategy, 0.5) + 0.05)
        except Exception as e:
            event.success = False
            event.resolution_time = time.time() - start
            self.strategy_scores[strategy] = max(0.1, self.strategy_scores.get(strategy, 0.5) - 0.1)
        self.history.append(event)
        self._save_history()
        self._save_patterns()
        return event

    def learn_new_pattern(self, trigger: str, fix: str, source: str):
        """Runtime learning: add new pattern from live errors"""
        name = f"runtime_{len(self.pattern_db)}_{int(time.time())}"
        self.pattern_db[name] = {"trigger": trigger, "fix": fix, "source": source, "hits": 0}
        self._save_patterns()

    def get_metrics(self) -> dict:
        total = len(self.history)
        success = sum(1 for e in self.history if e.success)
        avg_time = sum(e.resolution_time for e in self.history) / max(total, 1)
        by_strategy = {}
        for e in self.history:
            if e.strategy not in by_strategy:
                by_strategy[e.strategy] = {"total": 0, "success": 0}
            by_strategy[e.strategy]["total"] += 1
            if e.success:
                by_strategy[e.strategy]["success"] += 1
        return {
            "total_passbacks": total, "successful": success,
            "success_rate": round(success/max(total,1)*100, 1),
            "avg_resolution_sec": round(avg_time, 2),
            "patterns_known": len(self.pattern_db),
            "strategy_effectiveness": by_strategy,
            "strategy_scores": self.strategy_scores
        }

    def _save_history(self):
        Path("C:/ARK95X/logs").mkdir(parents=True, exist_ok=True)
        data = [{"task": e.task_id, "error": e.error_type, "strategy": e.strategy,
                 "success": e.success, "time": e.resolution_time, "ts": e.timestamp}
                for e in self.history[-100:]]  # keep last 100
        Path("C:/ARK95X/logs/passback_history.json").write_text(json.dumps(data, indent=2))

    def _save_patterns(self):
        Path("C:/ARK95X/config").mkdir(parents=True, exist_ok=True)
        Path("C:/ARK95X/config/learned_patterns.json").write_text(json.dumps(self.pattern_db, indent=2))

if __name__ == "__main__":
    engine = PassbackEngine()
    print(json.dumps(engine.get_metrics(), indent=2))
