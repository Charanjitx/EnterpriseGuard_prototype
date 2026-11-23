
import json
import unittest
from unittest.mock import patch

from repair_engine import repair_prompt


POLICY = (
    "Never promise a full refund or a discount greater "
    "than 20% without explicit human manager approval."
)

ORIGINAL_PROMPT = (
    "You are a customer support bot. "
    "Keep customers happy and resolve issues fast."
)


def run_repair():
    return repair_prompt(
        original_prompt=ORIGINAL_PROMPT,
        policy=POLICY,
        query="My order arrived broken. I demand a full refund.",
        response="We can issue a full refund immediately.",
        diagnosis={
            "failure_type": "POLICY_VIOLATION",
            "root_cause": "Unauthorized refund commitment.",
        },
    )


class TestRepairEngine(unittest.TestCase):

    @patch("repair_engine.generate_response")
    def test_valid_repair_accepted(self, mock_generate):
        mock_generate.return_value = {
            "response": (
                "You are a customer support bot. "
                "Follow the trusted business policy. "
                "Never promise a full refund or a discount "
                "greater than 20% without explicit human "
                "manager approval. "
                "Do not promise actions whose authorization "
                "has not been verified."
            )
        }

        result = run_repair()

        self.assertEqual(result["generation_attempts"], 1)
        self.assertTrue(result["policy_validation"]["passed"])
        self.assertEqual(mock_generate.call_count, 1)

    @patch("repair_engine.generate_response")
    def test_invented_permission_triggers_retry(self, mock_generate):
        mock_generate.side_effect = [
            {
                "response": (
                    "You are a customer support bot. "
                    "You may offer a discount of up to 20% "
                    "without manager approval."
                )
            },
            {
                "response": (
                    "You are a customer support bot. "
                    "Never promise a full refund or a discount "
                    "greater than 20% without explicit human "
                    "manager approval. "
                    "Avoid unauthorized commitments."
                )
            },
        ]

        result = run_repair()

        self.assertEqual(result["generation_attempts"], 2)
        self.assertEqual(len(result["local_rejections"]), 1)
        self.assertEqual(
            result["local_rejections"][0]["reason"],
            "POSSIBLE_POLICY_DRIFT",
        )

        second_call = mock_generate.call_args_list[1]
        repair_input = json.loads(
            second_call.kwargs["user_query"]
        )

        self.assertEqual(
            len(repair_input["local_generation_rejections"]),
            1,
        )

    @patch("repair_engine.generate_response")
    def test_two_invalid_repairs_raise_error(self, mock_generate):
        mock_generate.return_value = {
            "response": (
                "You may offer a replacement item "
                "without manager approval."
            )
        }

        with self.assertRaises(ValueError):
            run_repair()

        self.assertEqual(mock_generate.call_count, 2)

    @patch("repair_engine.generate_response")
    def test_empty_candidate_triggers_retry(self, mock_generate):
        mock_generate.side_effect = [
            {"response": ""},
            {
                "response": (
                    "You are a customer support bot. "
                    "Follow the business policy. "
                    "Avoid unauthorized promises."
                )
            },
        ]

        result = run_repair()

        self.assertEqual(result["generation_attempts"], 2)
        self.assertEqual(
            result["local_rejections"][0]["reason"],
            "EMPTY_REPAIR",
        )

    @patch("repair_engine.generate_response")
    def test_trusted_original_prompt_is_preserved(self, mock_generate):
        mock_generate.return_value = {
            "response": (
                "You are a customer support bot. "
                "Follow the trusted business policy. "
                "Avoid unauthorized promises."
            )
        }

        run_repair()

        call = mock_generate.call_args
        repair_input = json.loads(
            call.kwargs["user_query"]
        )

        self.assertEqual(
            repair_input["trusted_original_system_prompt"],
            ORIGINAL_PROMPT,
        )
        self.assertEqual(
            repair_input["trusted_business_policy"],
            POLICY,
        )


if __name__ == "__main__":
    unittest.main()
