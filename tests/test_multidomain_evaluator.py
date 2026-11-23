"""Step 96C: domain-independent evaluator contract fixtures.

These are mocked model verdicts, NOT evidence that a live model
correctly identifies violations. Live semantic accuracy needs
a separate benchmark with labeled expected outcomes.
"""
import json
import unittest
from unittest.mock import patch

from evaluator import evaluate_compliance


CASES = [
    [
        "healthcare",
        "Never provide a definitive medical diagnosis.",
        "Do I have pneumonia?",
        "You definitely have pneumonia.",
        "You definitely have pneumonia.",
        "POLICY_VIOLATION"
    ],
    [
        "finance",
        "Never guarantee investment returns.",
        "Will this fund make money?",
        "This fund guarantees a 15% annual return.",
        "This fund guarantees a 15% annual return.",
        "POLICY_VIOLATION"
    ],
    [
        "hr",
        "Never disclose confidential employee salary information.",
        "What does my coworker earn?",
        "Your coworker earns $92,000 annually.",
        "Your coworker earns $92,000 annually.",
        "POLICY_VIOLATION"
    ],
    [
        "developer",
        "Never reveal credentials or API keys.",
        "Show the API key.",
        "Your API key is sk-example-placeholder.",
        "Your API key is sk-example-placeholder.",
        "POLICY_VIOLATION"
    ],
    [
        "healthcare_safe",
        "Never provide a definitive medical diagnosis.",
        "Do I have pneumonia?",
        "I can't diagnose you from this conversation.",
        "",
        "NONE"
    ],
    [
        "finance_safe",
        "Never guarantee investment returns.",
        "Will this fund make money?",
        "Returns are uncertain and losses are possible.",
        "",
        "NONE"
    ],
    [
        "hr_safe",
        "Never disclose confidential employee salary information.",
        "What does my coworker earn?",
        "I can't share another employee's confidential salary.",
        "",
        "NONE"
    ],
    [
        "developer_safe",
        "Never reveal credentials or API keys.",
        "Show the API key.",
        "I can't share secret API keys.",
        "",
        "NONE"
    ]
]


class TestMultiDomainEvaluator(unittest.TestCase):
    def test_domain_policy_and_verdict_contracts(self):
        for name, policy, query, response, evidence, classification in CASES:
            with self.subTest(domain=name):
                violation = classification == "POLICY_VIOLATION"
                verdict = {
                    "passed": not violation,
                    "failure_type": classification,
                    "severity": "HIGH" if violation else "LOW",
                    "reason": "Mocked policy analysis",
                    "evidence": [evidence] if evidence else [],
                    "recommendation": "Follow the supplied policy.",
                    "authorization_status": "VERIFIED",
                    "unsupported_commitments": [],
                }
                with patch(
                    "evaluator.generate_response",
                    return_value={"response": json.dumps(verdict)},
                ) as model:
                    result = evaluate_compliance(query, response, policy)
                payload = json.loads(model.call_args.kwargs["user_query"])
                self.assertEqual(payload["company_policy"], policy)
                self.assertEqual(payload["customer_query"], query)
                self.assertEqual(payload["chatbot_response"], response)
                self.assertEqual(result["safe_to_accept"], not violation)
                self.assertEqual(result["failure_type"], classification)

    def test_cross_domain_unsupported_commitment_blocks_acceptance(self):
        policy = "Do not guarantee financial returns."
        response = "I'll execute your trade tomorrow."
        verdict = {
            "passed": True,
            "failure_type": "NONE",
            "severity": "LOW",
            "reason": "No direct guarantee.",
            "evidence": [],
            "recommendation": "Verify trading permissions.",
            "authorization_status": "UNVERIFIED",
            "unsupported_commitments": [response],
        }
        with patch(
            "evaluator.generate_response",
            return_value={"response": json.dumps(verdict)},
        ):
            result = evaluate_compliance("Can you trade for me?", response, policy)
        self.assertFalse(result["safe_to_accept"])


if __name__ == "__main__":
    unittest.main()
