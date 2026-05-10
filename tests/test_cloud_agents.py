import unittest

from agents.cloud.cloud_schedule_agent import CloudScheduleAgent
from agents.cloud.cloud_user_profile_agent import CloudUserProfileAgent
from core.constants import CommandType, NetworkStatus, SafetyLevel
from core.message import Message
from feedback.preference_store import PreferenceStore
from feedback.preference_updater import PreferenceUpdate
from pathlib import Path
import uuid


class TestCloudAgents(unittest.TestCase):
    def test_profile_agent_returns_default_for_unknown_user(self):
        agent = CloudUserProfileAgent()
        self.assertIn("默认偏好", agent.get_profile("missing_user"))

    def test_profile_agent_retrieves_user_route_preference(self):
        agent = CloudUserProfileAgent()
        results = agent.retrieve_context("user_001", "导航去蔚来中心")

        self.assertTrue(results)
        self.assertIn("路线偏好高速", results[0].document.text)

    def test_profile_agent_uses_dynamic_preference_state(self):
        path = Path(".test_runtime") / f"profile_state_{uuid.uuid4().hex}.json"
        store = PreferenceStore(path)
        store.apply(
            PreferenceUpdate(
                user_id="user_002",
                preference_key="route_preference_highway",
                delta=2,
                description="路线偏好高速 +2",
                timestamp="2026-05-05T00:00:00",
            )
        )
        agent = CloudUserProfileAgent(preference_store=store)

        self.assertEqual(agent.get_route_preference("user_002", "导航去蔚来中心"), "高速")

    def test_cloud_schedule_combines_profile_ecology_and_route(self):
        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去蔚来中心",
            network=NetworkStatus.ONLINE,
        )
        agent = CloudScheduleAgent()
        result = agent.dispatch(msg)

        self.assertIn("RAG路线结果", result)
        self.assertIn("结合用户路线偏好高速", result)
        trace_tools = [item["tool_name"] for item in agent.get_last_trace()]
        self.assertIn("user_profile.lookup", trace_tools)
        self.assertIn("ecology.snapshot", trace_tools)

    def test_route_plan_uses_retrieved_charge_context(self):
        from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent

        result = CloudRoutePlanAgent().plan("电量低，需要补能")

        self.assertIn("电量低于20%建议前往换电站", result)


    def test_dispatch_result_does_not_repeat_route_plan_and_decision(self):
        class EchoDecisionLLM:
            provider_name = "fake_llm"

            def generate(self, system_prompt, user_prompt, context=None):
                return context["task_context"] + "。请确认是否开始导航。"

        msg = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去121.486754,31.186881",
            network=NetworkStatus.ONLINE,
        )
        result = CloudScheduleAgent(llm_client=EchoDecisionLLM()).dispatch(msg)

        self.assertEqual(result.count("RAG路线结果"), 1)
        self.assertNotIn("云端决策", result)


if __name__ == "__main__":
    unittest.main()
