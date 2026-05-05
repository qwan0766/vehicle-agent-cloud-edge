import unittest

from runtime.agent_runtime import AgentRuntime
from runtime.tool_registry import ToolRegistry


class TestAgentRuntime(unittest.TestCase):
    def test_runtime_calls_registered_tool_and_records_trace(self):
        registry = ToolRegistry()
        registry.register("math.double", lambda payload: payload["value"] * 2)
        runtime = AgentRuntime()

        result = runtime.call_tool(registry, "math.double", {"value": 4})

        self.assertEqual(result, 8)
        trace = runtime.snapshot()
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["tool_name"], "math.double")
        self.assertEqual(trace[0]["input"], {"value": 4})
        self.assertEqual(trace[0]["output"], 8)
        self.assertGreaterEqual(trace[0]["duration_ms"], 0)

    def test_registry_reports_registered_tool_names(self):
        registry = ToolRegistry()
        registry.register("profile.lookup", lambda payload: payload)
        registry.register("route.plan", lambda payload: payload)

        self.assertEqual(registry.list_names(), ["profile.lookup", "route.plan"])


if __name__ == "__main__":
    unittest.main()
