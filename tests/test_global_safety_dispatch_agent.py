import unittest

from agents.vehicle.global_safety_dispatch_agent import GlobalSafetyDispatchAgent
from core.constants import CommandType


class FakeSafetyExplainer:
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
        return "安全拦截说明：AEB 属于主动安全能力，不能通过语音关闭。"


class TestGlobalSafetyDispatchAgent(unittest.TestCase):
    def test_cloud_result_allows_non_actionable_safety_mentions(self):
        agent = GlobalSafetyDispatchAgent()

        allowed, reason = agent.verify_cloud_result(
            "最终执行说明：已将温度设置为24度。安全提示：请遵守交通规则，注意限速、制动距离和AEB状态。"
        )

        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_cloud_result_allows_info_query_explanation_about_emergency_braking(self):
        agent = GlobalSafetyDispatchAgent()

        allowed, reason = agent.verify_cloud_result(
            "信息查询上下文：AEB 是自动紧急制动功能说明，本次不会执行车控动作。"
        )

        self.assertTrue(allowed)
        self.assertEqual(reason, "")

    def test_cloud_result_blocks_actionable_dangerous_control(self):
        agent = GlobalSafetyDispatchAgent()

        allowed, reason = agent.verify_cloud_result(
            "执行动作：关闭AEB，并立即加速到100km/h。"
        )

        self.assertFalse(allowed)
        self.assertIn("危险控制词", reason)

    def test_optional_edge_llm_explains_blocked_local_command(self):
        llm = FakeSafetyExplainer()
        agent = GlobalSafetyDispatchAgent(
            local_llm_provider=llm,
            enable_llm_explanations=True,
        )

        explanation = agent.explain_blocked_command(
            content="关闭AEB",
            command_type=CommandType.CAR_CONTROL,
            policy_reason="危险指令，已拦截！",
        )

        self.assertIn("安全拦截说明", explanation)
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(llm.calls[0]["context"]["agent_id"], "global_safety_dispatch")
        self.assertEqual(llm.calls[0]["context"]["command_type"], "CAR_CONTROL")

    def test_llm_explanation_failure_keeps_policy_reason(self):
        class BrokenExplainer:
            def generate(self, system_prompt: str, user_prompt: str, context: dict = None):
                raise RuntimeError("provider down")

        agent = GlobalSafetyDispatchAgent(
            local_llm_provider=BrokenExplainer(),
            enable_llm_explanations=True,
        )

        explanation = agent.explain_blocked_command(
            content="关闭AEB",
            command_type=CommandType.CAR_CONTROL,
            policy_reason="危险指令，已拦截！",
        )

        self.assertEqual(explanation, "危险指令，已拦截！")


if __name__ == "__main__":
    unittest.main()
