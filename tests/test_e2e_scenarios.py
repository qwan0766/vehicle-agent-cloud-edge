import uuid
import unittest
from pathlib import Path

from core.constants import ExecutionStatus, NetworkStatus
from core.vehicle_core_service import VehicleCoreService
from feedback.feedback_service import FeedbackService


class TestE2EScenarios(unittest.TestCase):
    def test_online_navigation_records_feedback_and_uses_cloud(self):
        runtime_dir = Path(".test_runtime") / f"e2e_{uuid.uuid4().hex}"
        service = VehicleCoreService(feedback_service=FeedbackService(runtime_dir))

        result = service.run("导航去蔚来中心", user_id="user_001", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.EXECUTED)
        self.assertIn("结合用户路线偏好高速", result.output)
        self.assertEqual(result.feedback["event_status"], "RECORDED")
        self.assertTrue((runtime_dir / "usage_events.jsonl").exists())

    def test_unknown_command_is_blocked_by_policy(self):
        service = VehicleCoreService()

        result = service.run("播放一首歌", user_id="user_001", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.BLOCKED)
        self.assertIn("未知指令", result.output)


if __name__ == "__main__":
    unittest.main()
