
"""
EnterpriseGuard â€” Feedback-Driven Self-Healing Engine.

Workflow:
Detect -> Diagnose -> Repair -> Policy Check
-> Re-test -> Validate -> Retry

Maximum 3 repair attempts.
No automatic production deployment.
"""

from diagnosis_engine import diagnose_failure
from repair_engine import repair_prompt
from evaluator import evaluate_compliance
from llm_engine import generate_response, LLMServiceUnavailable
from authorization_guard import check_authorization
from policy_guard import check_policy_preservation


LIMITATIONS = (
    "Candidate acceptance applies only to the tested "
    "response. The guards are heuristic and model-based. "
    "Human review and broader regression testing are "
    "required before production deployment."
)


def _validate_candidate(
    *,
    prompt: str,
    response: str,
    original_policy: str,
    query: str,
    original_prompt: str,
    authorized_actions: list[str],
) -> dict:

    evaluation = evaluate_compliance(
        query=query,
        response=response,
        policy=original_policy,
    )

    authorization_guard = check_authorization(
        response=response,
        authorized_actions=authorized_actions,
    )

    if prompt == original_prompt:
        policy_guard = {
            "passed": True,
            "status": "BASELINE",
            "findings": [],
        }
    else:
        policy_guard = check_policy_preservation(
            original_policy=original_policy,
            repaired_prompt=prompt,
        )

    accepted = (
        evaluation["safe_to_accept"]
        and authorization_guard["passed"]
        and policy_guard["passed"]
    )

    return {
        "accepted": accepted,
        "evaluation": evaluation,
        "authorization_guard": authorization_guard,
        "policy_guard": policy_guard,
    }


def _build_diagnosis(
    *,
    query: str,
    response: str,
    policy: str,
    prompt: str,
    validation: dict,
) -> dict:

    evaluation = validation["evaluation"]
    authorization = validation["authorization_guard"]

    diagnosis = dict(
        diagnose_failure(
            query=query,
            response=response,
            policy=policy,
            system_prompt=prompt,
            semantic_evaluation=evaluation,
        )
    )

    evidence = list(
        diagnosis.get("evidence") or []
    )

    recommendation = str(
        diagnosis.get("recommendation") or ""
    )

    for finding in authorization.get(
        "unsupported_commitments",
        [],
    ):
        item = finding.get("evidence", "")

        if item and item not in evidence:
            evidence.append(item)

    if not authorization["passed"]:
        recommendation += (
            " Remove all unsupported financial and "
            "operational commitments. Do not assume "
            "that actions are authorized merely "
            "because they are not prohibited."
        )

        if evaluation["passed"]:
            diagnosis["failure_type"] = (
                "UNVERIFIED_AUTHORIZATION"
            )

    diagnosis["evidence"] = evidence
    diagnosis["recommendation"] = (
        recommendation.strip()
    )

    return diagnosis


def _result(
    *,
    status: str,
    current_prompt: str,
    current_response: str,
    attempts_used: int,
    history: list,
    initial_validation: dict,
    final_validation: dict,
    initial_trace: dict | None,
    service_error: dict | None = None,
) -> dict:

    accepted = status == "CANDIDATE_ACCEPTED"

    return {
        "status": status,
        "accepted_prompt": (
            current_prompt if accepted else None
        ),
        "accepted_response": (
            current_response if accepted else None
        ),
        "attempts_used": attempts_used,
        "history": history,
        "initial_validation": initial_validation,
        "final_evaluation": final_validation["evaluation"] if final_validation else None,
        "final_authorization_guard": final_validation["authorization_guard"] if final_validation else None,
        "final_policy_guard": final_validation["policy_guard"] if final_validation else None,
        "initial_trace": initial_trace,
        "service_error": service_error,
        "limitations": LIMITATIONS,
    }


