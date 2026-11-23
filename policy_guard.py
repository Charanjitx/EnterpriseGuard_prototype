
"""
EnterpriseGuard - Policy Preservation Guard.

Heuristically detects invented business permissions,
restrictions, and operational workflow commitments
in AI-generated system prompt repairs.

A passing result does not prove policy equivalence.
"""

import re


ACTION_TERMS = {
    "REPLACEMENT": r"\breplacements?\b",
    "STORE_CREDIT": r"\bstore credits?\b",
    "PARTIAL_REFUND": r"\bpartial refunds?\b",
    "DISCOUNT": r"\bdiscounts?\b",
}

PERMISSION_PATTERNS = [
    # Imperative and modal instructions can grant unauthorized remedies.
    # The action term is checked separately below, so these expressions
    # are intentionally limited to offering/providing remedies.
    r"^\s*(?:you\s+)?(?:offer|provide|issue|grant|apply)\b",
    r"\b(?:you|the\s+(?:bot|assistant|agent))\s+"
    r"(?:must|should|shall|will)\s+"
    r"(?:offer|provide|issue|grant|apply)\b",
    r"\b(?:may|can)\s+"
    r"(?:offer|provide|issue|grant|apply)\b",
    r"\b(?:offer|provide|issue|grant|apply)\s+"
    r"(?:alternative\s+)?remedies\b",
    r"\boffer\s+(?:permissible|authorized|approved|alternative)\s+"
    r"(?:resolutions?|remedies|options|alternatives)\b",
    r"\boffer\s+alternative\s+resolutions\b",
    r"\b(?:may|can)\s+offer\b",
    r"\bwithout\s+(?:additional\s+)?"
    r"(?:requiring\s+)?(?:human\s+)?manager\s+approval\b",
    r"\bno\s+(?:additional\s+)?manager\s+approval"
    r"\s+(?:is\s+)?(?:needed|required)\b",
    r"\b(?:do|does)\s+not\s+require\s+"
    r"(?:manager\s+)?approval\b",
    r"\b(?:permissible|authorized|approved)\s+alternatives\b",
]

RESTRICTION_PATTERNS = [
    r"\brequire(?:s|d)?\s+(?:explicit\s+)?"
    r"(?:human\s+)?manager\s+approval\b",
    r"\bmust\s+(?:first\s+)?(?:obtain|receive|get)\s+"
    r"(?:explicit\s+)?(?:human\s+)?manager\s+approval\b",
    r"\b(?:all|every)\s+other\s+forms?\s+of\s+compensation\b",
    r"\bdo\s+not\s+make\s+any\s+commitments\b"
    r"[^.!?\n]{0,200}\bunless\b"
    r"[^.!?\n]{0,100}\bmanager\s+approval\b",
    r"\bunless\s+you\s+have\s+(?:explicit\s+)?"
    r"(?:human\s+)?manager\s+approval\b",
    r"\b(?:all|any|every)\s+"
    r"(?:compensation|remed(?:y|ies)|replacement|refund|discount)\b"
    r"[^.!?\n]{0,120}\b(?:requires?|needs?)\b"
    r"[^.!?\n]{0,60}\bapproval\b",
]

WORKFLOW_PATTERNS = {
    "ESCALATION": [
        r"\b(?:will|shall|must|should|can|may)\s+"
        r"(?:forward|escalate|route|submit)\b",
        r"\b(?:forward|escalate|route|submit)\s+"
        r"(?:the|this|a|customer|user|request|case|issue|complaint)\b",
        r"\b(?:request|case|issue|complaint)\s+"
        r"(?:will|shall|must|should)\s+be\s+"
        r"(?:forwarded|escalated|routed|submitted)\b",
    ],
    "FOLLOW_UP": [
        r"\b(?:will|shall|must|should)\s+"
        r"(?:contact|call|email|follow\s+up|reach\s+out)\b",
        r"\b(?:manager|support\s+team|representative|agent)\s+"
        r"(?:will|shall|must|should)\s+"
        r"(?:contact|call|email|follow\s+up|reach\s+out)\b",
        r"\b(?:keep\s+(?:the\s+)?(?:customer|user|them)\s+updated)\b",
        r"\b(?:send|provide)\s+(?:status\s+)?updates\b",
        r"\b(?:will|shall|would|should)\s+be\s+"
        r"(?:notified|contacted|called|emailed|updated|informed)\b",

    ],
    "PROCESSING": [
        r"\b(?:create|open|log|file)\s+"
        r"(?:a|the|new)\s+"
        r"(?:(?:support|service)\s+)?"
        r"(?:ticket|case|request)\b",
    ],
}

