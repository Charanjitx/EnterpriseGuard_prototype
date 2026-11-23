"""Regression tests for fail-closed repair generation in healing_engine.py.

Place in tests/test_healing_repair_failure.py and run unittest discovery.
"""
import unittest
from unittest.mock import patch

import healing_engine


class TestHealingRepairFailure(unittest.TestCase):
    def setUp(self):
        self.bad_validation = {
            "accepted": False,
            "evaluation": {"passed": False, "safe_to_accept": False},
            "authorization_guard": {
                "passed": False,
                "unsupported_commitments": [],
            },
            "policy_guard": {"passed": True, "findings": []},
        }
        self.diagnosis = {
            "failure_type": "POLICY_VIOLATION",
            "recommendation": "Avoid unauthorized commitments.",
            "evidence": [],
        }

    def test_exhausted_repairs_require_human_review(self):
        with (
            patch.object(healing_engine, "_validate_candidate", return_value=self.bad_validation),
            patch.object(healing_engine, "_build_diagnosis", return_value=self.diagnosis.copy()),
            patch.object(healing_engine, "repair_prompt", side_effect=ValueError("Local policy validation failed")) as repair,
            patch.object(healing_engine, "generate_response") as generate,
        ):
            result = healing_engine.run_self_healing(
                original_prompt="Original trusted prompt",
                policy="Never promise a refund without approval.",
                query="Give me a refund",
                initial_response="I promise a refund",
                max_attempts=3,
                authorized_actions=[],
            )

        self.assertEqual(result["status"], "REQUIRES_HUMAN_REVIEW")
        self.assertEqual(result["attempts_used"], 3)
        self.assertEqual(repair.call_count, 3)
        generate.assert_not_called()
        self.assertIsNone(result["accepted_prompt"])
        self.assertIsNone(result["accepted_response"])
        self.assertIs(result["final_evaluation"], self.bad_validation["evaluation"])
        self.assertTrue(all(h["outcome"] == "REPAIR_GENERATION_REJECTED" for h in result["history"]))
        self.assertTrue(all(h["retest"] is None for h in result["history"]))

    def test_repair_failure_can_retry_and_accept_valid_candidate(self):
        good_validation = {
            "accepted": True,
            "evaluation": {"passed": True, "safe_to_accept": True},
            "authorization_guard": {"passed": True, "unsupported_commitments": []},
            "policy_guard": {"passed": True, "findings": []},
        }
        with (
            patch.object(healing_engine, "_validate_candidate", side_effect=[self.bad_validation, good_validation]),
            patch.object(healing_engine, "_build_diagnosis", return_value=self.diagnosis.copy()),
            patch.object(healing_engine, "repair_prompt", side_effect=[
                ValueError("Local policy validation failed"),
                {"repaired_prompt": "Safe candidate"},
            ]),
            patch.object(healing_engine, "check_policy_preservation", return_value={"passed": True, "findings": []}),
            patch.object(healing_engine, "generate_response", return_value={"response": "Safe answer"}) as generate,
        ):
            result = healing_engine.run_self_healing(
                original_prompt="Original trusted prompt",
                policy="Never promise a refund without approval.",
                query="Give me a refund",
                initial_response="I promise a refund",
                max_attempts=3,
                authorized_actions=[],
            )

        self.assertEqual(result["status"], "CANDIDATE_ACCEPTED")
        self.assertEqual(result["attempts_used"], 2)
        self.assertEqual(result["accepted_prompt"], "Safe candidate")
        self.assertEqual(result["accepted_response"], "Safe answer")
        self.assertEqual(result["history"][0]["outcome"], "REPAIR_GENERATION_REJECTED")
        self.assertEqual(result["history"][1]["outcome"], "CANDIDATE_ACCEPTED")
        generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()