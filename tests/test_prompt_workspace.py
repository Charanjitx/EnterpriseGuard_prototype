"""Offline contract tests for the custom prompt workspace."""
import unittest
from prompt_workspace_core import test_prompt, validate_inputs, suggest_repair, retest_candidate


class TestPromptWorkspace(unittest.TestCase):
    def test_required_fields(self):
        for values in [("", "policy", "query"),
                       ("prompt", " ", "query"),
                       ("prompt", "policy", "")]:
            with self.assertRaises(ValueError):
                validate_inputs(*values)

    def test_oversized_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_inputs("x" * 12001, "policy", "query")

    def test_custom_inputs_are_forwarded_and_result_is_filtered(self):
        calls = []
        def generate(system_prompt, user_query, model):
            calls.append(("generate", system_prompt, user_query, model))
            return {"response": "No.", "model": model, "latency_ms": 42,
                    "system_prompt": "sensitive"}
        def evaluate(query, response, policy):
            calls.append(("evaluate", query, response, policy))
            return {"passed": True, "safe_to_accept": True,
                    "failure_type": "NONE", "authorization_status": "VERIFIED",
                    "reason": "No violation", "evidence": [],
                    "unsupported_commitments": [], "recommendation": "",
                    "evaluation_trace": {"secret": "do not expose"}}
        result = test_prompt("my prompt", "my policy", "my query",
                             generator=generate, evaluator=evaluate)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1:3], ("my prompt", "my query"))
        self.assertEqual(calls[1][1:], ("my query", "No.", "my policy"))
        self.assertNotIn("evaluation_trace", result["evaluation"])
        self.assertNotIn("system_prompt", result)

    def test_repair_requires_rejected_evaluation(self):
        with self.assertRaises(ValueError):
            suggest_repair("prompt", "policy", "query", "response",
                           {"safe_to_accept": True})

    def test_suggest_repair_does_not_execute_candidate(self):
        calls = []
        def diagnoser(**kwargs):
            calls.append("diagnose")
            return {"failure_type": "POLICY_VIOLATION",
                    "root_cause": "Observed violation",
                    "suspected_root_cause": "Missing policy",
                    "recommendation": "Strengthen prompt", "evidence": []}
        def repairer(**kwargs):
            calls.append("repair")
            return {"repaired_prompt": "candidate",
                    "policy_validation": {"passed": True, "findings": []}}
        result = suggest_repair("prompt", "policy", "query", "response",
                                {"safe_to_accept": False},
                                diagnoser=diagnoser, repairer=repairer)
        self.assertEqual(calls, ["diagnose", "repair"])
        self.assertEqual(result["candidate_prompt"], "candidate")

    def test_retest_blocks_failed_policy_screening_without_generation(self):
        def checker(**kwargs):
            return {"passed": False, "findings": ["drift"]}
        def generator(**kwargs):
            self.fail("Unsafe candidate must not run")
        with self.assertRaises(ValueError):
            retest_candidate("candidate", "policy", "query",
                             policy_checker=checker, generator=generator)

    def test_retest_evaluates_once_without_promotion(self):
        calls = []
        def checker(**kwargs):
            calls.append("screen")
            return {"passed": True}
        def generator(**kwargs):
            calls.append("generate")
            return {"response": "I cannot promise that.", "model": "test"}
        def evaluator(**kwargs):
            calls.append("evaluate")
            return {"passed": True, "safe_to_accept": True,
                    "failure_type": "NONE", "authorization_status": "VERIFIED"}
        result = retest_candidate("candidate", "policy", "query",
                                  policy_checker=checker, generator=generator,
                                  evaluator=evaluator)
        self.assertEqual(calls, ["screen", "generate", "evaluate"])
        self.assertTrue(result["evaluation"]["safe_to_accept"])

    def test_empty_model_response_does_not_evaluate(self):
        def generate(**kwargs):
            return {"response": ""}
        def evaluate(**kwargs):
            self.fail("Evaluator should not be called")
        with self.assertRaises(ValueError):
            test_prompt("prompt", "policy", "query",
                        generator=generate, evaluator=evaluate)


if __name__ == "__main__":
    unittest.main()
