import json
from pathlib import Path

from feedback.preference_updater import PreferenceUpdate


class PreferenceStore:
    def __init__(self, path: Path = Path("runtime/user_preference_state.json")):
        self.path = Path(path)

    def apply(self, update: PreferenceUpdate):
        state = self._load()
        user_state = state.setdefault(update.user_id, {})
        current = int(user_state.get(update.preference_key, 0))
        user_state[update.preference_key] = current + update.delta
        self._save(state)
        return user_state

    def get_user_state(self, user_id: str):
        return self._load().get(user_id, {})

    def _load(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
