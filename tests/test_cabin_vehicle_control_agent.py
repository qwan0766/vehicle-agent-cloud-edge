import unittest

from agents.vehicle.cabin_vehicle_control_agent import CabinVehicleControlAgent
from core.constants import CommandType


class FakeControlExplainer:
    provider_name = "edge_deepseek_sim"
    model = "deepseek-edge-lite"

    def __init__(self):
        self.calls = []

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "context": context or {},
            }
        )
        return "座舱说明：已按本地车控规则执行，不调用云端路线规划。"


class TestCabinVehicleControlAgent(unittest.TestCase):
    def test_optional_edge_llm_adds_control_explanation_without_replacing_execution(self):
        llm = FakeControlExplainer()
        agent = CabinVehicleControlAgent(
            local_llm_provider=llm,
            enable_llm_explanations=True,
        )

        result = agent.execute(
            CommandType.CAR_CONTROL,
            "打开座椅加热",
            local_context={"agent_id": "local_intent", "summary": "previous"},
        )

        self.assertIn("车控执行成功", result)
        self.assertIn("座舱说明", result)
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(llm.calls[0]["context"]["agent_id"], "cabin_vehicle_control")
        self.assertEqual(llm.calls[0]["context"]["source_context_agent"], "local_intent")

    def test_control_explanation_failure_keeps_base_execution_result(self):
        class BrokenExplainer:
            def generate(self, system_prompt: str, user_prompt: str, context: dict = None):
                raise RuntimeError("provider down")

        agent = CabinVehicleControlAgent(
            local_llm_provider=BrokenExplainer(),
            enable_llm_explanations=True,
        )

        result = agent.execute(CommandType.CAR_CONTROL, "打开座椅加热")

        self.assertIn("车控执行成功", result)
        self.assertNotIn("provider down", result)


if __name__ == "__main__":
    unittest.main()
