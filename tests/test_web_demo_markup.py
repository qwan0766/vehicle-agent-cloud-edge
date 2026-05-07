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


if __name__ == "__main__":
    unittest.main()
