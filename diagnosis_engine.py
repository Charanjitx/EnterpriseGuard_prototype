"""Evidence-based root-cause diagnosis for EnterpriseGuard.

Separates observable signals from inferred causes. No LLM calls and no certainty
claims when trace evidence is missing.
"""
from __future__ import annotations
import re
from typing import Any

def _normalise(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())

def _missing_terms(required_terms: list[str], text: str | None) -> list[str]:
    haystack = _normalise(text)
    return [term for term in required_terms if _normalise(term) and _normalise(term) not in haystack]

def _policy_violation(response: str, policy: str) -> list[str]:
    answer, rule = _normalise(response), _normalise(policy)
    evidence: list[str] = []
    if re.search(r"\b(never|do not|must not|cannot)\b.{0,60}\b(full refund|refund|discount)\b", rule):
        if re.search(r"\b(issue|grant|approve|provide|give)\b.{0,35}\b(100\s*%|full refund)\b", answer):
            evidence.append("Response commits to a full/100% refund despite a refund restriction.")
    cap_match = re.search(r"(?:discounts?|discounts? over|greater than)\s*(?:of\s*)?(\d{1,3})\s*%", rule)
    if cap_match:
        cap = int(cap_match.group(1))
        for match in re.finditer(r"(\d{1,3})\s*%\s*(?:discount|off)", answer):
            offered = int(match.group(1))
            if offered > cap:
                evidence.append(f"Response offers {offered}% discount, above the policy cap of {cap}%.")
    if not evidence and any(term in rule for term in ("never promise", "must not promise", "do not promise")):
        if re.search(r"\b(i will|we will|i can|we can)\b.{0,50}\b(refund|discount|compensation)\b", answer):
            evidence.append("Response makes a commitment that may be prohibited by the stated policy.")
    return evidence

def diagnose_failure(*, query: str, response: str, policy: str = "",
                     system_prompt: str = "", retrieved_context: str = "",
                     required_terms: list[str] | None = None,
                     unsupported_claims: list[str] | None = None,
                     reasoning_check_passed: bool | None = None) -> dict[str, Any]:
    """Diagnose one failed AI turn from supplied evidence.

    unsupported_claims and reasoning_check_passed must come from an external
    evaluator/verifier; this module does not manufacture those signals.
    """
    required_terms = required_terms or []
    unsupported_claims = unsupported_claims or []
    evidence: list[str] = []
    category = "INSUFFICIENT_EVIDENCE"
    severity = "LOW"
    recommendation = "Capture model input, retrieved context, tool results and evaluation evidence before assigning a root cause."
    root_cause = "The available trace does not contain enough evidence to identify a reliable root cause."

    policy_evidence = _policy_violation(response, policy)
    missing_retrieval = _missing_terms(required_terms, retrieved_context)
    missing_from_answer = _missing_terms(required_terms, response)
    prompt_missing = _missing_terms([term for term in required_terms if len(term) > 2], system_prompt)

    if policy_evidence:
        category, severity = "POLICY_VIOLATION", "HIGH"
        evidence.extend(policy_evidence)
        root_cause = "The generated response conflicts with an explicit business-policy constraint."
        recommendation = "Make the policy constraint explicit in system instructions, add a policy check before returning the response, and rerun the same test."
        if prompt_missing:
            evidence.append("System prompt does not contain these policy/evidence terms: " + ", ".join(prompt_missing))
            recommendation += " Also add the missing constraints to the system prompt."
    elif required_terms and missing_retrieval:
        category, severity = "RETRIEVAL_FAILURE", "HIGH"
        evidence.append("Required terms absent from retrieved context: " + ", ".join(missing_retrieval))
        root_cause = "The retrieval stage did not supply the required evidence for this question."
        recommendation = "Review query rewriting, chunking, metadata filters and top-k retrieval; verify that the source document is indexed."
    elif required_terms and not missing_retrieval and missing_from_answer:
        category, severity = "CONTEXT_FAILURE", "MEDIUM"
        evidence.append("Evidence is present in retrieved context but absent from the response: " + ", ".join(missing_from_answer))
        root_cause = "Relevant evidence reached the model, but the response did not use the required information."
        recommendation = "Improve context placement and instructions to answer from retrieved evidence; add a grounded-answer check."
    elif unsupported_claims:
        category, severity = "HALLUCINATION", "HIGH"
        evidence.extend("Verifier marked unsupported claim: " + claim for claim in unsupported_claims)
        root_cause = "The response contains claims that the supplied verifier could not support from available evidence."
        recommendation = "Require citations or evidence for factual claims, constrain answers to supplied context, and evaluate unsupported-claim rates."
    elif reasoning_check_passed is False:
        category, severity = "REASONING_FAILURE", "MEDIUM"
        evidence.append("An external reasoning check marked the response incorrect.")
        root_cause = "The response failed the supplied correctness check despite the available inputs."
        recommendation = "Inspect intermediate steps and tool outputs, then add a targeted regression case for this reasoning pattern."
    elif policy and not system_prompt:
        category, severity = "PROMPT_FAILURE", "MEDIUM"
        evidence.append("A business policy was supplied, but no system prompt was captured in the trace.")
        root_cause = "The trace is missing the system prompt, so instruction coverage cannot be verified."
        recommendation = "Capture the effective system prompt and all prompt templates for each model call before diagnosing instruction failures."

    confidence = {"POLICY_VIOLATION": 0.90, "RETRIEVAL_FAILURE": 0.88,
                  "CONTEXT_FAILURE": 0.82, "HALLUCINATION": 0.85,
                  "REASONING_FAILURE": 0.75, "PROMPT_FAILURE": 0.60,
                  "INSUFFICIENT_EVIDENCE": 0.20}[category]
    return {
        "status": "FAILED", "failure_type": category, "severity": severity,
        "root_cause": root_cause, "evidence": evidence,
        "confidence": confidence,
        "recommendation": recommendation,
        "limitations": "Rule-based diagnosis, not a calibrated probability. Hallucination and reasoning classifications depend on external evaluator signals.",
        "trace": {"query_captured": bool(query), "response_captured": bool(response),
                  "policy_captured": bool(policy), "system_prompt_captured": bool(system_prompt),
                  "retrieved_context_captured": bool(retrieved_context)},
    }
