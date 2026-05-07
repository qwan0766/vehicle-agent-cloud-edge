import json
import unittest
import uuid
from pathlib import Path

from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.message import Message
from core.vehicle_core_service import ExecutionResult
from feedback.feedback_service import FeedbackService
from feedback.preference_updater import PreferenceUpdater
from feedback.usage_logger import UsageEvent, UsageLogger


class TestFeedbackLoop(unittest.TestCase):
    def test_usage_logger_writes_jsonl_event(self):
        log_path = Path(".test_runtime") / f"usage_events_{uuid.uuid4().hex}.jsonl"
        logger = UsageLogger(log_path)
        event = UsageEvent(
            request_id="req-001",
            user_id="user_001",
            user_input="导航去蔚来中心",
            command_type="NAVIGATION",
            safety="SAFE",
            network="ONLINE",
            execution_status="EXECUTED",
            output="ok",
            timestamp="2026-05-05T00:00:00",
        )

        logger.log(event)

        rows = log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 1)
        payload = json.loads(rows[0])
        self.assertEqual(payload["request_id"], "req-001")
        self.assertEqual(payload["command_type"], "NAVIGATION")

    def test_preference_updater_increments_navigation_preference(self):
        updater = PreferenceUpdater()
        event = UsageEvent(
            request_id="req-002",
            user_id="user_001",
            user_input="导航去蔚来中心",
            command_type="NAVIGATION",
            safety="SAFE",
            network="ONLINE",
            execution_status="EXECUTED",
            output="ok",
            timestamp="2026-05-05T00:00:00",
        )

        update = updater.update(event)

        self.assertEqual(update.preference_key, "route_preference_highway")
        self.assertEqual(update.delta, 1)
        self.assertIn("路线偏好高速", update.description)

    def test_preference_updater_does_not_learn_from_clarification_prompt(self):
        updater = PreferenceUpdater()
        event = UsageEvent(
            request_id="req-clarify",
            user_id="user_001",
            user_input="导航去北京",
            command_type="NAVIGATION",
            safety="SAFE",
            network="ONLINE",
            execution_status="NEEDS_CLARIFICATION",
            output="请补充更具体的目的地",
            timestamp="2026-05-05T00:00:00",
        )

        update = updater.update(event)

        self.assertEqual(update.preference_key, "clarification_pending")
        self.assertEqual(update.delta, 0)
        self.assertIn("澄清", update.description)

    def test_feedback_service_records_result_and_returns_summary(self):
        runtime_dir = Path(".test_runtime") / f"feedback_service_{uuid.uuid4().hex}"
        service = FeedbackService(runtime_dir=runtime_dir)
        message = Message.create(
            user_id="user_001",
            command_type=CommandType.CAR_CONTROL,
            safety=SafetyLevel.SAFE,
            content="打开座椅加热",
            network=NetworkStatus.OFFLINE,
        )
        result = ExecutionResult(
            status=ExecutionStatus.FALLBACK,
            output="车控执行成功：打开座椅加热",
            message=message,
        )

        summary = service.record(result)

        self.assertEqual(summary["event_status"], "RECORDED")
        self.assertIn("座椅加热偏好", summary["preference_update"])
        self.assertTrue((runtime_dir / "usage_events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
