"""Offline regression tests for provider outages during self-healing."""
import unittest
from unittest.mock import patch

import healing_engine
from llm_engine import LLMServiceUnavailable


POLICY = "Never promise a full refund without human approval."
PROMPT = "You are a support bot."
QUERY = "I want a refund."
RESPONSE = "I can issue a refund now."


def failed_validation(*args, **kwargs):
    return {
        "accepted": False,
        "evaluation": {"passed": False, "safe_to_accept": False},
        "authorization_guard": {"passed": False, "unsupported_commitments": []},
        "policy_guard": {"passed": True, "status": "BASELINE", "findings": []},
    }


class TestHealingServiceUnavailable(unittest.TestCase):
    def test_initial_generation_outage(self):
        with patch.object(healing_engine, "generate_response", side_effect=LLMServiceUnavailable("429")):
            result = healing_engine.run_self_healing(PROMPT, POLICY, QUERY)
        self.assertEqual(result["status"], "SERVICE_UNAVAILABLE")
        self.assertEqual(result["attempts_used"], 0)
        self.assertIsNone(result["final_evaluation"])
        self.assertEqual(result["service_error"]["stage"], "INITIAL_RESPONSE")

    def test_initial_evaluation_outage(self):
        with patch.object(healing_engine, "_validate_candidate", side_effect=LLMServiceUnavailable("429")):
            result = healing_engine.run_self_healing(PROMPT, POLICY, QUERY, initial_response=RESPONSE)
        self.assertEqual(result["status"], "SERVICE_UNAVAILABLE")
        self.assertEqual(result["service_error"]["stage"], "INITIAL_VALIDATION")
        self.assertIsNone(result["final_evaluation"])

    def test_repair_generation_outage(self):
        with (
            patch.object(healing_engine, "_validate_candidate", side_effect=failed_validation),
            patch.object(healing_engine, "_build_diagnosis", return_value={"failure_type": "POLICY_VIOLATION", "recommendation": "Fix"}),
            patch.object(healing_engine, "repair_prompt", side_effect=LLMServiceUnavailable("429")),
        ):
            result = healing_engine.run_self_healing(PROMPT, POLICY, QUERY, initial_response=RESPONSE)
        self.assertEqual(result["status"], "SERVICE_UNAVAILABLE")
        self.assertEqual(result["service_error"]["stage"], "REPAIR_GENERATION")
        self.assertEqual(result["attempts_used"], 0)
        self.assertIsNone(result["accepted_prompt"])

    def test_retest_outage_does_not_promote_candidate(self):
        with (
            patch.object(healing_engine, "_validate_candidate", side_effect=failed_validation),
            patch.object(healing_engine, "_build_diagnosis", return_value={"failure_type": "POLICY_VIOLATION", "recommendation": "Fix"}),
            patch.object(healing_engine, "repair_prompt", return_value={"repaired_prompt": "Safe candidate"}),
            patch.object(healing_engine, "check_policy_preservation", return_value={"passed": True, "status": "NO_DRIFT_DETECTED", "findings": []}),
            patch.object(healing_engine, "generate_response", side_effect=LLMServiceUnavailable("429")),
        ):
            result = healing_engine.run_self_healing(PROMPT, POLICY, QUERY, initial_response=RESPONSE)
        self.assertEqual(result["status"], "SERVICE_UNAVAILABLE")
        self.assertEqual(result["service_error"]["stage"], "RETEST")
        self.assertIsNone(result["accepted_prompt"])
        self.assertEqual(result["final_evaluation"], {"passed": False, "safe_to_accept": False})


if __name__ == "__main__":
    unittest.main()
