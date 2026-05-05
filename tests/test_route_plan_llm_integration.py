import unittest

from agents.cloud.cloud_route_plan_agent import CloudRoutePlanAgent
from llm.mock_llm_client import MockLLMClient
from providers.offline_map_provider import OfflineMapProvider


class TestRoutePlanLLMIntegration(unittest.TestCase):
    def test_route_agent_uses_map_provider_and_llm_decision(self):
        agent = CloudRoutePlanAgent(
            llm_client=MockLLMClient(),
            map_provider=OfflineMapProvider(),
        )

        result = agent.plan("导航去蔚来中心", route_preference="高速")

        self.assertIn("RAG路线结果", result)
        self.assertIn("LLM决策", result)
        self.assertIn("高速", result)
        self.assertIn("预计", result)


if __name__ == "__main__":
    unittest.main()
