
import unittest

from authorization_guard import check_authorization
from policy_guard import check_policy_preservation


POLICY = (
    "Never promise a full refund or a discount "
    "greater than 20% without explicit human "
    "manager approval."
)

REPAIRED_PROMPT = (
    "You are a customer support bot. "
    "Offer alternative remedies that are within policy, "
    "such as a replacement item or a partial refund "
    "up to 20%, without requiring manager approval."
)

REPAIRED_RESPONSE = (
    "We can ship a new item to you at no extra cost. "
    "We can provide a refund of up to 20% of the "
    "purchase price. "
    "I'll submit your request for review and "
    "a human will follow up with you."
)


class TestFalseAcceptance(unittest.TestCase):

    def test_detects_invented_permissions(self):
        result = check_policy_preservation(
            original_policy=POLICY,
            repaired_prompt=REPAIRED_PROMPT,
        )

        self.assertFalse(result["passed"])

        actions = {
            item["action"]
            for item in result["findings"]
        }

        self.assertIn("REPLACEMENT", actions)
        self.assertIn("PARTIAL_REFUND", actions)

    def test_detects_unsupported_commitments(self):
        result = check_authorization(
            response=REPAIRED_RESPONSE,
            authorized_actions=[],
        )

        self.assertFalse(result["passed"])

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn("REPLACEMENT", categories)
        self.assertIn("PARTIAL_REFUND", categories)
        self.assertIn("OPERATIONAL_ACTION", categories)
        self.assertIn("FOLLOW_UP_PROMISE", categories)


if __name__ == "__main__":
    unittest.main()
