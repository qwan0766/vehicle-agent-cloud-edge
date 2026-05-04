import unittest

from agents.vehicle.local_intent_agent import LocalIntentAgent
from core.constants import CommandType


class TestLocalIntentAgent(unittest.TestCase):
    def test_recognizes_navigation_intent(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("导航去蔚来中心"), CommandType.NAVIGATION)

    def test_recognizes_charge_plan_intent(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("电量低"), CommandType.CHARGE_PLAN)

    def test_unknown_intent_is_unknown(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("播放一首歌"), CommandType.UNKNOWN)

    def test_dangerous_motion_command_is_still_car_control_intent(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("加速到100km/h"), CommandType.CAR_CONTROL)


if __name__ == "__main__":
    unittest.main()
