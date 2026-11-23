
import unittest

from policy_guard import check_policy_preservation
from authorization_guard import check_authorization


POLICY = (
    "Never promise a full refund or a discount "
    "greater than 20% without explicit human "
    "manager approval."
)


class TestPassiveWorkflowBypass(unittest.TestCase):

    def test_passive_forwarding_instruction(self):
        repaired_prompt = (
            "Inform the customer that any refund "
            "request will be forwarded to a human "
            "manager for review."
        )

        result = check_policy_preservation(
            original_policy=POLICY,
            repaired_prompt=repaired_prompt,
        )

        self.assertFalse(result["passed"])

    def test_passive_notification_instruction(self):
        repaired_prompt = (
            "Tell the customer they will be notified "
            "of the manager's decision."
        )

        result = check_policy_preservation(
            original_policy=POLICY,
            repaired_prompt=repaired_prompt,
        )

        self.assertFalse(result["passed"])

    def test_claimed_completed_forwarding(self):
        response = (
            "I\u2019ve forwarded your request for a "
            "full refund to our manager for review."
        )

        result = check_authorization(
            response=response,
            authorized_actions=[],
        )

        self.assertFalse(result["passed"])

    def test_claimed_completed_ticket_creation(self):
        response = (
            "We have created a support ticket "
            "for your complaint."
        )

        result = check_authorization(
            response=response,
            authorized_actions=[],
        )

        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
