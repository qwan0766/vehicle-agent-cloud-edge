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

    def test_result_rendering_updates_local_context_panel(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("localContextSummary", script)
        self.assertIn("localContextProvider", script)
        self.assertIn("localContextModel", script)
        self.assertIn("localContextPrompt", script)
        self.assertIn("estimated_prompt_tokens", script)
        self.assertIn("prompt_budget_tokens", script)
        self.assertIn("max_output_tokens", script)
        self.assertIn("renderLocalContext", script)
        self.assertIn("payload.local_context", script)

    def test_result_rendering_updates_graph_path(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("graphMode", script)
        self.assertIn("graphPath", script)
        self.assertIn("renderGraphPath", script)
        self.assertIn("payload.graph", script)

    def test_result_rendering_supports_destination_clarification(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("renderClarification", script)
        self.assertIn('result.status === "NEEDS_CLARIFICATION"', script)
        self.assertIn("clarification-suggestions", script)
        self.assertIn("nodes.commandInput.value = suggestion", script)
        self.assertIn("nodes.commandInput.focus()", script)

    def test_clarification_rendering_supports_destination_candidates(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("clarification-candidates", script)
        self.assertIn("candidate.confidence", script)
        self.assertIn("candidate.source", script)
        self.assertIn("nodes.commandInput.value = candidate.name", script)


if __name__ == "__main__":
    unittest.main()
