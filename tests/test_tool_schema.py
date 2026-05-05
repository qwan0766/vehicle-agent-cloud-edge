import unittest

from runtime.tool_registry import ToolRegistry
from runtime.tool_schema import FieldSpec, ToolSpec, ToolValidationError


class TestToolSchema(unittest.TestCase):
    def test_registry_validates_tool_input_and_output(self):
        registry = ToolRegistry()
        registry.register(
            "route.plan",
            lambda payload: {"summary": f"route for {payload['content']}"},
            spec=ToolSpec(
                input_fields=[FieldSpec("content", str)],
                output_fields=[FieldSpec("summary", str)],
            ),
        )

        result = registry.call("route.plan", {"content": "导航去蔚来中心"})

        self.assertEqual(result["summary"], "route for 导航去蔚来中心")

    def test_registry_rejects_missing_required_input(self):
        registry = ToolRegistry()
        registry.register(
            "weather.snapshot",
            lambda payload: {"summary": "天气晴"},
            spec=ToolSpec(input_fields=[FieldSpec("gps", str)]),
        )

        with self.assertRaises(ToolValidationError):
            registry.call("weather.snapshot", {})

    def test_registry_rejects_wrong_output_type(self):
        registry = ToolRegistry()
        registry.register(
            "charge.nearby",
            lambda payload: {"count": "2"},
            spec=ToolSpec(output_fields=[FieldSpec("count", int)]),
        )

        with self.assertRaises(ToolValidationError):
            registry.call("charge.nearby", {})


if __name__ == "__main__":
    unittest.main()
