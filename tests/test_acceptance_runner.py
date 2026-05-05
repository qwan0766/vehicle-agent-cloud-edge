import unittest

from scripts.run_acceptance import (
    AcceptanceStepResult,
    OnlineCaseExpectation,
    acceptance_passed,
    render_markdown_report,
    validate_online_case,
)


class TestAcceptanceRunner(unittest.TestCase):
    def test_acceptance_passed_rejects_failed_required_step(self):
        results = [
            AcceptanceStepResult("unit tests", "PASS", "84 tests", 1.2),
            AcceptanceStepResult("online matrix", "FAIL", "route mismatch", 0.3),
        ]

        self.assertFalse(acceptance_passed(results))

    def test_markdown_report_records_step_statuses_and_details(self):
        results = [
            AcceptanceStepResult("unit tests", "PASS", "84 tests", 20.5),
            AcceptanceStepResult("provider smoke", "SKIP", "optional key missing", 0.1),
        ]

        markdown = render_markdown_report(
            results,
            generated_at="2026-05-05T17:30:00+08:00",
        )

        self.assertIn("# 车载 Multi-Agent 验收报告", markdown)
        self.assertIn("| unit tests | PASS | 20.50s |", markdown)
        self.assertIn("optional key missing", markdown)

    def test_online_case_validation_checks_status_and_forbidden_trace(self):
        payload = {
            "request": {
                "command_type": "CAR_CONTROL",
                "safety": "SAFE",
            },
            "result": {
                "status": "EXECUTED",
            },
            "runtime_trace": [
                {"tool_name": "user_profile.lookup"},
                {"tool_name": "decision.summarize"},
            ],
        }
        expectation = OnlineCaseExpectation(
            content="温度调到24度",
            expected_command_type="CAR_CONTROL",
            expected_safety="SAFE",
            expected_status="EXECUTED",
            forbidden_trace_tools=("route.plan",),
        )

        ok, detail = validate_online_case(payload, expectation)

        self.assertTrue(ok, detail)

    def test_online_case_validation_reports_forbidden_trace(self):
        payload = {
            "request": {
                "command_type": "CAR_CONTROL",
                "safety": "SAFE",
            },
            "result": {
                "status": "EXECUTED",
            },
            "runtime_trace": [
                {"tool_name": "route.plan"},
            ],
        }
        expectation = OnlineCaseExpectation(
            content="温度调到24度",
            expected_command_type="CAR_CONTROL",
            expected_safety="SAFE",
            expected_status="EXECUTED",
            forbidden_trace_tools=("route.plan",),
        )

        ok, detail = validate_online_case(payload, expectation)

        self.assertFalse(ok)
        self.assertIn("forbidden trace tool", detail)


if __name__ == "__main__":
    unittest.main()
