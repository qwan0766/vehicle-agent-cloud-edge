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
        self.assertIn("const confirmedTarget = candidate.gps || candidate.name", script)
        self.assertIn("runCommand();", script)

    def test_scenario_buttons_mark_manual_trigger_and_auto_events_render_separately(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("scenario.trigger", script)
        self.assertIn("手动演示", script)
        self.assertIn("renderAutoEvents", script)
        self.assertIn("自动触发", script)

    def test_frontend_updates_vehicle_state_through_api(self):
        markup = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("roadTypeInput", markup)
        self.assertIn("batteryInput", markup)
        self.assertIn("updateVehicleStateBtn", markup)
        self.assertIn("/api/vehicle-state", script)
        self.assertIn("updateVehicleState", script)
        self.assertIn("renderAutoEvents(payload.auto_events", script)

    def test_frontend_polls_vehicle_events(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("/api/vehicle-events", script)
        self.assertIn("startVehicleEventPolling", script)
        self.assertIn("setInterval", script)
        self.assertIn("event.severity", script)

    def test_vehicle_event_polling_does_not_overwrite_state_form_draft(self):
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn("syncControls", script)
        self.assertIn("syncNetwork", script)
        self.assertIn("renderVehicle(payload.vehicle_state, { syncControls: false, syncNetwork: false })", script)


if __name__ == "__main__":
    unittest.main()
