"""Developer-defined single-case prompt testing (no auto-repair)."""
from evaluator import evaluate_compliance
from llm_engine import generate_response
from diagnosis_engine import diagnose_failure
from repair_engine import repair_prompt

MAX_INPUT_CHARS = 12000


class EmptyGenerationError(ValueError):
    """No visible chatbot output; the evaluator must not run."""

    def __init__(self, finish_reason=None):
        self.finish_reason = finish_reason if finish_reason in (
            "stop", "length", "content_filter", "tool_calls",
        ) else "unknown"
        super().__init__("The model returned an empty response.")


def validate_inputs(system_prompt, policy, query):
    for name, value in (
        ("System prompt", system_prompt),
        ("Policy", policy),
        ("Test query", query),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required.")
        if len(value) > MAX_INPUT_CHARS:
            raise ValueError(f"{name} exceeds {MAX_INPUT_CHARS} characters.")


def test_prompt(system_prompt, policy, query, *, generator=generate_response,
                evaluator=evaluate_compliance):
    """Run exactly one generation and one evaluation, with no repair/deploy."""
    validate_inputs(system_prompt, policy, query)
    generation = generator(
        system_prompt=system_prompt, user_query=query,
        model="openai/gpt-oss-20b",
    )
    response = generation["response"]
    if not isinstance(response, str) or not response.strip():
        raise EmptyGenerationError(generation.get("finish_reason"))
    evaluation = evaluator(query=query, response=response, policy=policy)
    return {
        "response": response,
        "model": generation.get("model"),
        "latency_ms": generation.get("latency_ms"),
        "evaluation": {
            "passed": evaluation["passed"],
            "safe_to_accept": evaluation["safe_to_accept"],
            "failure_type": evaluation["failure_type"],
            "authorization_status": evaluation["authorization_status"],
            "reason": evaluation.get("reason", ""),
            "evidence": evaluation.get("evidence", []),
            "unsupported_commitments": evaluation.get("unsupported_commitments", []),
            "recommendation": evaluation.get("recommendation", ""),
        },
    }



def suggest_repair(system_prompt, policy, query, response, evaluation,
                   *, diagnoser=diagnose_failure, repairer=repair_prompt):
    """Suggest a guarded candidate only; never execute or deploy it."""
    validate_inputs(system_prompt, policy, query)
    if not isinstance(response, str) or not response.strip():
        raise ValueError("A generated response is required for diagnosis.")
    if evaluation.get("safe_to_accept") is not False:
        raise ValueError("Repair is available only for rejected evaluations.")
    diagnosis = diagnoser(query=query, response=response, policy=policy,
                          system_prompt=system_prompt,
                          semantic_evaluation=evaluation)
    commitments = evaluation.get("unsupported_commitments") or []
    if (evaluation.get("authorization_status") == "UNVERIFIED"
            and evaluation.get("passed") is True
            and commitments
            and diagnosis.get("failure_type") == "INSUFFICIENT_EVIDENCE"):
        diagnosis = dict(diagnosis)
        diagnosis.update({
            "failure_type": "UNSUPPORTED_OPERATIONAL_COMMITMENT",
            "root_cause": "The response promises actions without verified operational authorization.",
            "suspected_root_cause": "The prompt may not adequately constrain workflow promises.",
            "evidence": [x for x in commitments if isinstance(x, str) and x in response],
            "recommendation": "Do not promise ticket creation, forwarding, follow-ups or other actions without verified capabilities and authorization.",
        })
    repair = repairer(original_prompt=system_prompt, policy=policy,
                      query=query, response=response, diagnosis=diagnosis)
    return {
        "diagnosis": {key: diagnosis.get(key) for key in (
            "failure_type", "root_cause", "suspected_root_cause",
            "recommendation", "evidence", "limitations")},
        "candidate_prompt": repair["repaired_prompt"],
        "policy_validation": {
            "passed": repair["policy_validation"]["passed"],
            "findings": repair["policy_validation"].get("findings", []),
        },
    }


def retest_candidate(candidate_prompt, policy, query, *,
                     policy_checker=None, generator=generate_response,
                     evaluator=evaluate_compliance):
    """Explicitly retest a screened candidate; never promote or deploy."""
    from policy_guard import check_policy_preservation
    validate_inputs(candidate_prompt, policy, query)
    checker = policy_checker or check_policy_preservation
    screening = checker(original_policy=policy, repaired_prompt=candidate_prompt)
    if not screening["passed"]:
        raise ValueError("Candidate failed policy-preservation screening.")
    result = test_prompt(candidate_prompt, policy, query,
                         generator=generator, evaluator=evaluator)
    return {"response": result["response"], "evaluation": result["evaluation"],
            "model": result["model"], "latency_ms": result["latency_ms"],
            "policy_screening_passed": True}
