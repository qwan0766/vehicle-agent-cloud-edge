import unittest

from core.constants import ExecutionStatus, NetworkStatus
from core.vehicle_core_service import VehicleCoreService


class FakeCloudAgent:
    def dispatch(self, msg):
        return "用户偏好：温度24℃ | RAG路线结果：导航去蔚来中心，推荐高速优先"

    def get_last_trace(self):
        return [{"tool_name": "trip.plan", "input": {}, "output": "RAG路线结果", "duration_ms": 0}]

    def get_last_graph(self):
        return {"mode": "lightweight", "path": ["profile", "trip_plan", "decision"]}


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
        result = service.run("加速到100km/h", network=NetworkStatus.ONLINE)

        self.assertEqual(result.status, ExecutionStatus.BLOCKED)
        self.assertIn("危险指令", result.output)


if __name__ == "__main__":
    unittest.main()
