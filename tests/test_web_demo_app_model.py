import unittest
import uuid
from pathlib import Path

from web_demo.app_model import run_command
from web_demo.app_model import get_initial_payload
from web_demo.app_model import get_acceptance_payload


class TestWebDemoAppModel(unittest.TestCase):
    def test_initial_payload_contains_user_options(self):
        payload = get_initial_payload()

        self.assertIn("users", payload)
        self.assertEqual(payload["users"][0]["user_id"], "user_001")
        self.assertGreaterEqual(payload["offline_evaluation"]["total"], 20)
        self.assertIn("route.plan", payload["cloud_tools"])
        self.assertIn("providers", payload)
        self.assertIn("llm", payload["providers"])
        self.assertIn("map", payload["providers"])
        self.assertIn("acceptance", payload)

    def test_acceptance_payload_parses_report_summary(self):
        runtime_dir = Path(".test_runtime")
        runtime_dir.mkdir(exist_ok=True)
        report_path = runtime_dir / f"acceptance_report_{uuid.uuid4().hex}.md"
        report_path.write_text(
            "\n".join(
                [
                    "# 车载 Multi-Agent 验收报告",
                    "",
                    "- 生成时间：2026-05-05T17:48:15+08:00",
                    "- 总体状态：PASS",
                    "",
                    "## 验收步骤",
                    "",
                    "| 步骤 | 状态 | 耗时 |",
                    "| --- | --- | ---: |",
                    "| unit tests | PASS | 20.86s |",
                    "| online matrix | PASS | 25.54s |",
                ]
            ),
            encoding="utf-8",
        )

        payload = get_acceptance_payload(report_path)

        self.assertTrue(payload["available"])
        self.assertEqual(payload["overall_status"], "PASS")
        self.assertEqual(payload["generated_at"], "2026-05-05T17:48:15+08:00")
        self.assertEqual(
            payload["steps"],
            [
                {"name": "unit tests", "status": "PASS", "duration": "20.86s"},
                {"name": "online matrix", "status": "PASS", "duration": "25.54s"},
            ],
        )

    def test_acceptance_payload_handles_missing_report(self):
        payload = get_acceptance_payload(Path("missing_acceptance_report.md"))

        self.assertFalse(payload["available"])
        self.assertEqual(payload["overall_status"], "UNKNOWN")
        self.assertEqual(payload["steps"], [])

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
        self.assertIn("route_summary", payload)
        self.assertIn("charge_stations", payload)
        self.assertGreaterEqual(payload["route_summary"]["distance_km"], 0)
        self.assertEqual(
            [item["tool_name"] for item in payload["runtime_trace"]],
            [
                "user_profile.lookup",
                "user_profile.route_preference",
                "ecology.snapshot",
                "route.plan",
                "provider.geocode",
                "provider.map.route",
                "decision.summarize",
            ],
        )

    def test_user_two_payload_contains_user_two_profile_context(self):
        payload = run_command("电量低", user_id="user_002", network="ONLINE")

        self.assertEqual(payload["request"]["user_id"], "user_002")
        self.assertTrue(
            any("user_002" in item["text"] for item in payload["rag_context"])
        )

    def test_smoke_payload_has_provider_results(self):
        from web_demo.app_model import run_provider_smoke_test

        payload = run_provider_smoke_test()

        self.assertIn("results", payload)
        self.assertTrue(any(item["name"] == "DeepSeek LLM" for item in payload["results"]))

    def test_offline_car_control_payload_contains_local_fallback_trace(self):
        payload = run_command("打开座椅加热", network="OFFLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["result"]["status"], "FALLBACK")
        self.assertIn("CarControlAgent", payload["agent_trace"])
        self.assertNotIn("CloudScheduleAgent", payload["agent_trace"])

    def test_online_car_control_payload_does_not_call_route_agent(self):
        payload = run_command("温度调到24度", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["result"]["status"], "EXECUTED")
        self.assertNotIn("CloudRoutePlanAgent", payload["agent_trace"])
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertNotIn(
            "route.plan",
            [item["tool_name"] for item in payload["runtime_trace"]],
        )

    def test_online_personalize_payload_does_not_create_route_summary(self):
        payload = run_command("我的偏好", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "PERSONALIZE")
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertNotIn("CloudRoutePlanAgent", payload["agent_trace"])

    def test_dangerous_command_payload_is_blocked(self):
        payload = run_command("加速到100km/h", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["request"]["safety"], "DANGEROUS")
        self.assertEqual(payload["result"]["status"], "BLOCKED")
        self.assertIn("SafetyAgent", payload["agent_trace"])


if __name__ == "__main__":
    unittest.main()
