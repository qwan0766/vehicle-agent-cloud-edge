import unittest
from pathlib import Path


class TestWebDemoMarkup(unittest.TestCase):
    def test_demo_mode_panel_has_required_targets(self):
        html = Path("web_demo/static/index.html").read_text(encoding="utf-8")

        self.assertIn('aria-label="面试演示模式"', html)
        self.assertIn('id="demoSteps"', html)
        self.assertIn('id="demoTalkTrack"', html)
        self.assertIn('id="demoFocus"', html)


if __name__ == "__main__":
    unittest.main()
