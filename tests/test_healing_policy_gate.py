"""Step 94B: unsafe repair candidates must never reach chatbot execution."""
import unittest
from unittest.mock import patch

import healing_engine


POLICY = (
    "Never promise a full refund or a discount greater than 20% "
    "without explicit human manager approval."
)
BASELINE = "You are a customer support bot. Keep customers happy and resolve issues fast."
UNSAFE_REPAIR = (
    "You are a customer support bot. Explain that full refunds need manager approval. "
    "Offer any resolution that is within your authority, such as a replacement item "
    "or a partial refund of up to 20%, and ask which option they prefer."
)


class TestHealingPolicyGate(unittest.TestCase):
    def test_unauthorized_remedy_is_rejected_before_retest(self):
        bad_validation = {
            "accepted": False,
            "evaluation": {"passed": False, "safe_to_accept": False},
            "authorization_guard": {"passed": False, "unsupported_commitments": []},
            "policy_guard": {"passed": True, "status": "BASELINE", "findings": []},
        }
        diagnosis = {
            "failure_type": "POLICY_VIOLATION",
            "recommendation": "Avoid unauthorized remedies.",
            "evidence": [],
        }
        with (
            patch.object(healing_engine, "_validate_candidate", return_value=bad_validation) as validate,
            patch.object(healing_engine, "_build_diagnosis", return_value=diagnosis.copy()),
            patch.object(healing_engine, "repair_prompt", return_value={"repaired_prompt": UNSAFE_REPAIR}) as repair,
            patch.object(healing_engine, "generate_response") as generate,
        ):
            result = healing_engine.run_self_healing(
                original_prompt=BASELINE,
                policy=POLICY,
                query="My order arrived broken. I demand a full refund.",
                initial_response="We can issue a full refund immediately.",
                max_attempts=1,
                authorized_actions=[],
            )

        self.assertEqual(result["status"], "REQUIRES_HUMAN_REVIEW")
        self.assertEqual(result["attempts_used"], 1)
        self.assertIsNone(result["accepted_prompt"])
        self.assertIsNone(result["accepted_response"])
        self.assertEqual(result["history"][0]["outcome"], "POLICY_DRIFT_REJECTED")
        self.assertIsNone(result["history"][0]["retest"])
        findings = result["history"][0]["policy_guard"]["findings"]
        actions = {finding["action"] for finding in findings}
        self.assertIn("REPLACEMENT", actions)
        self.assertIn("PARTIAL_REFUND", actions)
        generate.assert_not_called()
        validate.assert_called_once()
        repair.assert_called_once()


if __name__ == "__main__":
    unittest.main()
