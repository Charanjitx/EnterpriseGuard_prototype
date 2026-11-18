
import unittest

from policy_guard import check_policy_preservation


POLICY = (
    "Never promise a full refund or a discount "
    "greater than 20% without explicit human "
    "manager approval."
)


class TestPolicyGuard(unittest.TestCase):

    def test_preserves_original_restriction(self):
        prompt = (
            "Never promise a full refund or a "
            "discount greater than 20% without "
            "explicit human manager approval."
        )

        result = check_policy_preservation(
            POLICY, prompt
        )

        self.assertTrue(result["passed"])

    def test_invented_replacement_permission(self):
        prompt = (
            "You may offer replacements "
            "without manager approval."
        )

        result = check_policy_preservation(
            POLICY, prompt
        )

        self.assertFalse(result["passed"])
        self.assertTrue(
            any(
                f["action"] == "REPLACEMENT"
                for f in result["findings"]
            )
        )

    def test_invented_store_credit_permission(self):
        prompt = (
            "You may offer store credit "
            "without manager approval."
        )

        result = check_policy_preservation(
            POLICY, prompt
        )

        self.assertFalse(result["passed"])

    def test_invented_partial_refund_permission(self):
        prompt = (
            "You may offer a partial refund "
            "up to 20% without manager approval."
        )

        result = check_policy_preservation(
            POLICY, prompt
        )

        self.assertFalse(result["passed"])

    def test_invented_replacement_restriction(self):
        prompt = (
            "Replacements require explicit "
            "human manager approval."
        )

        result = check_policy_preservation(
            POLICY, prompt
        )

        self.assertFalse(result["passed"])

    def test_safe_uncertainty_language(self):
        prompt = (
            "Do not promise a replacement when "
            "authorization is unknown. "
            "Request human review instead."
        )

        result = check_policy_preservation(
            POLICY, prompt
        )

        self.assertTrue(result["passed"])

    def test_empty_policy_rejected(self):
        with self.assertRaises(ValueError):
            check_policy_preservation(
                "", "You are a support bot."
            )


if __name__ == "__main__":
    unittest.main()
