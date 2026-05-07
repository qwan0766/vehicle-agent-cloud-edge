import unittest

from core.constants import CommandType, ExecutionStatus, NetworkStatus, RoadType, SafetyLevel
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

    def test_highway_acceleration_request_requires_driver_confirmation(self):
        decision = SafetyPolicy().evaluate(
            command_type=CommandType.CAR_CONTROL,
            safety=SafetyLevel.DANGEROUS,
            network=NetworkStatus.ONLINE,
            content="加速到100km/h",
            vehicle_state={
                "road_type": RoadType.HIGHWAY.value,
                "speed_limit_kmh": 120,
                "speed_kmh": 80,
            },
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, ExecutionStatus.NEEDS_DRIVER_CONFIRMATION)
        self.assertIn("驾驶员确认", decision.reason)

    def test_city_acceleration_request_stays_blocked(self):
        decision = SafetyPolicy().evaluate(
            command_type=CommandType.CAR_CONTROL,
            safety=SafetyLevel.DANGEROUS,
            network=NetworkStatus.ONLINE,
            content="加速到100km/h",
            vehicle_state={
                "road_type": RoadType.URBAN.value,
                "speed_limit_kmh": 60,
                "speed_kmh": 40,
            },
        )

        self.assertFalse(decision.allowed)
        self.assertIn("限速", decision.reason)


if __name__ == "__main__":
    unittest.main()
