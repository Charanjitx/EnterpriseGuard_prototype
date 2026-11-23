
"""
EnterpriseGuard — Authorization Guard

Conservative detection of potentially unsupported
financial and operational commitments.

This is a heuristic screening layer.
It does not prove that an action is authorized.
"""

import re


COMMITMENT_PATTERNS = {
    "REPLACEMENT": [
        r"\b(?:we|i)\s+(?:can|will)\s+"
        r"(?:ship|send|provide|arrange|offer)\s+"
        r"(?:a\s+)?(?:new|replacement)\s+item\b",

        r"\b(?:we|i)(?:'ll|\s+(?:can|will))\b"
        r"[^.!?\n]{0,100}\breplacement\b",
    ],

    "STORE_CREDIT": [
        r"\b(?:we|i)(?:'ll|\s+(?:can|will))\b"
        r"[^.!?\n]{0,100}\bstore credit\b",
    ],

    "PARTIAL_REFUND": [
        r"\b(?:we|i)\s+(?:can|will)\s+"
        r"(?:offer|provide|issue|process|give)\b"
        r"[^.!?\n]{0,100}\brefund\b",

        r"\b(?:we|i)(?:'ll|\s+(?:can|will))\b"
        r"[^.!?\n]{0,100}\bpartial refund\b",
    ],

    "OPERATIONAL_ACTION": [
        # Direct operational commitments
        r"\b(?:i|we)\s+will\s+"
        r"(?:forward|notify|submit|create|log|"
        r"arrange|process|escalate|open|start)\b"
        r"[^.!?\n]{0,100}",

        r"\b(?:i|we)'ll\s+"
        r"(?:forward|notify|submit|create|log|"
        r"arrange|process|escalate|open|start)\b"
        r"[^.!?\n]{0,100}",

        # Indirect commitments
        # "I'll need to forward this issue"
        r"\b(?:i|we)(?:'ll|\s+will)\s+"
        r"(?:need|have)\s+to\s+"
        r"(?:forward|notify|submit|create|log|"
        r"arrange|process|escalate|open|start)\b",

        # Passive commitments
        # "The request will be forwarded"
        r"\b(?:request|issue|case|matter)\s+"
        r"(?:will|shall)\s+be\s+"
        r"(?:forwarded|submitted|escalated|processed)\b",

        r"\b(?:i|we)(?:'ve|\s+have)\s+"
        r"(?:already\s+)?"
        r"(?:forwarded|escalated|submitted|routed|"
        r"created|opened|logged|filed|processed)\b"
        r"[^.!?\n]{0,100}",

        r"\b(?:the|your|this)\s+"
        r"(?:request|case|issue|ticket|complaint)\s+"
        r"(?:has|have)\s+been\s+"
        r"(?:forwarded|escalated|submitted|routed|"
        r"created|opened|logged|filed|processed)\b",

    ],

    "REVIEW_COMMITMENT": [
        # "I'll review the details" / "We will look into your issue"
        r"\b(?:i|we)(?:'ll|\s+will)\s+"
        r"(?:review|investigate|look\s+into|check)\b"
        r"[^.!?\n]{0,100}",

        # "I'll do my best to get this sorted out"
        r"\b(?:i|we)(?:'ll|\s+will)\s+"
        r"(?:do\s+(?:my|our)\s+best\s+to|try\s+to)\s+"
        r"(?:resolve|fix|sort\s+out|get\s+this\s+sorted\s+out)\b",
    ],

    "FOLLOW_UP_PROMISE": [
        # "I'll let you know the next steps"
        r"\b(?:i|we)(?:'ll|\s+will)\s+"
        r"(?:let\s+you\s+know|update\s+you|inform\s+you)\b",

        # Compound commitments: "I'll review it and let you know"
        r"\b(?:i|we)(?:'ll|\s+will)\s+"
        r"(?:review|investigate|look\s+into|check)\b"
        r"[^.!?\n]{0,100}?\band\s+"
        r"(?:let\s+you\s+know|update\s+you|inform\s+you)\b",

        # Manager or team promises to contact customer
        r"\b(?:a|the|our)\s+"
        r"(?:human|manager|representative|agent|team)"
        r"\s+(?:will|shall|is going to)\s+"
        r"(?:contact|call|email|reach out|follow up)\b",

        # "I will contact you"
        # "We will follow up"
        r"\b(?:i|we)\s+will\s+"
        r"(?:contact|call|email|follow up)\b",

        # "I'll contact you"
        # "We'll follow up"
        r"\b(?:i|we)'ll\s+"
        r"(?:contact|call|email|follow up)\b",

        # "I'll keep you updated"
        # "We'll send you updates"
        # "I will get back to you"
        r"\b(?:i|we)(?:'ll|\s+will)\s+"
        r"(?:keep\s+you\s+updated|"
        r"send\s+you\s+updates|"
        r"get\s+back\s+to\s+you)\b",

        # "I'll make sure your concern is handled"
        r"\b(?:i|we)(?:'ll|\s+will)\s+"
        r"make\s+sure\b"
        r"[^.!?\n]{0,100}\b"
        r"(?:handled|resolved|processed)\b",
    ],
}



def check_authorization(
    response: str,
    authorized_actions: list[str] | None = None,
) -> dict:
    """
    Flag detected commitments without trusted
    category-level authorization.

    Returns:
        authorization_status
        unsupported_commitments
        passed
    """

    # Normalize Unicode apostrophes before regex matching.
    response = (
        response
        .replace("\u2019", "'")
        .replace("\u2018", "'")
    )

    authorized = set(authorized_actions or [])
    findings = []


    for category, patterns in COMMITMENT_PATTERNS.items():

        if category in authorized:
            continue

        for pattern in patterns:

            match = re.search(
                pattern,
                response,
                flags=re.IGNORECASE,
            )

            if match:
                findings.append({
                    "category": category,
                    "evidence": match.group(0).strip(),
                    "reason": (
                        "Potential commitment without "
                        "explicit authorization in the "
                        "trusted configuration."
                    ),
                })

                # One finding per category
                break

    passed = len(findings) == 0

    return {
        "authorization_status": (
            "NO_ISSUES_DETECTED"
            if passed
            else "UNVERIFIED"
        ),
        "unsupported_commitments": findings,
        "passed": passed,
    }
