import unittest

from agents.cloud.cloud_schedule_agent import CloudScheduleAgent
from core.constants import CommandType, NetworkStatus, SafetyLevel
from core.message import Message


class TestCloudRuntimeTrace(unittest.TestCase):
    def test_cloud_schedule_records_tool_level_trace(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去蔚来中心",
            network=NetworkStatus.ONLINE,
        )
        agent = CloudScheduleAgent()

        agent.dispatch(msg)

        trace = agent.get_last_trace()
        self.assertTrue(all(item["request_id"] == msg.request_id for item in trace))
        self.assertTrue(all(item["status"] == "OK" for item in trace))
        self.assertEqual(trace[0]["agent_id"], "UserProfileAgent")
        self.assertEqual(trace[1]["agent_id"], "VectorKnowledgeAgent")
        self.assertEqual(trace[3]["agent_id"], "ExternalEcologyAgent")
        self.assertEqual(trace[4]["agent_id"], "RouteProviderAgent")
        self.assertEqual(trace[6]["agent_id"], "GlobalTripPlanningAgent")
        self.assertEqual(trace[-1]["agent_id"], "GlobalDispatchAgent")
        self.assertEqual(
            [item["tool_name"] for item in trace],
            [
                "user_profile.lookup",
                "knowledge.retrieve",
                "user_profile.route_preference",
                "ecology.snapshot",
                "provider.geocode",
                "provider.map.route",
                "trip.plan",
                "decision.summarize",
            ],
        )
        self.assertEqual(trace[0]["input"]["user_id"], "user_001")
        self.assertIn("用户偏好", trace[0]["output"])
        self.assertNotIn("向量知识库召回", trace[1]["output"])
        self.assertIn("知识库", trace[1]["output"])
        ecology_output = trace[3]["output"]
        self.assertIsInstance(ecology_output, dict)
        self.assertIn("weather", ecology_output)
        self.assertIn("charge_stations", ecology_output)
        self.assertIn("temperature_c", ecology_output["weather"])
        self.assertIn("precipitation_mm", ecology_output["weather"])
        self.assertIn("source", ecology_output["weather"])
        self.assertIn("charge_source", ecology_output)
        self.assertEqual(trace[4]["output"]["destination_name"], "蔚来中心")
        self.assertEqual(trace[5]["output"]["provider"], "offline_map")
        self.assertIn("RAG路线结果", trace[6]["output"])
        self.assertIn("LLM决策", trace[-1]["output"])

    def test_cloud_schedule_skips_route_tools_for_car_control(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.CAR_CONTROL,
            safety=SafetyLevel.SAFE,
            content="温度调到24度",
            network=NetworkStatus.ONLINE,
        )
        agent = CloudScheduleAgent()

        result = agent.dispatch(msg)

        trace_names = [item["tool_name"] for item in agent.get_last_trace()]
        self.assertEqual(
            trace_names,
            [
                "user_profile.lookup",
                "knowledge.retrieve",
                "decision.summarize",
            ],
        )
        self.assertIn("座舱/车控上下文", result)
        self.assertNotIn("RAG路线结果", result)

    def test_cloud_schedule_skips_route_tools_for_personalize(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.PERSONALIZE,
            safety=SafetyLevel.SAFE,
            content="我的偏好",
            network=NetworkStatus.ONLINE,
        )
        agent = CloudScheduleAgent()

        result = agent.dispatch(msg)

        trace_names = [item["tool_name"] for item in agent.get_last_trace()]
        self.assertNotIn("trip.plan", trace_names)
        self.assertNotIn("provider.map.route", trace_names)
        self.assertIn("个性化上下文", result)


if __name__ == "__main__":
    unittest.main()
