import unittest

from providers.errors import ProviderUnavailableError
from runtime.agent_runtime import AgentRuntime
from runtime.tool_registry import ToolRegistry


class TestRuntimeErrorTrace(unittest.TestCase):
    def test_runtime_records_structured_error_trace_before_reraising(self):
        registry = ToolRegistry()

        def fail(_payload):
            raise ProviderUnavailableError(
                "Provider HTTP error: 503",
                provider="amap_route",
                operation="driving_route",
                code="HTTP_503",
            )

        registry.register("provider.map.route", fail)
        runtime = AgentRuntime(request_id="req-provider-error")

        with self.assertRaises(ProviderUnavailableError):
            runtime.call_tool(registry, "provider.map.route", {"destination": "121.50,31.25"})

        trace = runtime.snapshot()
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["request_id"], "req-provider-error")
        self.assertEqual(trace[0]["status"], "ERROR")
        self.assertEqual(trace[0]["provider"], "amap_route")
        self.assertEqual(trace[0]["error_code"], "HTTP_503")
        self.assertEqual(trace[0]["output"]["error_code"], "HTTP_503")
        self.assertTrue(trace[0]["output"]["retryable"])


if __name__ == "__main__":
    unittest.main()
