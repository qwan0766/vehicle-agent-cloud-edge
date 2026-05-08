import unittest

from scripts.web_qa import CheckResult, render_markdown


class TestWebQaReport(unittest.TestCase):
    def test_report_lists_checks_and_screenshots(self):
        payload = {
            "generated_at": "2026-05-08T20:00:00+08:00",
            "base_url": "http://127.0.0.1:8031",
            "overall_status": "PASS",
            "checks": [
                CheckResult("demo online_navigation", "PASS", "NAVIGATION / EXECUTED").__dict__,
                CheckResult(
                    "demo fuzzy_destination_clarification",
                    "PASS",
                    "NAVIGATION / NEEDS_CLARIFICATION",
                ).__dict__,
            ],
            "screenshots": ["E:/claudeCode/weilaiAgent/reports/browser_qa/desktop.png"],
        }

        report = render_markdown(payload)

        self.assertIn("# Web QA Report", report)
        self.assertIn("| demo online_navigation | PASS | NAVIGATION / EXECUTED |", report)
        self.assertIn("![desktop]", report)


if __name__ == "__main__":
    unittest.main()
