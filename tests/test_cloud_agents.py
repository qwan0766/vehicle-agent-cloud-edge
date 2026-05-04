import unittest

from agents.cloud.cloud_schedule_agent import CloudScheduleAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from core.constants import CommandType, NetworkStatus, SafetyLevel
from core.message import Message


class TestCloudAgents(unittest.TestCase):
    def test_profile_agent_returns_default_for_unknown_user(self):
        agent = CloudUserProfileAgent()
        self.assertIn("默认偏好", agent.get_profile("missing_user"))

    def test_profile_agent_retrieves_user_route_preference(self):
        agent = CloudUserProfileAgent()
        results = agent.retrieve_context("user_001", "导航去蔚来中心")

        self.assertTrue(results)
        self.assertIn("路线偏好高速", results[0].document.text)

    def test_cloud_schedule_combines_profile_ecology_and_route(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去蔚来中心",
            network=NetworkStatus.ONLINE,
        )
        result = CloudScheduleAgent().dispatch(msg)

        self.assertIn("用户偏好", result)
        self.assertIn("外部生态数据", result)
        self.assertIn("RAG路线结果", result)
        self.assertIn("结合用户路线偏好高速", result)

    def test_route_plan_uses_retrieved_charge_context(self):
        from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent

        result = CloudRoutePlanAgent().plan("电量低，需要补能")

        self.assertIn("电量低于20%建议前往换电站", result)


if __name__ == "__main__":
    unittest.main()
