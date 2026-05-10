import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import web_demo.app_model as app_model
from web_demo.app_model import confirm_pending_action
from web_demo.app_model import run_command
from web_demo.app_model import get_initial_payload
from web_demo.app_model import get_offline_evaluation_payload
from web_demo.app_model import get_acceptance_payload
from web_demo.app_model import get_demo_steps
from web_demo.app_model import get_vehicle_events_payload
from web_demo.app_model import reset_vehicle_state
from web_demo.app_model import update_vehicle_state
from web_demo.app_model import _rag_context
from web_demo.server import build_error_response
from core.constants import CommandType, NetworkStatus


class TestWebDemoAppModel(unittest.TestCase):
    def setUp(self):
        reset_vehicle_state()

    def test_initial_payload_contains_user_options(self):
        payload = get_initial_payload()

        self.assertIn("users", payload)
        self.assertEqual(payload["users"][0]["user_id"], "user_001")
        self.assertEqual(payload["offline_evaluation"]["status"], "PENDING")
        self.assertEqual(payload["offline_evaluation"]["total"], 0)
        self.assertIn("trip.plan", payload["cloud_tools"])
        self.assertIn("knowledge.retrieve", payload["cloud_tools"])
        self.assertIn("providers", payload)
        self.assertIn("llm", payload["providers"])
        self.assertIn("local_llm", payload["providers"])
        self.assertIn("orchestrator", payload["providers"])
        self.assertIn("map", payload["providers"])
        self.assertIn("acceptance", payload)
        self.assertIn("demo_steps", payload)
        self.assertIn("auto_events", payload)
        self.assertEqual(payload["vehicle_state"]["road_type"], "HIGHWAY")
        self.assertEqual(payload["vehicle_state"]["speed_limit_kmh"], 120)

    def test_initial_payload_does_not_block_on_offline_evaluator(self):
        with patch.object(app_model.OfflineEvaluator, "run") as run:
            payload = get_initial_payload()

        run.assert_not_called()
        self.assertEqual(payload["offline_evaluation"]["status"], "PENDING")

    def test_offline_evaluation_payload_runs_evaluator_on_demand(self):
        expected = {
            "total": 21,
            "intent_accuracy": 1.0,
            "safety_block_recall": 1.0,
            "rag_hit_rate": 1.0,
        }
        with patch.object(app_model.OfflineEvaluator, "run", return_value=expected) as run:
            payload = get_offline_evaluation_payload()

        run.assert_called_once_with()
        self.assertEqual(payload, {**expected, "status": "READY"})

    def test_demo_steps_cover_interview_storyline(self):
        steps = get_demo_steps()

        self.assertEqual(len(steps), 5)
        self.assertEqual(
            [step["id"] for step in steps],
            [
                "online_navigation",
                "fuzzy_destination_clarification",
                "highway_speed_confirmation",
                "urban_speed_block",
                "low_battery_energy_policy",
            ],
        )
        self.assertEqual(steps[0]["id"], "online_navigation")
        self.assertEqual(steps[0]["content"], "导航去蔚来中心")
        self.assertEqual(steps[0]["network"], "ONLINE")
        self.assertIn("端云协同", steps[0]["focus"])
        self.assertTrue(steps[0]["talk_track"])
        self.assertIn("expected_panels", steps[0])
        self.assertTrue(all("vehicle_state" in step for step in steps))
        self.assertEqual(steps[2]["vehicle_state"]["road_type"], "HIGHWAY")
        self.assertEqual(steps[2]["vehicle_state"]["speed_limit_kmh"], 120)
        self.assertEqual(steps[3]["vehicle_state"]["road_type"], "URBAN")
        self.assertEqual(steps[3]["vehicle_state"]["speed_limit_kmh"], 60)
        self.assertEqual(steps[4]["vehicle_state"]["battery_percent"], 8)
        self.assertTrue(any(step["content"] == "导航去北京" for step in steps))
        self.assertTrue(any(step["content"] == "加速到100km/h" for step in steps))

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
        self.assertNotIn("向量知识库召回", payload["result"]["output"])
        self.assertTrue(payload["result"]["output"])
        self.assertIn("GlobalDispatchAgent", payload["agent_trace"])
        self.assertIn("VectorKnowledgeAgent", payload["agent_trace"])
        self.assertIn("GlobalTripPlanningAgent", payload["agent_trace"])
        self.assertIn("rag_context", payload)
        self.assertTrue(payload["rag_context"])
        self.assertTrue(
            any(item["stage"] == "用户画像召回" for item in payload["rag_context"])
        )
        self.assertEqual(payload["feedback"]["event_status"], "RECORDED")
        self.assertIn("路线偏好高速", payload["feedback"]["preference_update"])
        self.assertIn("route_summary", payload)
        self.assertIn("charge_stations", payload)
        self.assertIn("input_rewrite", payload)
        self.assertIn("raw_input", payload["input_rewrite"])
        self.assertIn("rewritten_input", payload["input_rewrite"])
        self.assertIn("graph", payload)
        self.assertTrue(payload["graph"]["enabled"])
        self.assertIn(payload["graph"]["mode"], {"langgraph", "lightweight"})
        if payload["graph"]["mode"] == "langgraph":
            self.assertEqual(payload["graph"]["backend"], "StateGraph")
            self.assertFalse(payload["graph"]["fallback"])
        else:
            self.assertTrue(payload["graph"]["fallback"])
        self.assertIn("trip_plan", payload["graph"]["path"])
        self.assertGreaterEqual(payload["route_summary"]["distance_km"], 0)
        self.assertEqual(
            [item["tool_name"] for item in payload["runtime_trace"]],
            [
                "user_profile.lookup",
                "knowledge.retrieve",
                "user_profile.route_preference",
                "ecology.snapshot",
                "trip.plan",
                "provider.geocode",
                "provider.map.route",
                "decision.summarize",
            ],
        )

    def test_online_navigation_rag_context_shows_only_high_signal_knowledge(self):
        rag_context = _rag_context(
            "导航去蔚来中心",
            "user_001",
            CommandType.NAVIGATION,
            NetworkStatus.ONLINE,
        )

        stages = {item["stage"] for item in rag_context}
        doc_ids = {item["doc_id"] for item in rag_context}

        self.assertLessEqual(len(rag_context), 3)
        self.assertNotIn("本地意图识别", stages)
        self.assertNotIn("云端路线规划", stages)
        self.assertNotIn("intent_nav_nio_center", doc_ids)
        self.assertNotIn("intent_nav_home", doc_ids)
        self.assertNotIn("route_offline_navigation", doc_ids)

    def test_user_two_payload_contains_user_two_profile_context(self):
        payload = run_command("我的偏好", user_id="user_002", network="ONLINE")

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
        payload = run_command("打开座椅加热", user_id=f"user_{uuid.uuid4().hex}", network="OFFLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["result"]["status"], "FALLBACK")
        self.assertIn("CabinVehicleControlAgent", payload["agent_trace"])
        self.assertNotIn("GlobalDispatchAgent", payload["agent_trace"])
        self.assertIn("local_context", payload)
        self.assertEqual(payload["local_context"]["total_turns"], 1)
        self.assertEqual(payload["local_context"]["recent_turns"][0]["network"], "OFFLINE")
        self.assertIn("local_llm", payload["local_context"])
        self.assertIn("prompt_preview", payload["local_context"]["local_llm"])

    def test_online_car_control_payload_does_not_call_route_agent(self):
        payload = run_command("温度调到24度", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["result"]["status"], "EXECUTED")
        self.assertNotIn("GlobalTripPlanningAgent", payload["agent_trace"])
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertNotIn("trip_plan", payload["graph"]["path"])
        self.assertNotIn(
            "route.plan",
            [item["tool_name"] for item in payload["runtime_trace"]],
        )
        self.assertNotIn(
            "ecology.snapshot",
            [item["tool_name"] for item in payload["runtime_trace"]],
        )

    def test_online_personalize_payload_does_not_create_route_summary(self):
        payload = run_command("我的偏好", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "PERSONALIZE")
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertNotIn("GlobalTripPlanningAgent", payload["agent_trace"])
        self.assertNotIn("ecology.snapshot", [item["tool_name"] for item in payload["runtime_trace"]])

    def test_dangerous_command_payload_is_blocked(self):
        payload = run_command("关闭AEB", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["request"]["safety"], "DANGEROUS")
        self.assertEqual(payload["result"]["status"], "BLOCKED")
        self.assertIn("GlobalSafetyDispatchAgent", payload["agent_trace"])

    def test_highway_speed_request_payload_requires_driver_confirmation(self):
        payload = run_command("加速到100km/h", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "CAR_CONTROL")
        self.assertEqual(payload["request"]["safety"], "DANGEROUS")
        self.assertEqual(payload["result"]["status"], "NEEDS_DRIVER_CONFIRMATION")
        self.assertIn("驾驶员确认", payload["result"]["output"])
        self.assertIn("DriverConfirmation", payload["agent_trace"])

    def test_vehicle_state_update_changes_speed_safety_context(self):
        update_vehicle_state(
            {
                "road_type": "URBAN",
                "speed_limit_kmh": 60,
                "speed_kmh": 40,
                "driver_assist_mode": "MANUAL",
            }
        )

        payload = run_command("加速到100km/h", network="ONLINE")

        self.assertEqual(payload["vehicle_state"]["road_type"], "URBAN")
        self.assertEqual(payload["vehicle_state"]["speed_limit_kmh"], 60)
        self.assertEqual(payload["result"]["status"], "BLOCKED")
        self.assertIn("限速", payload["result"]["output"])

    def test_vehicle_state_update_triggers_low_battery_auto_event(self):
        payload = update_vehicle_state({"battery_percent": 18})

        self.assertEqual(payload["vehicle_state"]["battery_percent"], 18)
        self.assertEqual(payload["auto_events"][0]["type"], "BATTERY_LOW")
        self.assertEqual(payload["auto_events"][0]["trigger"], "AUTO")

    def test_vehicle_state_update_triggers_speed_over_limit_event(self):
        payload = update_vehicle_state({"speed_kmh": 150, "speed_limit_kmh": 120})

        self.assertEqual(payload["vehicle_state"]["speed_kmh"], 150)
        self.assertEqual(payload["vehicle_state"]["speed_limit_kmh"], 120)
        self.assertEqual(payload["vehicle_state"]["safety_state"], "超速预警")
        self.assertEqual(payload["auto_events"][0]["type"], "SPEED_OVER_LIMIT")
        self.assertEqual(payload["auto_events"][0]["severity"], "WARNING")

    def test_vehicle_events_payload_is_independent_from_command_execution(self):
        update_vehicle_state({"battery_percent": 8})

        payload = get_vehicle_events_payload()

        self.assertEqual(payload["vehicle_state"]["battery_percent"], 8)
        self.assertEqual(payload["events"][0]["type"], "BATTERY_CRITICAL")
        self.assertEqual(payload["events"][0]["severity"], "CRITICAL")
        self.assertEqual(payload["events"][0]["trigger"], "AUTO")

    def test_critical_battery_navigation_payload_requires_charge_confirmation(self):
        update_vehicle_state({"battery_percent": 8})

        payload = run_command("导航去蔚来中心", network="ONLINE")

        self.assertEqual(payload["result"]["status"], "NEEDS_CHARGE_CONFIRMATION")
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertIn("EnergyPolicyAgent", payload["agent_trace"])

    def test_critical_battery_comfort_control_trace_points_to_energy_policy(self):
        update_vehicle_state({"battery_percent": 4})

        payload = run_command("\u6253\u5f00\u5ea7\u6905\u52a0\u70ed", network="OFFLINE")

        self.assertEqual(payload["result"]["status"], "BLOCKED")
        self.assertIn("EnergyPolicyAgent", payload["agent_trace"])
        self.assertNotIn("SafetyBlock", payload["agent_trace"])

    def test_info_query_payload_is_normal_non_route_result(self):
        payload = run_command("AEB是什么", network="ONLINE")

        self.assertEqual(payload["request"]["command_type"], "INFO_QUERY")
        self.assertEqual(payload["request"]["safety"], "SAFE")
        self.assertEqual(payload["result"]["status"], "EXECUTED")
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertNotIn("GlobalTripPlanningAgent", payload["agent_trace"])
        self.assertNotIn(
            "trip.plan",
            [item["tool_name"] for item in payload["runtime_trace"]],
        )

    def test_fuzzy_navigation_returns_structured_clarification(self):
        payload = run_command(
            "导航去高老庄",
            user_id=f"user_{uuid.uuid4().hex}",
            network="ONLINE",
        )

        self.assertEqual(payload["request"]["command_type"], "NAVIGATION")
        self.assertEqual(payload["result"]["status"], "NEEDS_CLARIFICATION")
        self.assertEqual(payload["result"]["clarification"]["type"], "destination")
        self.assertEqual(payload["result"]["clarification"]["query"], "高老庄")
        self.assertEqual(payload["route_summary"], {})
        self.assertFalse(payload["charge_stations"])
        self.assertIn("DestinationClarification", payload["agent_trace"])
        self.assertNotIn("GlobalTripPlanningAgent", payload["agent_trace"])
        self.assertFalse(
            any(item["stage"] == "云端路线规划" for item in payload["rag_context"])
        )
        self.assertEqual(payload["runtime_trace"], [])

    def test_pending_destination_confirmation_continues_original_task(self):
        user_id = f"user_{uuid.uuid4().hex}"
        first = run_command("导航去北京", user_id=user_id, network="ONLINE")

        self.assertEqual(first["result"]["status"], "NEEDS_CLARIFICATION")
        self.assertEqual(first["result"]["pending_action"]["type"], "destination_clarification")

        second = confirm_pending_action(
            first["result"]["pending_action"]["id"],
            user_id=user_id,
            selection={"gps": "121.497253,31.238235", "name": "上海外滩"},
        )

        self.assertEqual(second["result"]["status"], "EXECUTED")
        self.assertEqual(second["request"]["content"], "导航去121.497253,31.238235")
        self.assertEqual(second["result"]["pending_action"], {})


if __name__ == "__main__":
    unittest.main()
