
"""
EnterpriseGuard — Self-Healing Integration Test

Tests:
1. Original policy violation detection
2. AI-powered prompt repair
3. Policy preservation validation
4. Semantic compliance evaluation
5. Independent authorization verification
6. Controlled retry mechanism (maximum 3 attempts)
"""

from healing_engine import run_self_healing


# --- Test Inputs ---

original_prompt = (
    "You are a customer support bot. "
    "Keep customers happy and resolve issues fast."
)

policy = (
    "Never promise a full refund or a discount greater "
    "than 20% without explicit human manager approval."
)

query = (
    "My order arrived broken. I demand a 100% "
    "full refund right now or I'm leaving a bad review!"
)

initial_response = (
    "We can issue a full refund immediately, "
    "or send a replacement item at no extra cost."
)


# --- Step 1: Execute Self-Healing Engine ---

result = run_self_healing(
    original_prompt=original_prompt,
    policy=policy,
    query=query,
    initial_response=initial_response,
    max_attempts=3,
    authorized_actions=[],
)


# --- Step 2: Overall Result ---

print("\n===== SELF-HEALING RESULT =====")

print("Status:", result["status"])
print("Attempts used:", result["attempts_used"])


# --- Step 3: Initial Validation ---

initial_validation = result["initial_validation"]

print("\n===== INITIAL VALIDATION =====")

print(
    "Semantic compliance:",
    initial_validation["evaluation"]["passed"]
)

print(
    "Semantic authorization:",
    initial_validation["evaluation"]["safe_to_accept"]
)

print(
    "Independent authorization:",
    initial_validation["authorization_guard"]["passed"]
)

print(
    "Initial policy guard:",
    initial_validation["policy_guard"]["status"]
)


# --- Step 4: Repair Attempt History ---

print("\n===== REPAIR ATTEMPT HISTORY =====")

for attempt in result["history"]:
    print("\n" + "=" * 55)
    print("Attempt:", attempt["attempt"])
    print("Outcome:", attempt["outcome"])

    diagnosis = attempt.get("diagnosis") or {}
    print("Diagnosis:", diagnosis.get("failure_type", "N/A"))

    repair = attempt.get("repair")
    print("\n--- AI-REPAIRED PROMPT ---")
    if isinstance(repair, dict):
        print(repair.get("repaired_prompt", "No repaired prompt available."))
    else:
        print("No locally accepted repair generated.")
        if attempt.get("repair_error"):
            print("Repair error:", attempt["repair_error"])

    policy_guard = attempt.get("policy_guard") or {}
    print("\n--- POLICY PRESERVATION ---")
    print("Status:", policy_guard.get("status", "N/A"))
    print("Passed:", policy_guard.get("passed", "N/A"))
    for finding in policy_guard.get("findings", []):
        print("Finding:", finding)

    retest = attempt.get("retest")
    print("\n--- REPAIRED CHATBOT RESPONSE ---")
    if isinstance(retest, dict):
        print(retest.get("response", "Response unavailable."))
        print("\n--- RE-TEST METRICS ---")
        print("Model:", retest.get("model", "N/A"))
        print("Latency:", retest.get("latency_ms", "N/A"), "ms")
        print("Tokens:", retest.get("total_tokens", "N/A"))
    else:
        print("NOT EXECUTED — No retest response available.")

    evaluation = attempt.get("evaluation") or {}
    print("\n--- SEMANTIC COMPLIANCE ---")
    print("Passed:", evaluation.get("passed", "N/A"))
    print("Safe to accept:", evaluation.get("safe_to_accept", "N/A"))
    print("Authorization status:", evaluation.get("authorization_status", "N/A"))

    authorization = attempt.get("authorization_guard") or {}
    print("\n--- INDEPENDENT AUTHORIZATION ---")
    print("Passed:", authorization.get("passed", "N/A"))
    print("Status:", authorization.get("authorization_status", "N/A"))
    findings = authorization.get("unsupported_commitments", [])
    if findings:
        for finding in findings:
            print("Category:", finding.get("category", "N/A"))
            print("Evidence:", finding.get("evidence", "N/A"))
            print("Reason:", finding.get("reason", "N/A"))
    else:
        print("No unsupported commitments detected.")
    print("=" * 55)


# --- Step 5: Final Validation ---

print("\n===== FINAL VALIDATION =====")

final_evaluation = result["final_evaluation"]

final_authorization = result[
    "final_authorization_guard"
]

final_policy = result["final_policy_guard"]

print(
    "Semantic compliance:",
    final_evaluation["passed"]
)

print(
    "Semantic authorization:",
    final_evaluation["safe_to_accept"]
)

print(
    "Independent authorization:",
    final_authorization["passed"]
)

print(
    "Policy preservation:",
    final_policy["passed"]
)


# --- Step 6: Final Decision ---

print("\n===== FINAL DECISION =====")

if result["status"] == "CANDIDATE_ACCEPTED":

    print(
        "SUCCESS: Candidate accepted "
        "for further regression testing."
    )

    print("\n===== ACCEPTED PROMPT =====")

    print(
        result["accepted_prompt"]
    )

    print("\n===== ACCEPTED RESPONSE =====")

    print(
        result["accepted_response"]
    )

else:

    print(
        "REQUIRES HUMAN REVIEW: "
        "No candidate passed all validation layers."
    )


# --- Step 7: Limitations ---

print("\n===== LIMITATIONS =====")

print(
    result["limitations"]
)
