import unittest
import uuid
from pathlib import Path

from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.message import Message
from core.vehicle_core_service import ExecutionResult, VehicleCoreService
from memory.local_context_manager import LocalContextManager


def make_result(
    user_input,
    command_type=CommandType.NAVIGATION,
    status=ExecutionStatus.EXECUTED,
    network=NetworkStatus.ONLINE,
    output="ok",
    user_id="user_001",
):
    message = Message.create(
        user_id=user_id,
        command_type=command_type,
        safety=SafetyLevel.SAFE,
        content=user_input,
        network=network,
    )
    return ExecutionResult(status=status, output=output, message=message)


class TestLocalContextManager(unittest.TestCase):
    def test_records_recent_turns_per_user(self):
        path = Path(".test_runtime") / f"local_context_{uuid.uuid4().hex}.json"
        manager = LocalContextManager(path=path, max_recent_turns=3)

        manager.record_result(make_result("navigate home", user_id="user_001"))
        manager.record_result(make_result("seat heat", user_id="user_002"))

        user_one = manager.snapshot("user_001")
        user_two = manager.snapshot("user_002")

        self.assertEqual(user_one["total_turns"], 1)
        self.assertEqual(user_one["recent_turns"][0]["user_input"], "navigate home")
        self.assertEqual(user_two["recent_turns"][0]["user_input"], "seat heat")

    def test_compresses_old_turns_when_recent_window_overflows(self):
        path = Path(".test_runtime") / f"local_context_{uuid.uuid4().hex}.json"
        manager = LocalContextManager(path=path, max_recent_turns=2, max_summary_chars=180)

        manager.record_result(make_result("first navigation", output="first route"))
        manager.record_result(make_result("second navigation", output="second route"))
        manager.record_result(make_result("third navigation", output="third route"))

        snapshot = manager.snapshot("user_001")

        self.assertEqual(snapshot["total_turns"], 3)
        self.assertEqual(snapshot["compressed_turns"], 1)
        self.assertEqual([item["user_input"] for item in snapshot["recent_turns"]], ["second navigation", "third navigation"])
        self.assertIn("first navigation", snapshot["summary"])
        self.assertLessEqual(len(snapshot["summary"]), 180)

    def test_offline_service_exposes_local_context_snapshot(self):
        path = Path(".test_runtime") / f"local_context_{uuid.uuid4().hex}.json"
        manager = LocalContextManager(path=path, max_recent_turns=3)
        service = VehicleCoreService(context_manager=manager)

        service.run("导航去蔚来中心", network=NetworkStatus.ONLINE)
        result = service.run("打开座椅加热", network=NetworkStatus.OFFLINE)

        self.assertEqual(result.status, ExecutionStatus.FALLBACK)
        self.assertEqual(result.local_context["total_turns"], 2)
        self.assertTrue(
            any(item["user_input"] == "导航去蔚来中心" for item in result.local_context["recent_turns"])
        )


if __name__ == "__main__":
    unittest.main()
