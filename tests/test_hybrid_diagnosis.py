
import unittest
from diagnosis_engine import diagnose_failure


class HybridDiagnosisTests(unittest.TestCase):

    def setUp(self):

        self.query = "I want a full refund."

        self.response = (
            "Your entire payment will be returned "
            "to your original payment method."
        )

        self.policy = (
            "Never promise full refunds without "
            "manager approval."
        )

        self.prompt = "You are a helpful customer support bot."

        self.evaluation = {
            "passed": False,
            "failure_type": "POLICY_VIOLATION",
            "severity": "HIGH",
            "reason": (
                "The chatbot promises a full refund "
                "without manager approval."
            ),
            "evidence": [self.response],
            "recommendation": (
                "Require manager approval before "
                "promising a full refund."
            )
        }

    def test_semantic_policy_violation(self):

        result = diagnose_failure(
            query=self.query,
            response=self.response,
            policy=self.policy,
            system_prompt=self.prompt,
            semantic_evaluation=self.evaluation
        )

        self.assertEqual(
            result["failure_type"],
            "POLICY_VIOLATION"
        )

        self.assertEqual(
            result["diagnosis_source"],
            "SEMANTIC_EVALUATOR"
        )

        self.assertTrue(
            result["trace"]["semantic_evidence_verified"]
        )

    def test_reject_unverified_evidence(self):

        self.evaluation["evidence"] = [
            "I promise you a million dollars."
        ]

        result = diagnose_failure(
            query=self.query,
            response=self.response,
            policy=self.policy,
            system_prompt=self.prompt,
            semantic_evaluation=self.evaluation
        )

        self.assertEqual(
            result["failure_type"],
            "INSUFFICIENT_EVIDENCE"
        )

        self.assertFalse(
            result["trace"]["semantic_evidence_verified"]
        )

    def test_missing_policy_hypothesis(self):

        result = diagnose_failure(
            query=self.query,
            response=self.response,
            policy=self.policy,
            system_prompt=self.prompt,
            semantic_evaluation=self.evaluation
        )

        self.assertIn(
            "possible contributing cause",
            result["suspected_root_cause"]
        )

    def test_hybrid_detection(self):

        response = "I will issue a full refund immediately."

        self.evaluation["evidence"] = [response]

        result = diagnose_failure(
            query=self.query,
            response=response,
            policy=self.policy,
            system_prompt=self.prompt,
            semantic_evaluation=self.evaluation
        )

        self.assertEqual(
            result["diagnosis_source"],
            "HYBRID"
        )

    def test_passing_evaluation_not_a_violation(self):

        self.evaluation["passed"] = True
        self.evaluation["failure_type"] = "NONE"

        result = diagnose_failure(
            query=self.query,
            response=self.response,
            policy=self.policy,
            system_prompt=self.prompt,
            semantic_evaluation=self.evaluation
        )

        self.assertNotEqual(
            result["failure_type"],
            "POLICY_VIOLATION"
        )


if __name__ == "__main__":
    unittest.main()
