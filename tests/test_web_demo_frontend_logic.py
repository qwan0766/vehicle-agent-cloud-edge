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
        self.assertIn("renderSummarySegments", script)
        self.assertIn("formatSummarySegments", script)
        self.assertIn("local-context-summary-list", script)
        self.assertIn("summary-status", script)
        self.assertNotIn("nodes.localContextSummary.textContent = payload.summary", script)
        self.assertIn("localContextProvider", script)
        self.assertIn("localContextModel", script)
        self.assertIn("localContextPrompt", script)
        self.assertIn("estimated_prompt_tokens", script)
        self.assertIn("prompt_budget_tokens", script)
        self.assertIn("max_output_tokens", script)
        self.assertIn("renderLocalContext", script)
        self.assertIn("payload.local_context", script)

    def test_result_rendering_exposes_input_rewrite(self):
        script = self.read_frontend_scripts()

        self.assertIn("renderInputRewrite", script)
        self.assertIn("payload.input_rewrite", script)
        self.assertIn("input-rewrite-card", script)

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
        self.assertIn("clarification-tips", script)
        self.assertNotIn("nodes.commandInput.value = suggestion", script)
        self.assertNotIn("suggestionBox", script)

    def test_clarification_rendering_supports_destination_candidates(self):
        script = self.read_frontend_scripts()

        self.assertIn("clarification-candidates", script)
        self.assertIn("clarification-tips", script)
        self.assertIn('button.className = "clarification-candidate"', script)
        self.assertIn("candidate.confidence", script)
        self.assertIn("candidate.source", script)
        self.assertIn("confirmPendingAction", script)
        self.assertIn("pendingAction.id", script)
        self.assertIn("/api/confirm", script)

    def test_destination_clarification_result_is_aligned_in_agent_trace(self):
        script = self.read_frontend_scripts()

        self.assertIn("DestinationClarification", script)
        self.assertIn("clarification.result", script)
        self.assertIn("目的地信息不足", script)
        self.assertIn("未继续调用云端规划链路", script)

    def test_ecology_snapshot_renders_structured_weather_and_charging_data(self):
        script = self.read_frontend_scripts()
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn('item.tool_name === "ecology.snapshot"', script)
        self.assertIn("renderEcologySnapshot", script)
        self.assertIn("precipitation_mm", script)
        self.assertIn("charge_source", script)
        self.assertIn(".ecology-snapshot", css)
        self.assertIn(".ecology-metric", css)

    def test_confirmation_states_render_action_buttons(self):
        script = self.read_frontend_scripts()

        self.assertIn("renderPendingConfirmation", script)
        self.assertIn('result.status === "NEEDS_DRIVER_CONFIRMATION"', script)
        self.assertIn('result.status === "NEEDS_CHARGE_CONFIRMATION"', script)
        self.assertIn("confirmation-actions", script)
        self.assertIn("confirmed: true", script)

    def test_demo_buttons_live_inside_command_panel_and_do_not_auto_run(self):
        markup = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        script = self.read_frontend_scripts()

        self.assertIn("演示按钮", markup)
        self.assertIn('id="demoSteps"', markup)
        self.assertNotIn('id="scenarioButtons"', markup)
        self.assertIn("renderAutoEvents", script)
        self.assertIn("自动触发", script)
        self.assertIn("renderDemoSteps(", script)
        self.assertIn("activateDemoStep(nodes, state, step, false", script)
        self.assertIn("step.display_mode || step.network", script)
        self.assertNotIn(
            "renderScenarioButtons(nodes, state, setNetworkForRenderers, runCommandForRenderers)",
            script,
        )

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

    def test_vehicle_renderer_updates_safety_badge_from_vehicle_state(self):
        script = self.read_frontend_scripts()

        self.assertIn("vehicle.safety_state", script)
        self.assertIn("renderSafetyBadge", script)
        self.assertIn("badge-clarification", script)

    def test_vehicle_event_polling_does_not_overwrite_state_form_draft(self):
        script = self.read_frontend_scripts()

        self.assertIn("syncControls", script)
        self.assertIn("syncNetwork", script)
        self.assertIn("renderVehicle", script)
        self.assertIn("syncControls: false", script)

    def test_vehicle_state_apply_does_not_overwrite_network_selection(self):
        script = self.read_frontend_scripts()

        self.assertIn("applyVehicleState(deps, updates)", script)
        self.assertIn("syncNetwork: false", script)
        self.assertIn("syncNetwork: false", script)

    def test_demo_mode_applies_vehicle_state_before_running_command(self):
        script = self.read_frontend_scripts()

        self.assertIn("applyVehicleState", script)
        self.assertIn("step.vehicle_state", script)
        self.assertIn("await applyVehicleState(step.vehicle_state)", script)
        self.assertIn("activateDemoStep", script)
        self.assertIn("async", script)

    def test_provider_smoke_results_update_matching_provider_cards(self):
        markup = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        script = self.read_frontend_scripts()

        self.assertIn("providerCards", script)
        self.assertIn("[data-provider-health]", script)
        self.assertIn("providerCard.dataset.smokeName === item.name", script)
        self.assertIn("provider-health", script)
        self.assertIn("已更新", script)
        self.assertIn("smoke-summary", markup)
        self.assertNotIn("smoke-row", script)

    def test_agent_trace_renders_descriptions_and_full_width_layout(self):
        script = self.read_frontend_scripts()
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn("agentDescription", script)
        self.assertIn("agentScope", script)
        self.assertIn("agent-scope", script)
        self.assertIn("parallelAgentSet", script)
        self.assertIn("并行收集", script)
        self.assertIn("CloudDecisionAgent", script)
        self.assertIn("RouteProviderAgent", script)
        self.assertIn("route_provider", script)
        self.assertIn("provider_parallel", script)
        self.assertIn("车端本地", script)
        self.assertIn("云端调度", script)
        self.assertIn("数据闭环", script)
        self.assertIn("renderAlignedTrace", script)
        self.assertIn("toolBelongsToAgent", script)
        self.assertIn("LocalIntentAgent", script)
        self.assertIn("解析用户指令意图", script)
        self.assertIn('description.className = "agent-description"', script)
        self.assertIn("trace-pair", script)
        self.assertIn("agent-output-card", script)
        self.assertIn(".agent-card-header", css)
        self.assertIn(".agent-scope.scope-edge", css)
        self.assertIn(".agent-scope.scope-cloud", css)
        self.assertIn(".trace-pair.parallel-group", css)
        self.assertIn(".agent-parallel-badge", css)
        self.assertIn('toolName.startsWith("user_profile.")', script)
        self.assertIn('toolName.startsWith("knowledge.")', script)
        self.assertIn('toolName.startsWith("provider.geocode")', script)
        self.assertIn('toolName.startsWith("provider.map")', script)
        self.assertIn('toolName.startsWith("decision.")', script)
        self.assertIn(".trace-workbench", css)
        self.assertIn("grid-template-columns: minmax(260px, 0.9fr) minmax(320px, 1.1fr);", css)

    def test_frontend_uses_native_es_modules(self):
        markup = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        script = Path("web_demo/static/app.js").read_text(encoding="utf-8")

        self.assertIn('type="module"', markup)
        self.assertIn('src="/app.js?v=knowledge-layer-v1-20260511"', markup)
        self.assertIn("import", script)
        self.assertIn("./js/api.js?v=knowledge-layer-v1-20260511", script)
        self.assertIn("./js/events.js?v=knowledge-layer-v1-20260511", script)
        self.assertIn("./js/renderers/result.js?v=knowledge-layer-v1-20260511", script)

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
        self.assertIn('fetch("/api/offline-evaluation")', api_script)
        self.assertIn("requestId !== state.activeRequestId", events_script)
        self.assertIn("renderVehicle", events_script)
        self.assertIn("syncControls: false", events_script)
        self.assertIn("syncNetwork: false", events_script)

    def test_frontend_loads_offline_evaluation_after_initial_state(self):
        script = self.read_frontend_scripts()

        self.assertIn("getOfflineEvaluation", script)
        self.assertIn("loadOfflineEvaluation", script)
        self.assertIn("renderOfflineEvaluation(nodes, payload.offline_evaluation)", script)
        self.assertIn("renderOfflineEvaluation(nodes, payload)", script)


if __name__ == "__main__":
    unittest.main()