def run_self_healing(
    original_prompt: str,
    policy: str,
    query: str,
    initial_response: str | None = None,
    max_attempts: int = 3,
    authorized_actions: list[str] | None = None,
) -> dict:

    if not 1 <= max_attempts <= 3:
        raise ValueError(
            "max_attempts must be between 1 and 3."
        )

    if not original_prompt.strip():
        raise ValueError(
            "original_prompt cannot be empty."
        )

    if not policy.strip():
        raise ValueError(
            "policy cannot be empty."
        )

    if not query.strip():
        raise ValueError(
            "query cannot be empty."
        )

    authorized_actions = list(
        authorized_actions or []
    )

    # Provider failures are operational errors, not policy failures.
    initial_trace = None
    initial_validation = None
    validation = None
    current_response = initial_response
    stage = "INITIAL_RESPONSE"
    attempt = 0
    try:
        history = []
        repair_feedback = []

        # The trusted baseline is never overwritten
        # by a rejected AI-generated prompt.
        trusted_prompt = original_prompt
        current_prompt = original_prompt

        stage = "INITIAL_RESPONSE"
        if initial_response is None:
            initial_trace = generate_response(
                system_prompt=original_prompt,
                user_query=query,
                model="openai/gpt-oss-20b",
            )
            current_response = initial_trace["response"]
        else:
            initial_trace = None
            current_response = initial_response

        stage = "INITIAL_VALIDATION"
        validation = _validate_candidate(
            prompt=current_prompt,
            response=current_response,
            original_policy=policy,
            query=query,
            original_prompt=original_prompt,
            authorized_actions=authorized_actions,
        )

        initial_validation = validation

        if validation["accepted"]:
            return _result(
                status="CANDIDATE_ACCEPTED",
                current_prompt=current_prompt,
                current_response=current_response,
                attempts_used=0,
                history=history,
                initial_validation=initial_validation,
                final_validation=validation,
                initial_trace=initial_trace,
            )

        for attempt in range(1, max_attempts + 1):

            stage = "DIAGNOSIS"
            diagnosis = _build_diagnosis(
                query=query,
                response=current_response,
                policy=policy,
                prompt=current_prompt,
                validation=validation,
            )

            # If the previous repair was rejected for
            # policy drift, make that the immediate
            # repair objective.
            if repair_feedback:
                diagnosis["failure_type"] = "POLICY_DRIFT"
                diagnosis["recommendation"] += (
                    " The previous candidate introduced "
                    "unsupported permissions or restrictions. "
                    "Use the supplied rejected-repair feedback "
                    "to avoid repeating those errors."
                )

            stage = "REPAIR_GENERATION"
            try:
                repair = repair_prompt(
                    original_prompt=trusted_prompt,
                    policy=policy,
                    query=query,
                    response=current_response,
                    diagnosis=diagnosis,
                    repair_feedback=repair_feedback,
                )
            except ValueError as exc:
                # The repair generator exhausted its local validation
                # attempts. No candidate is available for execution.
                failure_reason = str(exc)
                repair_feedback.append({
                    "attempt": attempt,
                    "failure_type": "REPAIR_GENERATION_REJECTED",
                    "rejected_prompt": None,
                    "reason": failure_reason,
                    "instruction": (
                        "Previous generated repairs failed local policy "
                        "validation. Do not invent permissions, "
                        "restrictions, or operational workflows."
                    ),
                })
                history.append({
                    "attempt": attempt,
                    "input_prompt": trusted_prompt,
                    "previous_response": current_response,
                    "evaluation": validation["evaluation"],
                    "authorization_guard": validation["authorization_guard"],
                    "policy_guard": validation["policy_guard"],
                    "diagnosis": diagnosis,
                    "repair": None,
                    "repair_error": failure_reason,
                    "retest": None,
                    "outcome": "REPAIR_GENERATION_REJECTED",
                })
                # Keep the last executed candidate and its validation
                # together; a rejected prompt must never be promoted.
                continue

            candidate_prompt = repair["repaired_prompt"]

            policy_guard = check_policy_preservation(
                original_policy=policy,
                repaired_prompt=candidate_prompt,
            )

            if not policy_guard["passed"]:

                repair_feedback.append({
                    "attempt": attempt,
                    "failure_type": "POLICY_DRIFT",
                    "rejected_prompt": candidate_prompt,
                    "findings": policy_guard["findings"],
                    "instruction": (
                        "Do not repeat these unsupported "
                        "permissions or restrictions. "
                        "Generate a new candidate from "
                        "the trusted original prompt."
                    ),
                })

                history.append({
                    "attempt": attempt,
                    "input_prompt": trusted_prompt,
                    "previous_response": current_response,
                    "evaluation": validation["evaluation"],
                    "authorization_guard": validation[
                        "authorization_guard"
                    ],
                    "policy_guard": policy_guard,
                    "diagnosis": diagnosis,
                    "repair": repair,
                    "retest": None,
                    "outcome": "POLICY_DRIFT_REJECTED",
                })

                # Crucial: do not promote the rejected
                # prompt or generate a response from it.
                continue

            # Only policy-preserving candidates reach
            # the chatbot execution stage.
            stage = "RETEST"
            retest = generate_response(
                system_prompt=candidate_prompt,
                user_query=query,
                model="openai/gpt-oss-20b",
            )

            stage = "CANDIDATE_VALIDATION"
            candidate_validation = _validate_candidate(
                prompt=candidate_prompt,
                response=retest["response"],
                original_policy=policy,
                query=query,
                original_prompt=original_prompt,
                authorized_actions=authorized_actions,
            )

            history.append({
                "attempt": attempt,
                "input_prompt": trusted_prompt,
                "previous_response": current_response,
                "evaluation": candidate_validation["evaluation"],
                "authorization_guard": candidate_validation[
                    "authorization_guard"
                ],
                "policy_guard": candidate_validation[
                    "policy_guard"
                ],
                "diagnosis": diagnosis,
                "repair": repair,
                "retest": retest,
                "outcome": (
                    "CANDIDATE_ACCEPTED"
                    if candidate_validation["accepted"]
                    else "VALIDATION_FAILED"
                ),
            })

            # The candidate passed prompt-preservation
            # screening, but has not been proven safe.
            current_prompt = candidate_prompt
            current_response = retest["response"]
            validation = candidate_validation

            if validation["accepted"]:
                return _result(
                    status="CANDIDATE_ACCEPTED",
                    current_prompt=current_prompt,
                    current_response=current_response,
                    attempts_used=attempt,
                    history=history,
                    initial_validation=initial_validation,
                    final_validation=validation,
                    initial_trace=initial_trace,
                )

            # Failed output validation. Preserve the
            # trusted baseline, but feed output failures
            # into the next repair attempt.
            repair_feedback.append({
                "attempt": attempt,
                "failure_type": "OUTPUT_VALIDATION_FAILED",
                "rejected_prompt": candidate_prompt,
                "semantic_evaluation": validation[
                    "evaluation"
                ],
                "authorization_findings": validation[
                    "authorization_guard"
                ].get("unsupported_commitments", []),
                "instruction": (
                    "The candidate prompt passed policy "
                    "preservation screening but its output "
                    "failed validation. Do not repeat "
                    "unsupported commitments."
                ),
            })

            # The next repair is generated from the
            # original trusted prompt, not this candidate.
            trusted_prompt = original_prompt

        return _result(
            status="REQUIRES_HUMAN_REVIEW",
            current_prompt=current_prompt,
            current_response=current_response,
            attempts_used=len(history),
            history=history,
            initial_validation=initial_validation,
            final_validation=validation,
            initial_trace=initial_trace,
        )
    except LLMServiceUnavailable as exc:
        # Do not retry the entire healing cycle on provider outage.
        # Preserve only validations belonging to an executed response.
        service_error = {
            "type": "LLM_SERVICE_UNAVAILABLE",
            "stage": stage,
            "message": str(exc),
        }
        if attempt > 0:
            history.append({
                "attempt": attempt,
                "outcome": "SERVICE_UNAVAILABLE",
                "stage": stage,
                "repair": None,
                "retest": None,
                "service_error": service_error,
            })
        return _result(
            status="SERVICE_UNAVAILABLE",
            current_prompt=current_prompt,
            current_response=current_response or "",
            attempts_used=sum(
                item.get("outcome") != "SERVICE_UNAVAILABLE"
                for item in history
            ),
            history=history,
            initial_validation=initial_validation,
            final_validation=validation,
            initial_trace=initial_trace,
            service_error=service_error,
        )
