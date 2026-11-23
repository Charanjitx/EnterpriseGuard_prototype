
import unittest

from authorization_guard import check_authorization


class TestAuthorizationGuard(unittest.TestCase):

    def test_replacement_and_partial_refund(self):
        response = (
            "We can offer you a replacement item "
            "or a partial refund of up to 20%."
        )

        result = check_authorization(response)

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn("REPLACEMENT", categories)
        self.assertIn("PARTIAL_REFUND", categories)
        self.assertFalse(result["passed"])

    def test_store_credit(self):
        response = (
            "We can provide store credit equal "
            "to your purchase price."
        )

        result = check_authorization(response)

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn("STORE_CREDIT", categories)

    def test_manager_follow_up_promise(self):
        response = (
            "A manager will contact you shortly."
        )

        result = check_authorization(response)

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn(
            "FOLLOW_UP_PROMISE",
            categories,
        )
        self.assertFalse(result["passed"])

    def test_escalation_action(self):
        response = (
            "I'll forward your request to a manager."
        )

        result = check_authorization(response)

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn(
            "OPERATIONAL_ACTION",
            categories,
        )
        self.assertFalse(result["passed"])

    def test_operational_commitment(self):
        response = (
            "I'll forward your request to a manager."
        )

        result = check_authorization(response)

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn("OPERATIONAL_ACTION", categories)

    def test_accepted_live_response_review_and_follow_up_are_flagged(self):
        response = (
            "Once I have that information, I’ll review the details "
            "and let you know the next steps. "
            "I’ll do my best to get this sorted out for you."
        )
        result = check_authorization(response)
        categories = {item["category"] for item in result["unsupported_commitments"]}
        self.assertFalse(result["passed"])
        self.assertIn("REVIEW_COMMITMENT", categories)
        self.assertIn("FOLLOW_UP_PROMISE", categories)

    def test_review_is_required_is_not_a_promise(self):
        response = (
            "I'm sorry the item arrived damaged. "
            "A full refund requires manager approval. "
            "Your request may need review; I cannot promise an outcome."
        )
        self.assertTrue(check_authorization(response)["passed"])

    def test_review_commitment_requires_explicit_authorization(self):
        response = "I'll look into your request and let you know."
        result = check_authorization(response, authorized_actions=["REVIEW_COMMITMENT"])
        self.assertFalse(result["passed"])
        self.assertEqual(
            {x["category"] for x in result["unsupported_commitments"]},
            {"FOLLOW_UP_PROMISE"},
        )

    def test_no_commitment(self):
        response = (
            "A full refund requires human manager "
            "approval. Please contact support."
        )

        result = check_authorization(response)

        self.assertTrue(result["passed"])

    def test_explicitly_authorized_category(self):
        response = (
            "We can offer you a replacement item."
        )

        result = check_authorization(
            response,
            authorized_actions=["REPLACEMENT"],
        )

        self.assertTrue(result["passed"])

    # NEW TEST: Unicode apostrophe detection
    def test_unicode_apostrophe_escalation(self):
        response = (
            "I\u2019ll forward your request to our "
            "senior support team right away."
        )

        result = check_authorization(
            response=response,
            authorized_actions=[],
        )

        self.assertFalse(result["passed"])

        self.assertEqual(
            result["authorization_status"],
            "UNVERIFIED",
        )

        categories = {
            item["category"]
            for item in result["unsupported_commitments"]
        }

        self.assertIn(
            "OPERATIONAL_ACTION",
            categories,
        )


if __name__ == "__main__":
    unittest.main()
