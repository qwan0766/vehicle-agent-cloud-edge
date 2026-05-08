import unittest

from core.constants import CommandType, ExecutionStatus, NetworkStatus
from core.constants import RoadType
from data.vehicle_state import VehicleState
from core.vehicle_core_service import VehicleCoreService
from providers.destination_resolver import DestinationClarificationRequired


class FakeCloudAgent:
    def dispatch(self, msg):
        return "用户偏好：温度24℃ | RAG路线结果：导航去蔚来中心，推荐高速优先"

    def get_last_trace(self):
        return [{"tool_name": "trip.plan", "input": {}, "output": "RAG路线结果", "duration_ms": 0}]

    def get_last_graph(self):
        return {"mode": "lightweight", "path": ["profile", "trip_plan", "decision"]}


class FakeDestinationConfidenceAgent:
    def ensure_executable(self, content, **kwargs):
        raise DestinationClarificationRequired(
            "世博园",
            "destination_candidate_confirmation",
            suggestions=("请确认要去哪个世博园。",),
            candidates=[
                {
                    "name": "上海世博园",
                    "gps": "121.50,31.18",
                    "address": "上海市浦东新区",
                    "source": "fake_poi",
                    "confidence": 0.91,
                    "distance_km": None,
                    "reason": "provider_text_search",
                }
            ],
        )


class TestVehicleCoreService(unittest.TestCase):
    def test_online_navigation_goes_to_cloud(self):
        service = VehicleCoreService(cloud_agent=FakeCloudAgent())
        result = service.run("导航去蔚来中心", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.EXECUTED)
        self.assertIn("RAG路线结果", result.output)
        self.assertEqual(result.graph["mode"], "lightweight")

    def test_offline_car_control_uses_local_execution(self):
        service = VehicleCoreService()
        result = service.run("打开座椅加热", network=NetworkStatus.OFFLINE)

        self.assertEqual(result.status, ExecutionStatus.FALLBACK)
        self.assertIn("车控执行成功", result.output)

    def test_dangerous_command_is_blocked_before_execution(self):
        service = VehicleCoreService()
        result = service.run("关闭AEB", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.BLOCKED)
        self.assertIn("危险指令", result.output)

    def test_info_query_enters_online_execution_without_route_planning(self):
        service = VehicleCoreService(cloud_agent=FakeCloudAgent())

        result = service.run("AEB是什么", network=NetworkStatus.ONLINE)

        self.assertEqual(result.message.command_type, CommandType.INFO_QUERY)
        self.assertEqual(result.status, ExecutionStatus.EXECUTED)

    def test_highway_speed_request_requires_driver_confirmation_not_cloud_execution(self):
        service = VehicleCoreService(
            cloud_agent=FakeCloudAgent(),
            vehicle_state=VehicleState(
                speed_kmh=80,
                battery_percent=35,
                network=NetworkStatus.ONLINE,
                gps="121.48, 31.23",
                road_type=RoadType.HIGHWAY,
                speed_limit_kmh=120,
            ),
        )

        result = service.run("加速到100km/h", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.NEEDS_DRIVER_CONFIRMATION)
        self.assertIn("驾驶员确认", result.output)

    def test_online_navigation_candidate_confirmation_is_normal_status(self):
        service = VehicleCoreService(
            cloud_agent=FakeCloudAgent(),
            destination_confidence_agent=FakeDestinationConfidenceAgent(),
        )

        result = service.run("导航去世博园", network=NetworkStatus.ONLINE)

        self.assertEqual(result.message.command_type, CommandType.NAVIGATION)
        self.assertEqual(result.status, ExecutionStatus.NEEDS_CLARIFICATION)
        self.assertEqual(result.clarification["reason"], "destination_candidate_confirmation")
        self.assertEqual(result.clarification["candidates"][0]["name"], "上海世博园")

    def test_low_battery_navigation_appends_energy_advisory(self):
        service = VehicleCoreService(
            cloud_agent=FakeCloudAgent(),
            vehicle_state=VehicleState(
                speed_kmh=60,
                battery_percent=18,
                network=NetworkStatus.ONLINE,
                gps="121.48, 31.23",
                road_type=RoadType.HIGHWAY,
                speed_limit_kmh=120,
            ),
        )

        result = service.run("导航去蔚来中心", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.EXECUTED)
        self.assertIn("能源提示", result.output)
        self.assertIn("建议规划补能点", result.output)

    def test_critical_battery_navigation_requires_charge_confirmation_before_cloud(self):
        service = VehicleCoreService(
            cloud_agent=FakeCloudAgent(),
            vehicle_state=VehicleState(
                speed_kmh=60,
                battery_percent=8,
                network=NetworkStatus.ONLINE,
                gps="121.48, 31.23",
                road_type=RoadType.HIGHWAY,
                speed_limit_kmh=120,
            ),
        )

        result = service.run("导航去蔚来中心", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.NEEDS_CHARGE_CONFIRMATION)
        self.assertIn("电量严重不足", result.output)

    def test_critical_battery_blocks_seat_heat_control(self):
        service = VehicleCoreService(
            cloud_agent=FakeCloudAgent(),
            vehicle_state=VehicleState(
                speed_kmh=60,
                battery_percent=4,
                network=NetworkStatus.ONLINE,
                gps="121.48, 31.23",
                road_type=RoadType.HIGHWAY,
                speed_limit_kmh=120,
            ),
        )

        result = service.run("打开座椅加热", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.BLOCKED)
        self.assertIn("低电量", result.output)


if __name__ == "__main__":
    unittest.main()
