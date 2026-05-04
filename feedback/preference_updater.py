from dataclasses import asdict, dataclass
import json
from pathlib import Path

from feedback.usage_logger import UsageEvent


@dataclass(frozen=True)
class PreferenceUpdate:
    user_id: str
    preference_key: str
    delta: int
    description: str
    timestamp: str

    def to_dict(self):
        return asdict(self)


class PreferenceUpdater:
    def update(self, event: UsageEvent) -> PreferenceUpdate:
        if event.safety == "DANGEROUS" or event.execution_status == "BLOCKED":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="safety_block",
                delta=0,
                description="危险指令拦截，不更新偏好",
                timestamp=event.timestamp,
            )

        if event.command_type == "NAVIGATION":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="route_preference_highway",
                delta=1,
                description="路线偏好高速 +1",
                timestamp=event.timestamp,
            )

        if event.command_type == "CAR_CONTROL" and "座椅加热" in event.user_input:
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="comfort_seat_heat",
                delta=1,
                description="座椅加热偏好 +1",
                timestamp=event.timestamp,
            )

        if event.command_type == "CHARGE_PLAN":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="charge_awareness",
                delta=1,
                description="补能提醒关注 +1",
                timestamp=event.timestamp,
            )

        return PreferenceUpdate(
            user_id=event.user_id,
            preference_key="general_interaction",
            delta=1,
            description="通用交互行为 +1",
            timestamp=event.timestamp,
        )


class PreferenceUpdateLogger:
    def __init__(self, log_path: Path):
        self.log_path = Path(log_path)

    def log(self, update: PreferenceUpdate) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(update.to_dict(), ensure_ascii=False) + "\n")
