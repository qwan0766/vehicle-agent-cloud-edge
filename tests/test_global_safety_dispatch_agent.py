import unittest

from agents.vehicle.global_safety_dispatch_agent import GlobalSafetyDispatchAgent


class TestGlobalSafetyDispatchAgent(unittest.TestCase):
    def test_cloud_result_allows_non_actionable_safety_mentions(self):
        agent = GlobalSafetyDispatchAgent()

        allowed, reason = agent.verify_cloud_result(
            "最终执行说明：已将温度设置为24度。安全提示：请遵守交通规则，注意限速、制动距离和AEB状态。"
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


if __name__ == "__main__":
    unittest.main()
