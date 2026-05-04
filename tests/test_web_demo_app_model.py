import unittest

from web_demo.app_model import run_command


class TestWebDemoAppModel(unittest.TestCase):
    def test_online_navigation_payload_contains_cloud_trace(self):
        payload = run_command("导航去蔚来中心", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "NAVIGATION")
        self.assertEqual(payload["result"]["status"], "EXECUTED")
        self.assertIn("RAG路线结果", payload["result"]["output"])
        self.assertIn("CloudScheduleAgent", payload["agent_trace"])
        self.assertIn("CloudRoutePlanAgent", payload["agent_trace"])
        self.assertIn("rag_context", payload)
        self.assertTrue(payload["rag_context"])

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
