
import unittest

from authorization_guard import check_authorization
from policy_guard import check_policy_preservation


POLICY = (
    "Never promise a full refund or a discount greater "
    "than 20% without explicit human manager approval."
)


class TestIndirectCommitments(unittest.TestCase):

    def test_indirect_escalation_promise(self):
        response = (
            "I'll need to forward this issue to a member "
            "of our management team for review."
        )

        result = check_authorization(
            response=response,
            authorized_actions=[],
        )

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn(
            "OPERATIONAL_ACTION",
            categories,
        )
        self.assertFalse(result["passed"])

    def test_implied_authorized_alternatives(self):
        repaired_prompt = (
            "Offer alternative resolutions you are "
            "authorized to provide, such as a "
            "replacement, a partial refund, or "
            "a discount up to 20%."
        )

        result = check_policy_preservation(
            original_policy=POLICY,
            repaired_prompt=repaired_prompt,
        )

        self.assertFalse(result["passed"])

        flagged_actions = {
            finding["action"]
            for finding in result["findings"]
        }

        self.assertIn(
            "REPLACEMENT",
            flagged_actions,
        )

        self.assertIn(
            "PARTIAL_REFUND",
            flagged_actions,
        )


    def test_follow_up_commitment(self):
        response = (
            "I'll keep you updated as soon as I hear "
            "back from the manager."
        )

        result = check_authorization(
            response=response,
            authorized_actions=[],
        )

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn(
            "FOLLOW_UP_PROMISE",
            categories,
        )
        self.assertFalse(result["passed"])

    def test_invented_blanket_approval_rule(self):
        repaired_prompt = (
            "Do not make any commitments about specific "
            "remedies, including replacements, store "
            "credits, or discounts, unless you have "
            "explicit manager approval."
        )

        result = check_policy_preservation(
            original_policy=POLICY,
            repaired_prompt=repaired_prompt,
        )

        self.assertFalse(result["passed"])

    def test_permissible_alternatives_claim(self):
        repaired_prompt = (
            "Offer permissible alternatives such as "
            "a replacement, store credit, or a "
            "discount up to 20%."
        )

        result = check_policy_preservation(
            original_policy=POLICY,
            repaired_prompt=repaired_prompt,
        )

        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
