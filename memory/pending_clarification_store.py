import json
from pathlib import Path


class PendingClarificationStore:
    def __init__(self, path: Path = Path("runtime/pending_clarifications.json")):
        self.path = Path(path)

    def save(self, user_id: str, session_id: str, payload: dict) -> None:
        state = self._load()
        state[self._key(user_id, session_id)] = dict(payload or {})
        self._save(state)

    def get(self, user_id: str, session_id: str):
        return self._load().get(self._key(user_id, session_id))

    def clear(self, user_id: str, session_id: str) -> None:
        state = self._load()
        state.pop(self._key(user_id, session_id), None)
        self._save(state)

    def _key(self, user_id: str, session_id: str) -> str:
        return f"{user_id}:{session_id}"

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
