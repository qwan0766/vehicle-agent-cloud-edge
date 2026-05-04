from datetime import datetime
from pathlib import Path

from core.vehicle_core_service import ExecutionResult
from feedback.preference_updater import PreferenceUpdateLogger, PreferenceUpdater
from feedback.usage_logger import UsageEvent, UsageLogger


class FeedbackService:
    def __init__(self, runtime_dir: Path = Path("runtime")):
        self.runtime_dir = Path(runtime_dir)
        self.usage_logger = UsageLogger(self.runtime_dir / "usage_events.jsonl")
        self.preference_updater = PreferenceUpdater()
        self.preference_logger = PreferenceUpdateLogger(
            self.runtime_dir / "preference_updates.jsonl"
        )

    def record(self, result: ExecutionResult):
        event = UsageEvent(
            request_id=result.message.request_id,
            user_id=result.message.user_id,
            user_input=result.message.content,
            command_type=result.message.command_type.value,
            safety=result.message.safety.value,
            network=result.message.network.value,
            execution_status=result.status.value,
            output=result.output,
            timestamp=datetime.now().isoformat(timespec="seconds"),
        )
        self.usage_logger.log(event)
        update = self.preference_updater.update(event)
        self.preference_logger.log(update)

        return {
            "event_status": "RECORDED",
            "event_log": str(self.usage_logger.log_path),
            "preference_update": update.description,
            "preference_key": update.preference_key,
            "delta": update.delta,
        }
