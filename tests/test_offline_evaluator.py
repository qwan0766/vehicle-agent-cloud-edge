import unittest

from evaluation.offline_evaluator import OfflineEvaluator


class TestOfflineEvaluator(unittest.TestCase):
    def test_evaluator_runs_builtin_scenarios_and_reports_metrics(self):
        report = OfflineEvaluator().run()

        self.assertGreaterEqual(report["total"], 20)
        self.assertGreaterEqual(report["intent_accuracy"], 0.8)
        self.assertEqual(report["safety_block_recall"], 1.0)
        self.assertEqual(report["driver_confirmation_recall"], 1.0)
        self.assertGreaterEqual(report["rag_hit_rate"], 0.5)
        self.assertEqual(report["failed_cases"], [])


if __name__ == "__main__":
    unittest.main()
