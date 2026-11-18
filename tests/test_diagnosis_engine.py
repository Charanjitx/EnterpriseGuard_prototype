import unittest
from diagnosis_engine import diagnose_failure

class DiagnosisEngineTests(unittest.TestCase):
    def test_policy_violation(self):
        result = diagnose_failure(query="I want a refund", response="I will issue a 100% full refund.",
            policy="Never promise a full refund or a discount greater than 20%.",
            system_prompt="Be helpful and keep customers happy.")
        self.assertEqual(result["failure_type"], "POLICY_VIOLATION")
        self.assertTrue(result["evidence"])

    def test_retrieval_failure(self):
        result = diagnose_failure(query="What is the leave policy?", response="You get 20 days.",
            required_terms=["annual leave entitlement"], retrieved_context="General HR overview only.")
        self.assertEqual(result["failure_type"], "RETRIEVAL_FAILURE")

    def test_context_failure(self):
        result = diagnose_failure(query="What is the leave policy?", response="Please contact HR.",
            required_terms=["30 days annual leave"],
            retrieved_context="Employees receive 30 days annual leave.")
        self.assertEqual(result["failure_type"], "CONTEXT_FAILURE")

    def test_hallucination_requires_verifier_signal(self):
        result = diagnose_failure(query="Who is the CEO?", response="The CEO is Jane Doe.",
            unsupported_claims=["The name Jane Doe is not supported by the supplied sources."])
        self.assertEqual(result["failure_type"], "HALLUCINATION")

    def test_reasoning_failure_requires_external_check(self):
        result = diagnose_failure(query="What is 17 times 19?", response="333",
            reasoning_check_passed=False)
        self.assertEqual(result["failure_type"], "REASONING_FAILURE")

    def test_missing_trace_evidence_is_not_guessed(self):
        result = diagnose_failure(query="Question", response="Unclear answer")
        self.assertEqual(result["failure_type"], "INSUFFICIENT_EVIDENCE")
        self.assertLess(result["confidence"], 0.5)

if __name__ == "__main__":
    unittest.main()
