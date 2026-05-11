import unittest

from core.agent_schema import (
    AgentTraceFrame,
    ExecutionResultFrame,
    ProviderResultFrame,
    VehicleStateFrame,
)
from core.constants import CommandType, ExecutionStatus, NetworkStatus, SafetyLevel
from core.message import Message
from core.trace import TraceEvent
from core.vehicle_core_service import ExecutionResult
from data.vehicle_state import DEFAULT_VEHICLE_STATE


class TestAgentSchema(unittest.TestCase):
    def test_message_converts_to_intent_frame_with_enum_values(self):
        message = Message.create(
            user_id="user_001",
            command_type=CommandType.NAVIGATION,
            safety=SafetyLevel.SAFE,
            content="导航去蔚来中心",
            network=NetworkStatus.ONLINE,
        )

        frame = message.to_intent_frame(raw_input="去蔚来中心", confidence=0.92)

        self.assertEqual(frame.request_id, message.request_id)
        self.assertEqual(frame.raw_input, "去蔚来中心")
        self.assertEqual(frame.normalized_input, "导航去蔚来中心")
        self.assertEqual(frame.command_type, CommandType.NAVIGATION)
        self.assertEqual(frame.confidence, 0.92)
        self.assertEqual(
            frame.to_dict()["command_type"],
            "NAVIGATION",
        )
        self.assertEqual(frame.to_dict()["network"], "ONLINE")

    def test_vehicle_state_frame_accepts_vehicle_state_and_payload(self):
        from_state = VehicleStateFrame.from_vehicle_state(DEFAULT_VEHICLE_STATE)
        from_payload = VehicleStateFrame.from_payload(
            {
                "speed_kmh": 88,
                "battery_percent": 42,
                "network": "OFFLINE",
                "gps": "121.48,31.23",
                "road_type": "URBAN",
                "speed_limit_kmh": 80,
                "driver_assist_mode": "MANUAL",
                "vehicle_ready": False,
                "lane_confidence": 0.5,
            }
        )

        self.assertEqual(from_state.to_dict()["road_type"], "HIGHWAY")
        self.assertEqual(from_payload.speed_kmh, 88)
        self.assertEqual(from_payload.to_dict()["network"], "OFFLINE")
        self.assertFalse(from_payload.vehicle_ready)

    def test_provider_result_frame_normalizes_trace_event(self):
        trace = TraceEvent(
            tool_name="provider.map.route",
            output={"distance_km": 4},
            duration_ms=12.5,
            request_id="req-1",
            agent_id="GlobalTripPlanningAgent",
            provider="amap_route",
            status="OK",
            metadata={"capability": "route"},
        )

        frame = ProviderResultFrame.from_trace_event(trace)

        self.assertEqual(frame.request_id, "req-1")
        self.assertEqual(frame.provider, "amap_route")
        self.assertEqual(frame.capability, "route")
        self.assertEqual(frame.payload, {"distance_km": 4})
        self.assertEqual(frame.to_dict()["latency_ms"], 12.5)

    def test_agent_trace_frame_groups_outputs_by_agent(self):
        provider = ProviderResultFrame(
            request_id="req-1",
            agent_id="ExternalEcologyAgent",
            provider="open_meteo",
            capability="weather",
            payload={"temperature": 18},
        )

        frame = AgentTraceFrame(
            request_id="req-1",
            agent_id="ExternalEcologyAgent",
            scope="cloud",
            description="聚合天气和补能生态数据。",
            outputs=[provider],
        )

        rendered = frame.to_dict()

        self.assertEqual(rendered["scope"], "cloud")
        self.assertEqual(rendered["outputs"][0]["provider"], "open_meteo")

    def test_execution_result_frame_converts_existing_result(self):
        message = Message.create(
            user_id="user_001",
            command_type=CommandType.CAR_CONTROL,
            safety=SafetyLevel.SAFE,
            content="打开座椅加热",
            network=NetworkStatus.OFFLINE,
        )
        result = ExecutionResult(
            status=ExecutionStatus.FALLBACK,
            output="车控执行成功",
            message=message,
            trace=[
                {
                    "tool_name": "local.control",
                    "output": "ok",
                    "duration_ms": 1,
                }
            ],
            feedback={"recorded": True},
        )

        frame = ExecutionResultFrame.from_result(result)

        self.assertEqual(frame.status, ExecutionStatus.FALLBACK)
        self.assertEqual(frame.intent.command_type, CommandType.CAR_CONTROL)
        self.assertEqual(frame.trace[0].payload, "ok")
        self.assertEqual(frame.to_dict()["status"], "FALLBACK")
        self.assertEqual(frame.to_dict()["intent"]["content"], "打开座椅加热")


if __name__ == "__main__":
    unittest.main()
