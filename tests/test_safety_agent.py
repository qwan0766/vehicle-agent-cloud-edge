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

    def test_allows_non_actionable_aeb_question(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("AEB是什么"), SafetyLevel.SAFE)

    def test_allows_non_actionable_motion_keyword_media_request(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("播放一首加速感很强的歌"), SafetyLevel.SAFE)

    def test_blocks_disabling_aeb(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("关闭AEB"), SafetyLevel.DANGEROUS)

    def test_blocks_actionable_steering_command(self):
        agent = SafetyAgent()
        self.assertEqual(agent.check("执行自动转向"), SafetyLevel.DANGEROUS)


if __name__ == "__main__":
    unittest.main()
