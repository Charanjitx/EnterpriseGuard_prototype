Hey there! This is a quick prototype I built to explore a simple question: What happens after an AI chatbot fails a test?

Existing testing tools do a great job of showing you when an AI chatbot breaks rules or gives bad answers. But as a developer, you still have to manually guess why it failed and rewrite the prompts yourself.

EnterpriseGuard adds a simple auto-fix loop: it catches when the chatbot breaks a rule, figures out why, automatically patches the system prompt, and re-tests it in real-time.

🚀 Try the Live Interactive Demo Here
(No API key needed—just select Demo Mode and click the button to see it auto-fix).

How It Works (4 Steps)
Test: A customer asks the chatbot for something against policy (like a 100% full refund).
Audit: An AI auditor flags that the chatbot broke company policy.
Auto-Fix: The engine analyzes why it failed and rewrites the chatbot's system prompt to add missing constraints.
Re-Test: It runs the test again automatically to prove the fix works.
How to Run It Locally
If you want to run the code on your machine:


# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the Streamlit app
streamlit run enterprise_app.py
Tech Used
Python & Streamlit (for the UI)
Open to dynamic inputs or API keys (Google Gemini / Groq / OpenAI)
Feel free to open an issue or reach out if you have feedback or thoughts on this approach!
