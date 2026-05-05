import unittest

from web_demo.app_model import run_command
from web_demo.app_model import get_initial_payload


class TestWebDemoAppModel(unittest.TestCase):
    def test_initial_payload_contains_user_options(self):
        payload = get_initial_payload()

        self.assertIn("users", payload)
        self.assertEqual(payload["users"][0]["user_id"], "user_001")

    def test_online_navigation_payload_contains_cloud_trace(self):
        payload = run_command("导航去蔚来中心", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "NAVIGATION")
        self.assertEqual(payload["result"]["status"], "EXECUTED")
        self.assertIn("RAG路线结果", payload["result"]["output"])
        self.assertIn("CloudScheduleAgent", payload["agent_trace"])
        self.assertIn("CloudRoutePlanAgent", payload["agent_trace"])
        self.assertIn("rag_context", payload)
        self.assertTrue(payload["rag_context"])
        self.assertTrue(
            any(item["stage"] == "用户画像召回" for item in payload["rag_context"])
        )
        self.assertEqual(payload["feedback"]["event_status"], "RECORDED")
        self.assertIn("路线偏好高速", payload["feedback"]["preference_update"])
        self.assertEqual(
            [item["tool_name"] for item in payload["runtime_trace"]],
            [
                "user_profile.lookup",
                "user_profile.route_preference",
                "ecology.snapshot",
                "route.plan",
            ],
        )

    def test_user_two_payload_contains_user_two_profile_context(self):
        payload = run_command("电量低", user_id="user_002", network="ONLINE")

        self.assertEqual(payload["request"]["user_id"], "user_002")
        self.assertTrue(
            any("user_002" in item["text"] for item in payload["rag_context"])
        )

    def test_offline_car_control_payload_contains_local_fallback_trace(self):
        payload = run_command("打开座椅加热", network="OFFLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["result"]["status"], "FALLBACK")
        self.assertIn("CarControlAgent", payload["agent_trace"])
        self.assertNotIn("CloudScheduleAgent", payload["agent_trace"])

    def test_dangerous_command_payload_is_blocked(self):
        payload = run_command("加速到100km/h", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["request"]["safety"], "DANGEROUS")
        self.assertEqual(payload["result"]["status"], "BLOCKED")
        self.assertIn("SafetyAgent", payload["agent_trace"])


if __name__ == "__main__":
    unittest.main()
