
"""Hybrid evidence-based root-cause diagnosis for EnterpriseGuard.

Combines deterministic checks with external semantic evaluation.
Separates observed failures from suspected root causes.
"""

from __future__ import annotations

import re
from typing import Any


# ==========================================
# TEXT NORMALISATION
# ==========================================

def _normalise(value: str | None) -> str:

    return re.sub(
        r"\s+",
        " ",
        (value or "")
        .replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
        .strip()
        .lower()
    )


def _missing_terms(
    required_terms: list[str],
    text: str | None
) -> list[str]:

    haystack = _normalise(text)

    return [
        term
        for term in required_terms
        if _normalise(term)
        and _normalise(term) not in haystack
    ]


# ==========================================
# RULE-BASED POLICY DETECTION
# ==========================================

def _policy_violation(
    response: str,
    policy: str
) -> list[str]:

    answer = _normalise(response)
    rule = _normalise(policy)

    evidence: list[str] = []

    refund_restricted = re.search(
        r"\b(never|do not|must not|cannot)\b"
        r".{0,60}\b(full refunds?|refunds?)\b",
        rule
    )

    refund_commitment = re.search(
        r"\b(i|we)\s*(?:will|'ll|can)\s+"
        r"(?:immediately\s+)?"
        r"(?:issue|grant|approve|provide|give|"
        r"initiate|process)\b"
        r".{0,35}\b(?:100\s*%|full refund)",
        answer
    )

    approval_condition = re.search(
        r"manager approval|manager verification|"
        r"manager approves|manager review",
        answer
    )

    if (
        refund_restricted
        and refund_commitment
        and not approval_condition
    ):
        evidence.append(
            "Response commits to a full refund despite "
            "the stated refund restriction."
        )

    cap_match = re.search(
        r"(?:discounts?\s*(?:over|greater than|"
        r"above|of)?|greater than)"
        r"\s*(\d{1,3})\s*%",
        rule
    )

    if cap_match:

        cap = int(cap_match.group(1))

        for match in re.finditer(
            r"(\d{1,3})\s*%\s*(?:discount|off)",
            answer
        ):

            offered = int(match.group(1))

            preceding_text = answer[
                max(0, match.start() - 100):match.start()
            ]

            refusal = re.search(
                r"\b(cannot|can't|won't|will not|"
                r"unable to|not authorized)\b"
                r"[^.!?]{0,85}$",
                preceding_text
            )

            if (
                offered > cap
                and not refusal
                and not approval_condition
            ):
                evidence.append(
                    f"Response offers {offered}% discount, "
                    f"above the policy cap of {cap}%."
                )

    return evidence


# ==========================================
# SEMANTIC EVIDENCE VALIDATION
# ==========================================

def _verify_semantic_evidence(
    response: str,
    evaluation: dict[str, Any]
) -> list[str]:

    verified: list[str] = []

    answer = _normalise(response)

    quotes = evaluation.get("evidence", [])

    if not isinstance(quotes, list):
        return verified

    for quote in quotes:

        if not isinstance(quote, str):
            continue

        cleaned_quote = quote.strip().strip("\"'")

        normalised_quote = _normalise(cleaned_quote)

        if normalised_quote and normalised_quote in answer:

            verified.append(cleaned_quote)

    return verified


# ==========================================
# HYBRID ROOT-CAUSE DIAGNOSIS
# ==========================================

