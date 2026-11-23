"""Offline tests for Step 97 benchmark; no external model calls."""
import unittest
from benchmark_evaluator import CASES, run_benchmark, score


class TestEvaluatorBenchmark(unittest.TestCase):
    def test_fixture_balance_and_uniqueness(self):
        self.assertEqual(len(CASES), 8)
        self.assertEqual(len({c["id"] for c in CASES}), 8)
        self.assertEqual({c["domain"] for c in CASES},
                         {"healthcare", "finance", "hr", "developer"})
        for domain in {c["domain"] for c in CASES}:
            self.assertEqual(
                {c["expected_safe"] for c in CASES if c["domain"] == domain},
                {True, False},
            )

    def test_score_false_approvals_and_rejections(self):
        results = [
            {"status": "evaluated", "expected_safe": False, "predicted_safe": True},
            {"status": "evaluated", "expected_safe": True, "predicted_safe": False},
            {"status": "evaluated", "expected_safe": True, "predicted_safe": True},
            {"status": "error", "expected_safe": False},
        ]
        metrics = score(results)
        self.assertEqual(metrics["false_approvals"], 1)
        self.assertEqual(metrics["false_rejections"], 1)
        self.assertEqual(metrics["errors"], 1)
        self.assertEqual(metrics["accuracy"], 1 / 3)

    def test_injected_evaluator_and_errors(self):
        def evaluator(query, response, policy):
            if "definitely" in response:
                raise ValueError("Invalid model output")
            return {"safe_to_accept": True, "failure_type": "NONE",
                    "authorization_status": "VERIFIED", "evidence": []}
        report = run_benchmark(CASES[:2], evaluator=evaluator)
        self.assertEqual(report["metrics"]["errors"], 1)
        self.assertEqual(report["metrics"]["evaluated"], 1)
        self.assertEqual(report["results"][0]["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
