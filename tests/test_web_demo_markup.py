import unittest
from pathlib import Path


class TestWebDemoMarkup(unittest.TestCase):
    def test_demo_mode_panel_has_required_targets(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('aria-label="面试演示模式"', html)
        self.assertIn('id="demoSteps"', html)
        self.assertIn('id="demoTalkTrack"', html)
        self.assertIn('id="demoFocus"', html)

    def test_local_context_panel_has_required_targets(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('aria-label="本地意图Agent上下文管理"', html)
        self.assertIn('id="localContextWindow"', html)
        self.assertIn('id="localContextProvider"', html)
        self.assertIn('id="localContextModel"', html)
        self.assertIn('id="localContextSummary"', html)
        self.assertIn('id="localContextRecent"', html)
        self.assertIn('id="localContextPrompt"', html)

    def test_trace_panel_has_graph_targets(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('aria-label="Agent 调用链"', html)
        self.assertIn('id="graphMode"', html)
        self.assertIn('id="graphPath"', html)

    def test_styles_include_clarification_card_targets(self):
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn(".clarification-card", css)
        self.assertIn(".clarification-suggestions", css)
        self.assertIn(".clarification-candidates", css)
        self.assertIn(".clarification-candidate", css)

    def test_styles_include_mobile_overflow_guardrails(self):
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 520px)", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr);", css)
        self.assertIn("padding: 14px 10px;", css)
        self.assertIn("overflow-x: hidden;", css)
        self.assertIn("max-width: 100%;", css)

    def test_styles_place_result_panel_before_secondary_panels(self):
        css = Path("web_demo/static/styles.css").read_text(encoding="utf-8")

        self.assertIn(".result-panel", css)
        self.assertIn("order: 3;", css)
        self.assertIn(".demo-panel", css)
        self.assertIn("order: 4;", css)


if __name__ == "__main__":
    unittest.main()
