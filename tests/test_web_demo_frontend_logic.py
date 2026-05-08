import unittest
from pathlib import Path


class TestWebDemoFrontendLogic(unittest.TestCase):
    @staticmethod
    def read_frontend_scripts():
        script_paths = [Path("web_demo/static/app.js")]
        script_paths.extend(sorted(Path("web_demo/static/js").rglob("*.js")))

        return "\n".join(
            script_path.read_text(encoding="utf-8")
            for script_path in script_paths
            if script_path.exists()
        )

    def test_run_command_ignores_stale_responses(self):
        script = self.read_frontend_scripts()

        self.assertIn("requestSeq", script)
        self.assertIn("activeRequestId", script)
        self.assertIn("requestId !== state.activeRequestId", script)

    def test_blocked_result_has_dedicated_trace_mode(self):
        script = self.read_frontend_scripts()

        self.assertIn('result.status === "BLOCKED"', script)
        self.assertIn('"安全拦截"', script)

    def test_result_rendering_updates_local_context_panel(self):
        script = self.read_frontend_scripts()

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
        script = self.read_frontend_scripts()

        self.assertIn("graphMode", script)
        self.assertIn("graphPath", script)
        self.assertIn("renderGraphPath", script)
        self.assertIn("payload.graph", script)

    def test_result_rendering_supports_destination_clarification(self):
        script = self.read_frontend_scripts()

        self.assertIn("renderClarification", script)
        self.assertIn('result.status === "NEEDS_CLARIFICATION"', script)
        self.assertIn("clarification-suggestions", script)
        self.assertIn("nodes.commandInput.value = suggestion", script)
        self.assertIn("nodes.commandInput.focus()", script)

    def test_clarification_rendering_supports_destination_candidates(self):
        script = self.read_frontend_scripts()

        self.assertIn("clarification-candidates", script)
        self.assertIn("candidate.confidence", script)
        self.assertIn("candidate.source", script)
        self.assertIn("confirmPendingAction", script)
        self.assertIn("pendingAction.id", script)
        self.assertIn("/api/confirm", script)

    def test_confirmation_states_render_action_buttons(self):
        script = self.read_frontend_scripts()

        self.assertIn("renderPendingConfirmation", script)
        self.assertIn('result.status === "NEEDS_DRIVER_CONFIRMATION"', script)
        self.assertIn('result.status === "NEEDS_CHARGE_CONFIRMATION"', script)
        self.assertIn("confirmation-actions", script)
        self.assertIn("confirmed: true", script)

    def test_scenario_buttons_mark_manual_trigger_and_auto_events_render_separately(self):
        script = self.read_frontend_scripts()

        self.assertIn("scenario.trigger", script)
        self.assertIn("手动演示", script)
        self.assertIn("renderAutoEvents", script)
        self.assertIn("自动触发", script)

    def test_frontend_updates_vehicle_state_through_api(self):
        markup = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        script = self.read_frontend_scripts()

        self.assertIn("roadTypeInput", markup)
        self.assertIn("batteryInput", markup)
        self.assertIn("updateVehicleStateBtn", markup)
        self.assertIn("/api/vehicle-state", script)
        self.assertIn("updateVehicleState", script)
        self.assertIn("applyVehicleState", script)
        self.assertIn("payload.auto_events || []", script)

    def test_frontend_polls_vehicle_events(self):
        script = self.read_frontend_scripts()

        self.assertIn("/api/vehicle-events", script)
        self.assertIn("startVehicleEventPolling", script)
        self.assertIn("setInterval", script)
        self.assertIn("event.severity", script)

    def test_vehicle_event_polling_does_not_overwrite_state_form_draft(self):
        script = self.read_frontend_scripts()

        self.assertIn("syncControls", script)
        self.assertIn("syncNetwork", script)
        self.assertIn("renderVehicle", script)
        self.assertIn("syncControls: false", script)
        self.assertIn("syncNetwork: false", script)

    def test_demo_mode_applies_vehicle_state_before_running_command(self):
        script = self.read_frontend_scripts()

        self.assertIn("applyVehicleState", script)
        self.assertIn("step.vehicle_state", script)
        self.assertIn("await applyVehicleState(step.vehicle_state)", script)
        self.assertIn("activateDemoStep", script)
        self.assertIn("async", script)

    def test_frontend_uses_native_es_modules(self):
        markup = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn('type="module"', markup)
        self.assertIn('src="/app.js"', markup)
        self.assertIn("import", script)
        self.assertIn("./js/api.js", script)
        self.assertIn("./js/events.js", script)

    def test_frontend_modules_exist_with_expected_responsibilities(self):
        module_paths = [
            Path("web_demo/static/js/api.js"),
            Path("web_demo/static/js/state.js"),
            Path("web_demo/static/js/dom.js"),
            Path("web_demo/static/js/events.js"),
            Path("web_demo/static/js/markdown.js"),
            Path("web_demo/static/js/renderers/vehicle.js"),
            Path("web_demo/static/js/renderers/demo.js"),
            Path("web_demo/static/js/renderers/result.js"),
            Path("web_demo/static/js/renderers/trace.js"),
            Path("web_demo/static/js/renderers/rag.js"),
            Path("web_demo/static/js/renderers/feedback.js"),
            Path("web_demo/static/js/renderers/providers.js"),
            Path("web_demo/static/js/renderers/acceptance.js"),
            Path("web_demo/static/js/renderers/route.js"),
            Path("web_demo/static/js/renderers/local-context.js"),
        ]

        for module_path in module_paths:
            with self.subTest(module_path=module_path):
                self.assertTrue(module_path.exists(), f"{module_path} should exist")

        if any(not module_path.exists() for module_path in module_paths):
            return

        api_script = Path("web_demo/static/js/api.js").read_text(encoding="utf-8")
        events_script = Path("web_demo/static/js/events.js").read_text(encoding="utf-8")

        self.assertIn('fetch("/api/state")', api_script)
        self.assertIn('fetch("/api/run"', api_script)
        self.assertIn('fetch("/api/vehicle-state"', api_script)
        self.assertIn('fetch("/api/vehicle-events")', api_script)
        self.assertIn("requestId !== state.activeRequestId", events_script)
        self.assertIn("renderVehicle", events_script)
        self.assertIn("syncControls: false", events_script)
        self.assertIn("syncNetwork: false", events_script)


if __name__ == "__main__":
    unittest.main()
