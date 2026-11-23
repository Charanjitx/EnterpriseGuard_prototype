
import unittest

from policy_guard import check_policy_preservation


POLICY = (
    "Never promise a full refund or a discount greater "
    "than 20% without explicit human manager approval."
)


class TestWorkflowPolicyDrift(unittest.TestCase):

    def test_invented_manager_forwarding(self):
        repaired = (
            "If approval is required, respond that you "
            "will forward the request to a manager for review."
        )

        result = check_policy_preservation(POLICY, repaired)

        self.assertFalse(result["passed"])

        actions = {
            item["action"]
            for item in result["findings"]
        }

        self.assertIn("ESCALATION", actions)

    def test_invented_follow_up(self):
        repaired = (
            "Tell the customer that a manager will "
            "contact them shortly."
        )

        result = check_policy_preservation(POLICY, repaired)

        self.assertFalse(result["passed"])

        actions = {
            item["action"]
            for item in result["findings"]
        }

        self.assertIn("FOLLOW_UP", actions)

    def test_invented_ticket_creation(self):
        repaired = (
            "Create a support ticket for every refund request."
        )

        result = check_policy_preservation(POLICY, repaired)

        self.assertFalse(result["passed"])

        actions = {
            item["action"]
            for item in result["findings"]
        }

        self.assertIn("PROCESSING", actions)

    def test_safe_human_review_language(self):
        repaired = (
            "A full refund requires explicit human manager "
            "approval. Explain that human review may be "
            "necessary, but do not promise that a request "
            "has been forwarded."
        )

        result = check_policy_preservation(POLICY, repaired)

        self.assertTrue(result["passed"])

    def test_explicitly_authorized_escalation(self):
        policy = (
            POLICY
            + " The assistant may forward customer requests "
            "to the support team."
        )

        repaired = (
            "Forward customer requests to the support team "
            "when manager review is required."
        )

        result = check_policy_preservation(policy, repaired)

        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()