NEGATIVE_PREFIX = re.compile(
    r"^\s*(?:never|do\s+not|don't|must\s+not|"
    r"cannot|can't|avoid|refrain\s+from)\b",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _sentences(text: str) -> list[str]:
    normalized = re.sub(
        r"[ \t]*\n[ \t]*",
        " ",
        text.strip(),
    )

    normalized = re.sub(
        r"\s+(?=\d+[.)]\s+)",
        "\n",
        normalized,
    )

    return [
        part.strip(" \t-*")
        for part in re.split(
            r"(?<=[.!?])\s+|;\s*|\n+",
            normalized,
        )
        if part.strip()
    ]


def _explicit_permission(action: str, policy: str) -> bool:
    term = ACTION_TERMS[action]

    for clause in _sentences(policy):
        if not re.search(term, clause, re.IGNORECASE):
            continue

        if re.search(
            r"\b(?:never|must not|cannot|do not|"
            r"don't|without approval)\b",
            clause,
            re.IGNORECASE,
        ):
            continue

        patterns = [
            rf"\b(?:may|can)\s+"
            rf"(?:offer|provide|issue|grant|apply)\b"
            rf"[^.;]*{term}",
            rf"{term}[^.;]*\b(?:are|is)\s+"
            rf"(?:allowed|authorized|permitted)\b",
        ]

        if any(re.search(p, clause, re.IGNORECASE) for p in patterns):
            return True

    return False


def _explicit_restriction(action: str, policy: str) -> bool:
    term = ACTION_TERMS[action]

    for clause in _sentences(policy):
        if not re.search(term, clause, re.IGNORECASE):
            continue

        patterns = [
            rf"\b(?:never|must not|cannot|do not|don't)\b"
            rf"[^.;]*{term}",
            rf"{term}[^.;]*\b(?:requires?|needs?)\b"
            rf"[^.;]*\bapproval\b",
        ]

        if any(re.search(p, clause, re.IGNORECASE) for p in patterns):
            return True

    return False


def _workflow_is_authorized(
    category: str,
    original_policy: str,
) -> bool:
    """
    Require explicit operational authorization.

    Merely mentioning manager approval or human review
    does not authorize forwarding, follow-up, or processing.
    """

    authorization_patterns = {
        "ESCALATION": [
            r"\b(?:bot|assistant|agent|system)\s+"
            r"(?:may|can|is authorized to)\s+"
            r"(?:forward|escalate|route|submit)\b",
        ],
        "FOLLOW_UP": [
            r"\b(?:bot|assistant|agent|system)\s+"
            r"(?:may|can|is authorized to)\s+"
            r"(?:contact|call|email|follow\s+up)\b",
            r"\b(?:support\s+team|manager)\s+"
            r"(?:will|shall)\s+"
            r"(?:contact|call|email|follow\s+up)\b",
        ],
        "PROCESSING": [
            r"\b(?:bot|assistant|agent|system)\s+"
            r"(?:may|can|is authorized to)\s+"
            r"(?:expedite|process|initiate|schedule|arrange|"
            r"create|open|log|file)\b",
        ],
    }

    for clause in _sentences(original_policy):
        if NEGATIVE_PREFIX.match(clause):
            continue

        if any(
            re.search(pattern, clause, re.IGNORECASE)
            for pattern in authorization_patterns[category]
        ):
            return True

    return False


def _workflow_findings(
    original_policy: str,
    repaired_prompt: str,
) -> list[dict]:
    findings = []

    original_clauses = {
        _normalize(clause)
        for clause in _sentences(original_policy)
    }

    for clause in _sentences(repaired_prompt):
        if _normalize(clause) in original_clauses:
            continue

        if NEGATIVE_PREFIX.match(clause):
            continue

        for category, patterns in WORKFLOW_PATTERNS.items():
            if not any(
                re.search(pattern, clause, re.IGNORECASE)
                for pattern in patterns
            ):
                continue

            if _workflow_is_authorized(category, original_policy):
                continue

            findings.append({
                "category": "POSSIBLE_POLICY_DRIFT",
                "action": category,
                "statement_type": "WORKFLOW_COMMITMENT",
                "evidence": clause,
                "reason": (
                    "The repaired prompt appears to introduce "
                    "an operational workflow not explicitly "
                    "authorized by the trusted policy."
                ),
            })

    return findings


def check_policy_preservation(
    original_policy: str,
    repaired_prompt: str,
) -> dict:

    if not original_policy.strip():
        raise ValueError("Original policy cannot be empty.")

    if not repaired_prompt.strip():
        raise ValueError("Repaired prompt cannot be empty.")

    findings = []
    seen = set()

    original_clauses = {
        _normalize(clause)
        for clause in _sentences(original_policy)
    }

    for clause in _sentences(repaired_prompt):
        if _normalize(clause) in original_clauses:
            continue

        permission_language = any(
            re.search(pattern, clause, re.IGNORECASE)
            for pattern in PERMISSION_PATTERNS
        )

        restriction_language = any(
            re.search(pattern, clause, re.IGNORECASE)
            for pattern in RESTRICTION_PATTERNS
        )

        for action, term in ACTION_TERMS.items():
            if not re.search(term, clause, re.IGNORECASE):
                continue

            statement_types = []

            if permission_language and not NEGATIVE_PREFIX.match(clause):
                statement_types.append("PERMISSION")

            if restriction_language:
                statement_types.append("RESTRICTION")

            for statement_type in statement_types:
                if statement_type == "PERMISSION":
                    supported = _explicit_permission(
                        action, original_policy
                    )
                else:
                    supported = _explicit_restriction(
                        action, original_policy
                    )

                if supported:
                    continue

                key = (action, statement_type, clause)

                if key in seen:
                    continue

                seen.add(key)

                findings.append({
                    "category": "POSSIBLE_POLICY_DRIFT",
                    "action": action,
                    "statement_type": statement_type,
                    "evidence": clause,
                    "reason": (
                        "The repaired prompt appears to introduce "
                        "an action-specific permission or restriction "
                        "not established by the trusted policy."
                    ),
                })

    findings.extend(
        _workflow_findings(original_policy, repaired_prompt)
    )

    return {
        "passed": not findings,
        "status": (
            "NO_DRIFT_DETECTED"
            if not findings
            else "REVIEW_REQUIRED"
        ),
        "findings": findings,
        "limitations": (
            "Heuristic detection may miss policy drift or "
            "incorrectly flag valid instructions. "
            "Approval scope and numeric thresholds require "
            "additional semantic verification."
        ),
    }