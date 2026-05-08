import unittest
from pathlib import Path

from scripts.run_delivery_check import (
    CheckResult,
    DEMO_CASES,
    PROJECT_ROOT,
    build_stable_env,
    render_report,
)


class TestDeliveryCheck(unittest.TestCase):
    def test_report_contains_summary_and_demo_cases(self):
        report = render_report(
            [
                CheckResult("unit tests", "PASS", "226 passed", 1.2),
                CheckResult("frontend js syntax", "PASS", "15 files checked", 0.4),
                CheckResult("demo scenarios", "PASS", "5 scenarios checked", 0.8),
            ],
            generated_at="2026-05-08T20:00:00+08:00",
        )

        self.assertIn("# 车载 Multi-Agent 交付验收报告", report)
        self.assertIn("- 总体状态：PASS", report)
        self.assertIn("| unit tests | PASS | 1.20s |", report)
        self.assertIn("## 面试演示场景", report)
        self.assertIn("正常导航端云协同", report)
        self.assertIn("模糊目的地澄清", report)
        self.assertIn("低电量状态与能源策略", report)

    def test_demo_cases_cover_delivery_storyline(self):
        ids = [case["id"] for case in DEMO_CASES]

        self.assertEqual(
            ids,
            [
                "online_navigation",
                "fuzzy_destination_clarification",
                "highway_speed_confirmation",
                "urban_speed_block",
                "low_battery_energy_policy",
            ],
        )

    def test_stable_env_disables_external_providers(self):
        env = build_stable_env()

        self.assertEqual(env["LOCAL_LLM_PROVIDER"], "mock_local")
        self.assertEqual(env["USE_OPEN_METEO"], "0")
        self.assertEqual(env["USE_OPENCHARGEMAP"], "0")
        self.assertEqual(env["DEEPSEEK_API_KEY"], "")
        self.assertEqual(env["AMAP_API_KEY"], "")

    def test_project_root_points_to_workspace(self):
        self.assertTrue((PROJECT_ROOT / "web_demo" / "app_model.py").exists())
        self.assertTrue(Path("scripts").exists())


if __name__ == "__main__":
    unittest.main()
