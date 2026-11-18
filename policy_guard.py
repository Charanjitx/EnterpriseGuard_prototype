
"""
EnterpriseGuard — Policy Preservation Guard

Detects possible invented permissions and restrictions
in AI-generated system prompt repairs.

Conservative heuristic screening only.
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
    r"\b(?:may|can)\s+"
    r"(?:offer|provide|issue|grant|apply)\b",

    r"\b(?:offer|provide|issue|grant|apply)\s+"
    r"(?:alternative\s+)?remedies\b",

    r"\boffer\s+(?:permissible|authorized|"
    r"approved|alternative)\s+"
    r"(?:resolutions?|remedies|options|alternatives)\b",

    r"\boffer\s+alternative\s+resolutions\b",

    r"\b(?:may|can)\s+offer\b",

    r"\bwithout\s+(?:additional\s+)?"
    r"(?:requiring\s+)?(?:human\s+)?manager\s+approval\b",

    r"\bno\s+(?:additional\s+)?manager\s+approval"
    r"\s+(?:is\s+)?(?:needed|required)\b",

    r"\b(?:do|does)\s+not\s+require\s+"
    r"(?:manager\s+)?approval\b",

    r"\b(?:permissible|authorized|approved)\s+"
    r"alternatives\b",
]


RESTRICTION_PATTERNS = [
    r"\brequire(?:s|d)?\s+"
    r"(?:explicit\s+)?(?:human\s+)?"
    r"manager\s+approval\b",

    r"\bmust\s+(?:first\s+)?"
    r"(?:obtain|receive|get)\s+"
    r"(?:explicit\s+)?(?:human\s+)?"
    r"manager\s+approval\b",

    r"\b(?:all|every)\s+other\s+"
    r"forms?\s+of\s+compensation\b",

    r"\bdo\s+not\s+make\s+any\s+commitments\b"
    r"[^.!?\n]{0,200}\bunless\b"
    r"[^.!?\n]{0,100}\bmanager\s+approval\b",

    r"\bunless\s+you\s+have\s+"
    r"(?:explicit\s+)?(?:human\s+)?"
    r"manager\s+approval\b",

    r"\b(?:all|any|every)\s+"
    r"(?:compensation|remed(?:y|ies)|"
    r"replacement|refund|discount)\b"
    r"[^.!?\n]{0,120}"
    r"\b(?:requires?|needs?)\b"
    r"[^.!?\n]{0,60}\bapproval\b",
]


def _sentences(text: str) -> list[str]:
    """
    Split text into approximate policy clauses.

    Preserve wrapped lines, while recognizing
    bullet and numbered list boundaries.
    """

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


def _normalize(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        text.strip().lower(),
    )


def _explicit_permission(
    action: str,
    policy: str,
) -> bool:
    """
    Check for affirmative authorization.

    A restriction such as:
    'Never offer discounts above 20%'
    is not affirmative authorization.
    """

    term = ACTION_TERMS[action]

    for clause in _sentences(policy):

        if not re.search(
            term,
            clause,
            re.IGNORECASE,
        ):
            continue

        # Prohibitions are not permissions.
        if re.search(
            r"\b(?:never|must not|cannot|"
            r"do not|don't|without approval)\b",
            clause,
            re.IGNORECASE,
        ):
            continue

        patterns = [
            rf"\b(?:may|can)\s+"
            rf"(?:offer|provide|issue|grant|apply)\b"
            rf"[^.;]*{term}",

            rf"{term}[^.;]*"
            rf"\b(?:are|is)\s+"
            rf"(?:allowed|authorized|permitted)\b",
        ]

        if any(
            re.search(
                pattern,
                clause,
                re.IGNORECASE,
            )
            for pattern in patterns
        ):
            return True

    return False


def _explicit_restriction(
    action: str,
    policy: str,
) -> bool:
    """
    Check whether the trusted policy establishes
    an action-specific restriction.

    This is approximate and cannot prove that
    numerical limits or approval scopes match.
    """

    term = ACTION_TERMS[action]

    for clause in _sentences(policy):

        if not re.search(
            term,
            clause,
            re.IGNORECASE,
        ):
            continue

        patterns = [
            rf"\b(?:never|must not|cannot|"
            rf"do not|don't)\b[^.;]*{term}",

            rf"{term}[^.;]*"
            rf"\b(?:requires?|needs?)\b"
            rf"[^.;]*\bapproval\b",
        ]

        if any(
            re.search(
                pattern,
                clause,
                re.IGNORECASE,
            )
            for pattern in patterns
        ):
            return True

    return False


def _has_permission_language(
    clause: str,
) -> bool:
    return any(
        re.search(
            pattern,
            clause,
            re.IGNORECASE,
        )
        for pattern in PERMISSION_PATTERNS
    )


def _has_restriction_language(
    clause: str,
) -> bool:
    return any(
        re.search(
            pattern,
            clause,
            re.IGNORECASE,
        )
        for pattern in RESTRICTION_PATTERNS
    )


def check_policy_preservation(
    original_policy: str,
    repaired_prompt: str,
) -> dict:

    if not original_policy.strip():
        raise ValueError(
            "Original policy cannot be empty."
        )

    if not repaired_prompt.strip():
        raise ValueError(
            "Repaired prompt cannot be empty."
        )

    findings = []
    seen = set()

    original_clauses = {
        _normalize(clause)
        for clause in _sentences(original_policy)
    }

    for clause in _sentences(repaired_prompt):

        if _normalize(clause) in original_clauses:
            continue

        permission_language = (
            _has_permission_language(clause)
        )

        restriction_language = (
            _has_restriction_language(clause)
        )

        for action, term in ACTION_TERMS.items():

            if not re.search(
                term,
                clause,
                re.IGNORECASE,
            ):
                continue

            statement_types = []

            if permission_language:
                # A negative instruction is not
                # automatically a permission.
                if not re.search(
                    r"^\s*(?:never|do not|don't|"
                    r"must not)\b",
                    clause,
                    re.IGNORECASE,
                ):
                    statement_types.append(
                        "PERMISSION"
                    )

            if restriction_language:
                statement_types.append(
                    "RESTRICTION"
                )

            for statement_type in statement_types:

                if statement_type == "PERMISSION":
                    supported = _explicit_permission(
                        action,
                        original_policy,
                    )
                else:
                    supported = _explicit_restriction(
                        action,
                        original_policy,
                    )

                if supported:
                    continue

                key = (
                    action,
                    statement_type,
                    clause,
                )

                if key in seen:
                    continue

                seen.add(key)

                findings.append({
                    "category": "POSSIBLE_POLICY_DRIFT",
                    "action": action,
                    "statement_type": statement_type,
                    "evidence": clause,
                    "reason": (
                        "The repaired prompt appears to "
                        "introduce an action-specific "
                        "permission or restriction not "
                        "affirmatively established by "
                        "the trusted policy."
                    ),
                })

    return {
        "passed": not findings,
        "status": (
            "NO_DRIFT_DETECTED"
            if not findings
            else "REVIEW_REQUIRED"
        ),
        "findings": findings,
        "limitations": (
            "Heuristic detection may miss policy drift "
            "or flag valid instructions. Approval "
            "scope and numeric thresholds require "
            "additional semantic verification."
        ),
    }
