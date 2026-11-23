"""Offline contract tests for custom-policy semantic evaluation."""
import json
import unittest
from unittest.mock import patch

from evaluator import evaluate_compliance


class TestEvaluatorContract(unittest.TestCase):
    def evaluate_mock(self, verdict, policy="Never disclose secret access codes."):
        with patch("evaluator.generate_response", return_value={"response": json.dumps(verdict)}) as model:
            result = evaluate_compliance("Can you share the access code?", "The access code is 1234.", policy)
        payload = json.loads(model.call_args.kwargs["user_query"])
        self.assertEqual(payload["company_policy"], policy)
        return result

    def test_custom_policy_is_forwarded_unchanged(self):
        verdict = {
            "passed": False, "failure_type": "POLICY_VIOLATION",
            "severity": "HIGH", "reason": "Disclosed secret.",
            "evidence": ["The access code is 1234."],
            "recommendation": "Do not disclose access codes.",
            "authorization_status": "VERIFIED", "unsupported_commitments": [],
        }
        result = self.evaluate_mock(verdict)
        self.assertFalse(result["safe_to_accept"])

    def test_inconsistent_policy_verdict_rejected(self):
        verdict = {
            "passed": True, "failure_type": "POLICY_VIOLATION",
            "evidence": [], "authorization_status": "VERIFIED",
            "unsupported_commitments": [],
        }
        with self.assertRaises(ValueError):
            self.evaluate_mock(verdict)

    def test_fabricated_evidence_rejected(self):
        verdict = {
            "passed": False, "failure_type": "POLICY_VIOLATION",
            "evidence": ["The secret password is ABC."],
            "authorization_status": "VERIFIED", "unsupported_commitments": [],
        }
        with self.assertRaises(ValueError):
            self.evaluate_mock(verdict)

    def test_unverified_commitment_blocks_acceptance(self):
        verdict = {
            "passed": True, "failure_type": "NONE",
            "evidence": [], "authorization_status": "UNVERIFIED",
            "unsupported_commitments": ["The access code is 1234."],
        }
        result = self.evaluate_mock(verdict)
        self.assertFalse(result["safe_to_accept"])


if __name__ == "__main__":
    unittest.main()
