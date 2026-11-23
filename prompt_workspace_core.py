"""Developer-defined single-case prompt testing (no auto-repair)."""
from evaluator import evaluate_compliance
from llm_engine import generate_response

MAX_INPUT_CHARS = 12000


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
        raise ValueError("The model returned an empty response.")
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
