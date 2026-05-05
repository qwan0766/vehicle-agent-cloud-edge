import unittest
from pathlib import Path


class TestWebDemoFrontendLogic(unittest.TestCase):
    def test_run_command_ignores_stale_responses(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("requestSeq", script)
        self.assertIn("activeRequestId", script)
        self.assertIn("requestId !== state.activeRequestId", script)

    def test_blocked_result_has_dedicated_trace_mode(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn('result.status === "BLOCKED"', script)
        self.assertIn('"安全拦截"', script)


if __name__ == "__main__":
    unittest.main()
