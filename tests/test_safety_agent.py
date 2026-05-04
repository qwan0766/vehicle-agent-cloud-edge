import unittest

from agents.vehicle.safety_agent import SafetyAgent
from core.constants import SafetyLevel


class TestSafetyAgent(unittest.TestCase):
    def test_blocks_dangerous_acceleration_command(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("加速到100km/h"), SafetyLevel.DANGEROUS)

    def test_allows_safe_comfort_command(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("打开座椅加热"), SafetyLevel.SAFE)


if __name__ == "__main__":
    unittest.main()
