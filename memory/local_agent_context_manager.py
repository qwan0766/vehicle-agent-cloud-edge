from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List


DEFAULT_LOCAL_AGENT_ID = "local_intent"
DEFAULT_SESSION_ID = "default"


@dataclass(frozen=True)
class LocalContextTurn:
    request_id: str
    user_id: str
    user_input: str
    command_type: str
    safety: str
    network: str
    execution_status: str
    output: str
    timestamp: str

    def to_dict(self):
        return asdict(self)


class LocalAgentContextManager:
    def __init__(
        self,
        path: Path = Path("runtime/local_context_state.json"),
        max_recent_turns: int = 4,
        max_summary_chars: int = 600,
        max_output_chars: int = 160,
        default_agent_id: str = DEFAULT_LOCAL_AGENT_ID,
        default_session_id: str = DEFAULT_SESSION_ID,
    ):
        self.path = Path(path)
        self.max_recent_turns = max(1, int(max_recent_turns))
        self.max_summary_chars = max(80, int(max_summary_chars))
        self.max_output_chars = max(40, int(max_output_chars))
        self.default_agent_id = default_agent_id
        self.default_session_id = default_session_id

    def record_result(self, result, agent_id: str = None, session_id: str = None):
        state = self._load()
        scoped_state = self._scoped_state(
            state,
            agent_id or self.default_agent_id,
            result.message.user_id,
            session_id or self.default_session_id,
        )
        turn = self._turn_from_result(result)
        scoped_state["recent_turns"].append(turn.to_dict())
        scoped_state["total_turns"] = int(scoped_state.get("total_turns", 0)) + 1
        self._compress_if_needed(scoped_state)
        self._save(state)
        return self.snapshot(
            result.message.user_id,
            agent_id=agent_id or self.default_agent_id,
            session_id=session_id or self.default_session_id,
        )

    def snapshot(self, user_id: str, agent_id: str = None, session_id: str = None) -> Dict:
        resolved_agent_id = agent_id or self.default_agent_id
        resolved_session_id = session_id or self.default_session_id
        state = self._load()
        scoped_state = self._scoped_state(
            state,
            resolved_agent_id,
            user_id,
            resolved_session_id,
        )
        return {
            "memory_scope": "agent_local",
            "agent_id": resolved_agent_id,
            "session_id": resolved_session_id,
            "user_id": user_id,
            "summary": scoped_state["summary"],
            "recent_turns": list(scoped_state["recent_turns"]),
            "total_turns": int(scoped_state["total_turns"]),
            "compressed_turns": int(scoped_state["compressed_turns"]),
            "max_recent_turns": self.max_recent_turns,
            "max_summary_chars": self.max_summary_chars,
        }

    def build_local_llm_context(
        self,
        user_id: str,
        preference_state=None,
        agent_id: str = None,
        session_id: str = None,
        current_input: str = "",
        vehicle_state=None,
        retrieved_context=None,
    ) -> Dict:
        snapshot = self.snapshot(
            user_id,
            agent_id=agent_id or self.default_agent_id,
            session_id=session_id or self.default_session_id,
        )
        return {
            "memory_scope": "agent_local",
            "agent_id": snapshot["agent_id"],
            "session_id": snapshot["session_id"],
            "current_input": current_input,
            "summary": snapshot["summary"],
            "recent_turns": snapshot["recent_turns"],
            "preference_state": preference_state or {},
            "vehicle_state": vehicle_state or {},
            "retrieved_context": retrieved_context or [],
            "window": {
                "total_turns": snapshot["total_turns"],
                "compressed_turns": snapshot["compressed_turns"],
                "max_recent_turns": snapshot["max_recent_turns"],
                "context_limit_tokens": 7500,
                "generation_buffer_tokens": 500,
            },
        }

    def _turn_from_result(self, result) -> LocalContextTurn:
        return LocalContextTurn(
            request_id=result.message.request_id,
            user_id=result.message.user_id,
            user_input=result.message.content,
            command_type=result.message.command_type.value,
            safety=result.message.safety.value,
            network=result.message.network.value,
            execution_status=result.status.value,
            output=self._truncate(result.output),
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )

    def _compress_if_needed(self, scoped_state: Dict) -> None:
        recent_turns: List[Dict] = scoped_state["recent_turns"]
        if len(recent_turns) <= self.max_recent_turns:
            return

        overflow_count = len(recent_turns) - self.max_recent_turns
        overflow = recent_turns[:overflow_count]
        scoped_state["recent_turns"] = recent_turns[overflow_count:]
        scoped_state["compressed_turns"] = int(scoped_state["compressed_turns"]) + len(
            overflow
        )

        fragments = [self._summarize_turn(turn) for turn in overflow]
        merged = " | ".join(
            item for item in [scoped_state.get("summary", ""), *fragments] if item
        )
        scoped_state["summary"] = self._trim_summary(merged)

    def _summarize_turn(self, turn: Dict) -> str:
        return (
            f"{turn.get('command_type')}:{turn.get('execution_status')} "
            f"user={turn.get('user_input')} -> {self._truncate(turn.get('output', ''), 80)}"
        )

    def _trim_summary(self, summary: str) -> str:
        if len(summary) <= self.max_summary_chars:
            return summary
        return "..." + summary[-(self.max_summary_chars - 3) :]

    def _truncate(self, value, limit=None) -> str:
        limit = limit or self.max_output_chars
        text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)] + "..."

    def _scoped_state(
        self,
        state: Dict,
        agent_id: str,
        user_id: str,
        session_id: str,
    ) -> Dict:
        if "agents" not in state:
            self._migrate_legacy_state(state)
        return (
            state.setdefault("agents", {})
            .setdefault(agent_id, {})
            .setdefault("users", {})
            .setdefault(user_id, {})
            .setdefault("sessions", {})
            .setdefault(session_id, self._empty_scope())
        )

    def _migrate_legacy_state(self, state: Dict) -> None:
        if not state:
            state["agents"] = {}
            return
        legacy_users = {
            key: value
            for key, value in list(state.items())
            if isinstance(value, dict) and "recent_turns" in value
        }
        state.clear()
        state["agents"] = {}
        for user_id, user_state in legacy_users.items():
            state["agents"].setdefault(self.default_agent_id, {}).setdefault(
                "users", {}
            ).setdefault(user_id, {}).setdefault("sessions", {})[
                self.default_session_id
            ] = {
                "summary": user_state.get("summary", ""),
                "recent_turns": list(user_state.get("recent_turns", [])),
                "total_turns": int(user_state.get("total_turns", 0)),
                "compressed_turns": int(user_state.get("compressed_turns", 0)),
            }

    def _empty_scope(self) -> Dict:
        return {
            "summary": "",
            "recent_turns": [],
            "total_turns": 0,
            "compressed_turns": 0,
        }

    def _load(self) -> Dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, state: Dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
