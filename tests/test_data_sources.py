import unittest

from core.constants import CommandType
from data.knowledge_base import (
    DANGEROUS_KEYWORDS,
    INTENT_KNOWLEDGE,
    ROUTE_KNOWLEDGE,
)
from data.user_profiles import DEFAULT_PROFILE, USER_PROFILES
from data.vehicle_state import DEFAULT_VEHICLE_STATE


class TestDataSources(unittest.TestCase):
    def test_builtin_intent_knowledge_contains_required_examples(self):
        self.assertEqual(INTENT_KNOWLEDGE["导航去蔚来中心"], CommandType.NAVIGATION)
        self.assertEqual(INTENT_KNOWLEDGE["电量低"], CommandType.CHARGE_PLAN)
        self.assertEqual(INTENT_KNOWLEDGE["我的偏好"], CommandType.PERSONALIZE)

    def test_safety_and_profile_data_are_available(self):
        self.assertIn("加速", DANGEROUS_KEYWORDS)
        self.assertIn("长途优先高速路线", ROUTE_KNOWLEDGE)
        self.assertIn("user_001", USER_PROFILES)
        self.assertIn("温度24", DEFAULT_PROFILE)
        self.assertEqual(DEFAULT_VEHICLE_STATE.speed_kmh, 60)


if __name__ == "__main__":
    unittest.main()