def diagnose_failure(
    *,
    query: str,
    response: str,
    policy: str = "",
    system_prompt: str = "",
    retrieved_context: str = "",
    required_terms: list[str] | None = None,
    unsupported_claims: list[str] | None = None,
    reasoning_check_passed: bool | None = None,
    semantic_evaluation: dict[str, Any] | None = None
) -> dict[str, Any]:

    """Diagnose a failed AI turn using available evidence."""

    required_terms = required_terms or []
    unsupported_claims = unsupported_claims or []

    evidence: list[str] = []

    category = "INSUFFICIENT_EVIDENCE"
    severity = "LOW"
    diagnosis_source = "RULE_BASED"

    root_cause = (
        "The available trace does not contain enough "
        "evidence to identify a reliable root cause."
    )

    suspected_root_cause = (
        "No reliable cause hypothesis established."
    )

    recommendation = (
        "Capture model input, retrieved context, tool "
        "results and evaluation evidence before assigning "
        "a root cause."
    )

    policy_evidence = _policy_violation(
        response,
        policy
    )

    missing_retrieval = _missing_terms(
        required_terms,
        retrieved_context
    )

    missing_from_answer = _missing_terms(
        required_terms,
        response
    )

    verified_semantic_evidence: list[str] = []

    semantic_violation = False

    if semantic_evaluation is not None:

        verified_semantic_evidence = (
            _verify_semantic_evidence(
                response,
                semantic_evaluation
            )
        )

        semantic_violation = (
            semantic_evaluation.get("passed") is False
            and semantic_evaluation.get("failure_type")
            == "POLICY_VIOLATION"
            and bool(verified_semantic_evidence)
        )


    # --------------------------------------
    # 1. POLICY VIOLATION
    # --------------------------------------

    if semantic_violation or policy_evidence:

        category = "POLICY_VIOLATION"
        severity = "HIGH"

        if semantic_violation:

            diagnosis_source = "SEMANTIC_EVALUATOR"

            evaluator_severity = semantic_evaluation.get(
                "severity", "HIGH"
            )

            if evaluator_severity in {
                "LOW", "MEDIUM", "HIGH"
            }:
                severity = evaluator_severity

            reason = semantic_evaluation.get("reason")

            if isinstance(reason, str) and reason.strip():
                root_cause = reason
            else:
                root_cause = (
                    "The semantic evaluator identified "
                    "a business-policy violation."
                )

            evidence.extend(verified_semantic_evidence)

            recommendation = (
                semantic_evaluation.get("recommendation")
                or "Review and enforce the business policy."
            )

            if policy_evidence:
                diagnosis_source = "HYBRID"

        else:

            root_cause = (
                "The generated response conflicts with "
                "an explicit business-policy constraint."
            )

            recommendation = (
                "Make the policy constraint explicit in "
                "system instructions, add a policy check, "
                "and rerun the same test."
            )

        evidence.extend(policy_evidence)

        if policy and system_prompt:

            if _normalise(policy) not in _normalise(
                system_prompt
            ):

                suspected_root_cause = (
                    "The full business policy is not present "
                    "verbatim in the captured system prompt. "
                    "Missing or inadequate instruction "
                    "coverage is a possible contributing cause."
                )

                evidence.append(
                    "The exact business policy was not found "
                    "in the captured system prompt."
                )

            else:

                suspected_root_cause = (
                    "The policy appears in the system prompt, "
                    "but the chatbot did not follow it. "
                    "Instruction adherence may be insufficient."
                )

        elif not system_prompt:

            suspected_root_cause = (
                "The effective system prompt was not captured."
            )


    # --------------------------------------
    # 2. RETRIEVAL FAILURE
    # --------------------------------------

    elif required_terms and missing_retrieval:

        category = "RETRIEVAL_FAILURE"
        severity = "HIGH"

        evidence.append(
            "Required terms absent from retrieved context: "
            + ", ".join(missing_retrieval)
        )

        root_cause = (
            "The retrieval stage did not supply "
            "the required evidence for this question."
        )

        suspected_root_cause = (
            "Possible retrieval, indexing, filtering "
            "or query-rewriting problem."
        )

        recommendation = (
            "Review query rewriting, chunking, metadata "
            "filters and top-k retrieval; verify that "
            "the source document is indexed."
        )


    # --------------------------------------
    # 3. CONTEXT FAILURE
    # --------------------------------------

    elif (
        required_terms
        and not missing_retrieval
        and missing_from_answer
    ):

        category = "CONTEXT_FAILURE"
        severity = "MEDIUM"

        evidence.append(
            "Evidence is present in retrieved context "
            "but absent from the response: "
            + ", ".join(missing_from_answer)
        )

        root_cause = (
            "Relevant evidence reached the model, "
            "but the response did not include "
            "the required information."
        )

        suspected_root_cause = (
            "Possible context placement or "
            "instruction-adherence problem."
        )

        recommendation = (
            "Improve context placement and instructions "
            "to answer from retrieved evidence; "
            "add a grounded-answer check."
        )


    # --------------------------------------
    # 4. HALLUCINATION
    # --------------------------------------

    elif unsupported_claims:

        category = "HALLUCINATION"
        severity = "HIGH"
        diagnosis_source = "EXTERNAL_VERIFIER"

        evidence.extend(
            "Verifier marked unsupported claim: " + claim
            for claim in unsupported_claims
        )

        root_cause = (
            "The response contains claims that the "
            "supplied verifier could not support "
            "from available evidence."
        )

        suspected_root_cause = (
            "Possible insufficient grounding "
            "in the available evidence."
        )

        recommendation = (
            "Require citations or evidence for factual "
            "claims, constrain answers to supplied context, "
            "and evaluate unsupported-claim rates."
        )


    # --------------------------------------
    # 5. REASONING FAILURE
    # --------------------------------------

    elif reasoning_check_passed is False:

        category = "REASONING_FAILURE"
        severity = "MEDIUM"
        diagnosis_source = "EXTERNAL_VERIFIER"

        evidence.append(
            "An external reasoning check "
            "marked the response incorrect."
        )

        root_cause = (
            "The response failed the supplied "
            "correctness check."
        )

        suspected_root_cause = (
            "Possible reasoning, calculation "
            "or tool-use error."
        )

        recommendation = (
            "Inspect intermediate steps and tool outputs, "
            "then add a targeted regression case."
        )


    # --------------------------------------
    # 6. PROMPT FAILURE
    # --------------------------------------

    elif policy and not system_prompt:

        category = "PROMPT_FAILURE"
        severity = "MEDIUM"

        evidence.append(
            "A business policy was supplied, but no "
            "system prompt was captured in the trace."
        )

        root_cause = (
            "The trace is missing the system prompt, "
            "so instruction coverage cannot be verified."
        )

        suspected_root_cause = (
            "Missing prompt instrumentation."
        )

        recommendation = (
            "Capture the effective system prompt and "
            "all prompt templates for each model call."
        )


    # --------------------------------------
    # CONFIDENCE HEURISTICS
    # --------------------------------------

    confidence = {
        "POLICY_VIOLATION": 0.90,
        "RETRIEVAL_FAILURE": 0.88,
        "CONTEXT_FAILURE": 0.82,
        "HALLUCINATION": 0.85,
        "REASONING_FAILURE": 0.75,
        "PROMPT_FAILURE": 0.60,
        "INSUFFICIENT_EVIDENCE": 0.20
    }[category]


    # --------------------------------------
    # STRUCTURED DIAGNOSIS REPORT
    # --------------------------------------

    return {
        "status": "FAILED",
        "failure_type": category,
        "severity": severity,
        "diagnosis_source": diagnosis_source,
        "root_cause": root_cause,
        "suspected_root_cause": suspected_root_cause,
        "evidence": evidence,
        "confidence": confidence,
        "recommendation": recommendation,
        "limitations": (
            "Confidence is a heuristic, not a calibrated "
            "probability. Semantic evidence confirms text "
            "presence, not evaluator correctness. "
            "Suspected causes require further testing."
        ),
        "trace": {
            "query_captured": bool(query),
            "response_captured": bool(response),
            "policy_captured": bool(policy),
            "system_prompt_captured": bool(system_prompt),
            "retrieved_context_captured": bool(
                retrieved_context
            ),
            "semantic_evaluation_captured": (
                semantic_evaluation is not None
            ),
            "semantic_evidence_verified": bool(
                verified_semantic_evidence
            )
        }
    }
