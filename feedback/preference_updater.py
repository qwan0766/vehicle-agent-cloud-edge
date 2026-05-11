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
    memory_key: str = ""
    memory_value: str = ""
    source: str = "rule"
    confidence_delta: float = 0.0
    evidence_type: str = "behavior"
    polarity: str = "positive"
    scenario: str = ""
    confidence_weight: float = 0.0

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

        if event.execution_status == "NEEDS_CLARIFICATION":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="clarification_pending",
                delta=0,
                description="等待用户澄清，不更新偏好",
                timestamp=event.timestamp,
            )

        if event.execution_status == "NEEDS_CHARGE_CONFIRMATION":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="charge_confirmation_pending",
                delta=0,
                description="等待补能确认，不更新偏好",
                timestamp=event.timestamp,
            )

        if event.execution_status == "NEEDS_DRIVER_CONFIRMATION":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="driver_confirmation_pending",
                delta=0,
                description="等待驾驶员确认，不更新偏好",
                timestamp=event.timestamp,
            )

        if event.command_type == "NAVIGATION":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="route_preference_highway",
                delta=1,
                description="路线偏好高速 +1",
                timestamp=event.timestamp,
                memory_key="route_preference",
                memory_value="高速优先",
                source="repeated_behavior",
                confidence_delta=0.12,
                evidence_type="behavior",
                scenario="navigation",
                confidence_weight=0.12,
            )

        if event.command_type == "CAR_CONTROL" and "座椅加热" in event.user_input:
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="comfort_seat_heat",
                delta=1,
                description="座椅加热偏好 +1",
                timestamp=event.timestamp,
                memory_key="seat_heat_preference",
                memory_value="倾向开启座椅加热",
                source="repeated_behavior",
                confidence_delta=0.1,
                evidence_type="behavior",
                scenario="comfort",
                confidence_weight=0.1,
            )

        if event.command_type == "CHARGE_PLAN":
            return PreferenceUpdate(
                user_id=event.user_id,
                preference_key="charge_awareness",
                delta=1,
                description="补能提醒关注 +1",
                timestamp=event.timestamp,
                memory_key="charge_awareness",
                memory_value="关注低电量补能提醒",
                source="repeated_behavior",
                confidence_delta=0.1,
                evidence_type="behavior",
                scenario="energy",
                confidence_weight=0.1,
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
