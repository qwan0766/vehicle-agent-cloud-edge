import unittest
from pathlib import Path


class TestDeliveryPackaging(unittest.TestCase):
    def test_start_demo_script_documents_safe_demo_bootstrap(self):
        script_path = Path("scripts/start_demo.ps1")

        self.assertTrue(script_path.exists())
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("$ErrorActionPreference = \"Stop\"", script)
        self.assertIn("web_demo.server", script)
        self.assertIn("Start-Process", script)
        self.assertIn("Provider status", script)
        self.assertIn("DEEPSEEK_API_KEY", script)
        self.assertNotIn("sk-", script)

    def test_check_all_script_runs_full_delivery_checks(self):
        script_path = Path("scripts/check_all.ps1")

        self.assertTrue(script_path.exists())
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("pytest tests", script)
        self.assertIn("scripts/run_acceptance.py", script)
        self.assertIn("scripts/web_qa.py", script)
        self.assertIn("--screenshots", script)
        self.assertIn("reports/acceptance_report.md", script)
        self.assertIn("reports/web_qa_report.md", script)

    def test_readme_first_screen_is_interview_delivery_oriented(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        first_screen = readme[:2500]

        self.assertIn("面试作品定位", first_screen)
        self.assertIn("一键启动", first_screen)
        self.assertIn("一键验收", first_screen)
        self.assertIn("固定演示路线", first_screen)
        self.assertIn("LangGraph", first_screen)
        self.assertIn("edge_deepseek_sim", first_screen)


if __name__ == "__main__":
    unittest.main()
