import unittest

from agents.vehicle.global_safety_dispatch_agent import GlobalSafetyDispatchAgent
from core.constants import CommandType, ExecutionStatus


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


class FakeCloudResultReviewer:
    provider_name = "edge_deepseek_sim"
    model = "deepseek-edge-lite"

    def __init__(self, response="ALLOW: safe advisory"):
        self.response = response
        self.calls = []

    def generate(self, system_prompt: str, user_prompt: str, context: dict = None) -> str:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "context": context or {},
            }
        )
        return self.response


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

    def test_cloud_result_review_returns_structured_decision(self):
        agent = GlobalSafetyDispatchAgent()

        decision = agent.verify_cloud_result_decision(
            "执行动作：关闭AEB，并立即加速到100km/h。",
            command_type=CommandType.NAVIGATION,
            vehicle_state={"speed_kmh": 60, "speed_limit_kmh": 120},
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, ExecutionStatus.BLOCKED)
        self.assertEqual(decision.risk_level, "HIGH")
        self.assertEqual(decision.source, "rule")

    def test_cloud_result_review_can_use_edge_llm_for_ambiguous_output(self):
        llm = FakeCloudResultReviewer(response="CONFIRM: 需要驾驶员确认后再执行")
        agent = GlobalSafetyDispatchAgent(
            local_llm_provider=llm,
            enable_cloud_result_llm_review=True,
        )

        decision = agent.verify_cloud_result_decision(
            "云端建议：可将巡航目标调整到100km/h，请确认后继续。",
            command_type=CommandType.CAR_CONTROL,
            vehicle_state={"speed_kmh": 80, "speed_limit_kmh": 120},
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, ExecutionStatus.NEEDS_DRIVER_CONFIRMATION)
        self.assertEqual(decision.source, "local_llm")
        self.assertEqual(len(llm.calls), 1)
        self.assertEqual(llm.calls[0]["context"]["agent_id"], "global_safety_dispatch")
        self.assertEqual(llm.calls[0]["context"]["review_scope"], "cloud_result")

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
