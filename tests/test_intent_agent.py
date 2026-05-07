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

    def test_recognizes_similar_navigation_expression_with_retrieval(self):
        agent = LocalIntentAgent()
        self.assertEqual(agent.recognize("帮我导航到蔚来中心"), CommandType.NAVIGATION)

    def test_structured_analysis_keeps_city_qualified_destination_slots(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("导航去北京的蔚来中心")

        self.assertEqual(frame.command_type, CommandType.NAVIGATION)
        self.assertEqual(frame.slots["raw_destination"], "北京的蔚来中心")
        self.assertEqual(frame.slots["destination_query"], "北京蔚来中心")
        self.assertGreaterEqual(frame.confidence, 0.9)

    def test_safety_keyword_question_is_not_car_control_intent(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("AEB是什么")

        self.assertEqual(frame.command_type, CommandType.UNKNOWN)
        self.assertIn("AEB", frame.evidence["keyword_hits"])
        self.assertEqual(agent.recognize("AEB是什么"), CommandType.UNKNOWN)

    def test_media_request_with_motion_keyword_is_unknown_not_car_control(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("播放一首加速感很强的歌")

        self.assertEqual(frame.command_type, CommandType.UNKNOWN)
        self.assertIn("加速", frame.evidence["keyword_hits"])

    def test_negated_navigation_keyword_does_not_start_navigation(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("我不想导航去蔚来中心，只是问问怎么取消导航")

        self.assertEqual(frame.command_type, CommandType.UNKNOWN)
        self.assertLess(frame.confidence, 0.5)

    def test_car_control_analysis_extracts_temperature_slot(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("把空调温度调到23度")

        self.assertEqual(frame.command_type, CommandType.CAR_CONTROL)
        self.assertEqual(frame.slots["temperature_c"], 23)
        self.assertIn("温度", frame.evidence["keyword_hits"])

    def test_charge_question_is_charge_plan_not_raw_keyword_shortcut(self):
        agent = LocalIntentAgent()

        frame = agent.analyze("现在电量低怎么办")

        self.assertEqual(frame.command_type, CommandType.CHARGE_PLAN)
        self.assertIn("电量低", frame.evidence["keyword_hits"])


if __name__ == "__main__":
    unittest.main()
