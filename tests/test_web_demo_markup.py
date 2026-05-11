import unittest
from pathlib import Path


class TestWebDemoMarkup(unittest.TestCase):
    def test_command_panel_embeds_demo_buttons(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('aria-label="指令执行"', html)
        self.assertIn("演示按钮", html)
        self.assertIn('id="demoSteps"', html)
        self.assertIn('id="demoTalkTrack"', html)
        self.assertIn('id="demoFocus"', html)
        self.assertNotIn('class="panel demo-panel"', html)
        self.assertNotIn('aria-label="面试演示模式"', html)
        self.assertNotIn('id="scenarioButtons"', html)

    def test_local_context_panel_has_required_targets(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn('aria-label="本地意图Agent上下文管理"', html)
        self.assertIn('id="localContextWindow"', html)
        self.assertIn('data-layout="full-width"', html)
        self.assertIn('style="grid-column: 1 / -1"', html)
        self.assertIn('id="localContextProvider"', html)
        self.assertIn('id="localContextModel"', html)
        self.assertIn('id="localContextSummary"', html)
        self.assertIn('class="local-context-summary"', html)
        self.assertNotIn('<strong id="localContextSummary"', html)
        self.assertNotIn('<div id="localContextSummary"', html)
        self.assertIn('id="localContextRecent"', html)
        self.assertIn('id="localContextPrompt"', html)
        self.assertIn("section.local-context-panel.panel", css)
        self.assertIn("grid-column: 1 / -1", css)
        self.assertIn("!important", css)
        self.assertIn(".local-context-panel .local-context-grid", css)

    def test_trace_panel_has_graph_targets(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('aria-label="Agent 调用链"', html)
        self.assertIn('id="graphMode"', html)
        self.assertIn('id="graphPath"', html)
        self.assertIn('class="trace-workbench"', html)
        self.assertIn('class="trace-heading agent-column"', html)
        self.assertIn('class="trace-heading runtime-column"', html)
        self.assertIn('class="agent-trace aligned-agent-trace"', html)

    def test_static_assets_are_versioned_for_browser_cache_busting(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn("/styles.css?v=knowledge-layer-v1-20260511", html)
        self.assertIn("/app.js?v=knowledge-layer-v1-20260511", html)

    def test_styles_include_clarification_card_targets(self):
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn(".clarification-card", css)
        self.assertIn(".clarification-tips", css)
        self.assertIn(".clarification-candidates", css)
        self.assertIn(".clarification-candidate", css)

    def test_styles_include_mobile_overflow_guardrails(self):
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 520px)", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", css)
        self.assertIn("padding: 14px 10px;", css)
        self.assertIn("overflow-x: hidden;", css)
        self.assertIn("max-width: 100%;", css)

    def test_result_panel_is_in_primary_workflow_before_secondary_panels(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        result_index = html.index('class="panel result-panel"')
        trace_index = html.index('class="panel trace-panel"')
        rag_index = html.index('class="panel rag-panel"')

        self.assertLess(result_index, trace_index)
        self.assertLess(result_index, rag_index)

    def test_dashboard_has_primary_and_observability_sections(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('class="dashboard-section-title primary-section-title"', html)
        self.assertIn('class="dashboard-section-title observability-section-title"', html)

    def test_provider_panel_maps_cards_to_real_interfaces(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('data-smoke-name="DeepSeek LLM"', html)
        self.assertIn('class="provider-smoke-name">对应检测：DeepSeek LLM</small>', html)
        self.assertIn('接口：DeepSeek /chat/completions', html)
        self.assertIn('data-smoke-name="Open-Meteo Weather"', html)
        self.assertIn('class="provider-smoke-name">对应检测：Open-Meteo Weather</small>', html)
        self.assertIn('接口：Open-Meteo /v1/forecast', html)
        self.assertIn('data-smoke-name="AMap Route"', html)
        self.assertIn('class="provider-smoke-name">对应检测：AMap Route</small>', html)
        self.assertIn('接口：高德 /v3/direction/driving', html)
        self.assertIn('data-smoke-name="AMap POI"', html)
        self.assertIn('class="provider-smoke-name">对应检测：AMap POI</small>', html)
        self.assertIn('接口：高德 /v3/place/around', html)
        self.assertIn('data-provider-health', html)
        self.assertIn('class="smoke-summary"', html)

        self.assertNotIn("OpenChargeMap", html)
        self.assertNotIn("Baidu Map", html)


if __name__ == "__main__":
    unittest.main()
