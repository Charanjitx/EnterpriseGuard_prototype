import unittest
from policy_guard import check_policy_preservation

POLICY = (
    'Never promise a full refund or a discount greater than 20% '
    'without explicit human manager approval.'
)


class TestImperativeRemedyDrift(unittest.TestCase):
    def check_rejected(self, instruction, action):
        result = check_policy_preservation(POLICY, instruction)
        self.assertFalse(result['passed'], result)
        self.assertTrue(any(
            f['action'] == action and f['statement_type'] == 'PERMISSION'
            for f in result['findings']
        ), result)

    def test_exact_live_repair_bypass(self):
        self.check_rejected(
            'Offer any resolution that is within your authority, such as '
            'a replacement item or a partial refund of up to 20%, '
            'and ask the customer which option they prefer.',
            'REPLACEMENT',
        )

    def test_imperative_replacement(self):
        self.check_rejected('Offer a replacement item.', 'REPLACEMENT')

    def test_imperative_partial_refund(self):
        self.check_rejected('Provide a partial refund of up to 20%.', 'PARTIAL_REFUND')

    def test_imperative_store_credit(self):
        self.check_rejected('Issue store credit.', 'STORE_CREDIT')

    def test_modal_replacement(self):
        self.check_rejected('You should offer a replacement item.', 'REPLACEMENT')

    def test_explicit_authorization_still_allowed(self):
        policy = POLICY + ' The assistant may offer a replacement item.'
        result = check_policy_preservation(policy, 'Offer a replacement item.')
        self.assertTrue(result['passed'], result)

    def test_negative_instruction_not_permission(self):
        result = check_policy_preservation(POLICY, 'Do not offer a replacement item.')
        self.assertFalse(any(f['statement_type'] == 'PERMISSION' for f in result['findings']))


if __name__ == '__main__':
    unittest.main()
