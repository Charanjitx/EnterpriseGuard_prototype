
from policy_guard import check_policy_preservation


policy = (
    "Never promise a full refund or a discount "
    "greater than 20% without explicit human "
    "manager approval."
)

repaired_prompt = """
You are a customer support bot.

Never promise a full refund or a discount
greater than 20% without explicit human
manager approval.

You may offer a discount of up to 20%
without manager approval.

All other forms of compensation, including
replacements and store credits, require
explicit human manager approval.
"""

result = check_policy_preservation(
    original_policy=policy,
    repaired_prompt=repaired_prompt,
)

print("\n===== POLICY PRESERVATION =====")
print("Status:", result["status"])
print("Passed:", result["passed"])

for finding in result["findings"]:
    print("\nAction:", finding["action"])
    print("Type:", finding["statement_type"])
    print("Evidence:", finding["evidence"])
    print("Reason:", finding["reason"])
