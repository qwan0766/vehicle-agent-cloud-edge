import unittest

from core.constants import CommandType, NetworkStatus, SafetyLevel
from safety.safety_policy import SafetyPolicy


class TestSafetyPolicy(unittest.TestCase):
    def test_blocks_unknown_command(self):
        decision = SafetyPolicy().evaluate(
            command_type=CommandType.UNKNOWN,
            safety=SafetyLevel.SAFE,
            network=NetworkStatus.ONLINE,
            content="播放一首歌",
        )

        self.assertFalse(decision.allowed)
        self.assertIn("未知指令", decision.reason)

    def test_blocks_dangerous_command(self):
        decision = SafetyPolicy().evaluate(
            command_type=CommandType.CAR_CONTROL,
            safety=SafetyLevel.DANGEROUS,
            network=NetworkStatus.ONLINE,
            content="加速到100km/h",
        )

        self.assertFalse(decision.allowed)
        self.assertIn("危险指令", decision.reason)


if __name__ == "__main__":
    unittest.main()
