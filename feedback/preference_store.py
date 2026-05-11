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
        self._apply_long_term_memory(user_state, update)
        self._save(state)
        return user_state

    def get_user_state(self, user_id: str):
        return self._load().get(user_id, {})

    def get_long_term_memory(self, user_id: str):
        return self.get_user_state(user_id).get("long_term_memory", {})

    def _apply_long_term_memory(self, user_state, update: PreferenceUpdate) -> None:
        if update.delta == 0:
            return
        if not update.memory_key or not update.memory_value:
            return

        memories = user_state.setdefault("long_term_memory", {})
        existing = memories.get(update.memory_key, {})
        same_value = existing.get("value") == update.memory_value
        positive_count = int(
            existing.get(
                "positive_evidence_count",
                existing.get("evidence_count", 0),
            )
            if same_value
            else 0
        )
        negative_count = int(existing.get("negative_evidence_count", 0) if same_value else 0)
        polarity = self._resolve_polarity(update)
        base_confidence = float(existing.get("confidence", 0.5) if same_value else 0.5)
        weight = self._confidence_weight(update)
        last_positive_at = existing.get("last_positive_at", "") if same_value else ""
        last_negative_at = existing.get("last_negative_at", "") if same_value else ""

        if polarity == "negative":
            negative_count += 1
            confidence = max(0.05, base_confidence - self._diminished_weight(weight, negative_count))
            last_negative_at = update.timestamp
        else:
            positive_count += 1
            confidence = min(0.95, base_confidence + self._diminished_weight(weight, positive_count))
            last_positive_at = update.timestamp

        evidence_count = positive_count + negative_count
        memories[update.memory_key] = {
            "value": update.memory_value,
            "confidence": round(confidence, 3),
            "source": update.source or "rule",
            "evidence_count": evidence_count,
            "positive_evidence_count": positive_count,
            "negative_evidence_count": negative_count,
            "evidence_type": update.evidence_type,
            "polarity": polarity,
            "scenario": update.scenario,
            "updated_at": update.timestamp,
            "last_positive_at": last_positive_at,
            "last_negative_at": last_negative_at,
            "last_evidence": update.description,
        }

    def _resolve_polarity(self, update: PreferenceUpdate) -> str:
        if update.polarity in {"positive", "negative"}:
            return update.polarity
        if update.delta < 0:
            return "negative"
        return "positive"

    def _confidence_weight(self, update: PreferenceUpdate) -> float:
        if update.confidence_weight:
            return abs(float(update.confidence_weight))
        if update.confidence_delta:
            return abs(float(update.confidence_delta))

        defaults = {
            "explicit_preference": 0.25,
            "behavior": 0.08,
            "system_inference": 0.04,
        }
        return defaults.get(update.evidence_type, 0.06)

    def _diminished_weight(self, weight: float, evidence_count: int) -> float:
        return weight / (1 + 0.25 * max(0, evidence_count - 1))

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
