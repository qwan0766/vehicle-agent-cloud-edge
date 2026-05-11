import unittest

from core.trace import TraceEvent, normalize_trace_event
from runtime.agent_runtime import AgentRuntime


class TestTraceSchema(unittest.TestCase):
    def test_trace_event_keeps_legacy_fields_and_adds_standard_fields(self):
        event = TraceEvent(
            tool_name="provider.map.route",
            input={"destination": "121.50,31.25"},
            output={"distance_km": 4},
            duration_ms=12.5,
            request_id="req-1",
            agent_id="GlobalTripPlanningAgent",
            phase="tool",
            provider="amap_route",
        )

        payload = event.to_dict()

        self.assertEqual(payload["tool_name"], "provider.map.route")
        self.assertEqual(payload["input"], {"destination": "121.50,31.25"})
        self.assertEqual(payload["output"], {"distance_km": 4})
        self.assertEqual(payload["duration_ms"], 12.5)
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["agent_id"], "GlobalTripPlanningAgent")
        self.assertEqual(payload["phase"], "tool")
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["provider"], "amap_route")
        self.assertEqual(payload["error_code"], "")

    def test_normalize_trace_event_accepts_legacy_dict(self):
        event = normalize_trace_event(
            {
                "tool_name": "knowledge.retrieve",
                "input": {"content": "nav"},
                "output": "knowledge",
                "duration_ms": 0.1,
            },
            agent_id="VectorKnowledgeAgent",
        )

        self.assertEqual(event.tool_name, "knowledge.retrieve")
        self.assertEqual(event.agent_id, "VectorKnowledgeAgent")
        self.assertEqual(event.status, "OK")

    def test_runtime_snapshot_returns_standardized_dicts(self):
        runtime = AgentRuntime(request_id="req-2")

        runtime.append_trace(
            tool_name="user_profile.lookup",
            input={"user_id": "user_001"},
            output="profile",
            duration_ms=0.2,
            agent_id="UserProfileAgent",
        )

        trace = runtime.snapshot()

        self.assertEqual(trace[0]["request_id"], "req-2")
        self.assertEqual(trace[0]["agent_id"], "UserProfileAgent")
        self.assertEqual(trace[0]["status"], "OK")
        self.assertIn("metadata", trace[0])


if __name__ == "__main__":
    unittest.main()
