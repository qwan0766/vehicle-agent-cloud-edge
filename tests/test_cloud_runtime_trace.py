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
                "user_profile.route_preference",
                "ecology.snapshot",
                "route.plan",
            ],
        )
        self.assertEqual(trace[0]["input"]["user_id"], "user_001")
        self.assertIn("用户偏好", trace[0]["output"])
        self.assertIn("RAG路线结果", trace[-1]["output"])


if __name__ == "__main__":
    unittest.main()
