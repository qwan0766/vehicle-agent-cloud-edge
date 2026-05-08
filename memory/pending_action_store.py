import json
import time
import uuid
from pathlib import Path


class PendingActionStore:
    def __init__(
        self,
        path: Path = Path("runtime/pending_actions.json"),
        ttl_seconds: int = 300,
    ):
        self.path = Path(path)
        self.ttl_seconds = ttl_seconds

    def create(
        self,
        action_type: str,
        user_id: str,
        session_id: str,
        content: str,
        command_type: str,
        network: str,
        reason: str,
        payload: dict = None,
    ) -> dict:
        now = time.time()
        action = {
            "id": str(uuid.uuid4()),
            "type": action_type,
            "user_id": user_id,
            "session_id": session_id,
            "content": content,
            "command_type": command_type,
            "network": network,
            "reason": reason,
            "payload": dict(payload or {}),
            "created_at": now,
            "expires_at": now + self.ttl_seconds,
        }
        state = self._load()
        state[action["id"]] = action
        self._save(state)
        return self.public_payload(action)

    def get(self, action_id: str):
        if not action_id:
            return None
        action = self._load().get(action_id)
        if not action:
            return None
        if self.is_expired(action):
            self.clear(action_id)
            return None
        return action

    def clear(self, action_id: str) -> None:
        state = self._load()
        state.pop(action_id, None)
        self._save(state)

    def clear_scope(self, user_id: str, session_id: str) -> None:
        state = self._load()
        scoped = [
            action_id
            for action_id, action in state.items()
            if action.get("user_id") == user_id and action.get("session_id") == session_id
        ]
        for action_id in scoped:
            state.pop(action_id, None)
        self._save(state)

    def public_payload(self, action: dict) -> dict:
        if not action:
            return {}
        return {
            "id": action.get("id", ""),
            "type": action.get("type", ""),
            "reason": action.get("reason", ""),
            "expires_at": action.get("expires_at", 0),
            "command_type": action.get("command_type", ""),
        }

    def is_expired(self, action: dict) -> bool:
        return float(action.get("expires_at") or 0) < time.time()

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
