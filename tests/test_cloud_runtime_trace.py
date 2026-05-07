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
        self.assertEqual(
            [item["tool_name"] for item in trace],
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
        self.assertEqual(trace[0]["input"]["user_id"], "user_001")
        self.assertIn("用户偏好", trace[0]["output"])
        self.assertIn("向量知识库召回", trace[1]["output"])
        self.assertIn("RAG路线结果", trace[4]["output"])
        self.assertEqual(trace[5]["output"]["destination_name"], "蔚来中心")
        self.assertEqual(trace[6]["output"]["provider"], "offline_map")
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
