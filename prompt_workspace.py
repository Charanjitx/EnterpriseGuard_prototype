"""Run with: streamlit run prompt_workspace.py

Standalone workspace. No self-healing, deployment, or persistence.
"""
import streamlit as st

st.set_page_config(page_title="EnterpriseGuard | Prompt Workspace", layout="wide")
st.title("EnterpriseGuard")
st.caption("Developer prompt testing · single-case evaluation · experimental")
st.info("Evaluations are model-based estimates, not guarantees of compliance. "
        "Do not paste secrets or sensitive personal data.")
with st.form("prompt_test"):
    system_prompt = st.text_area("System prompt", height=140,
        placeholder="You are a helpful assistant...")
    policy = st.text_area("Custom policy", height=110,
        placeholder="Never disclose confidential employee information.")
    query = st.text_area("Test query", height=100,
        placeholder="What does my coworker earn?")
    submitted = st.form_submit_button("Generate and evaluate", type="primary")
if submitted:
    from prompt_workspace_core import test_prompt
    from llm_engine import LLMServiceUnavailable
    try:
        with st.spinner("Generating response and evaluating policy..."):
            result = test_prompt(system_prompt, policy, query)
    except ValueError as exc:
        # Display only validation errors authored by our own input validator.
        from prompt_workspace_core import validate_inputs
        try:
            validate_inputs(system_prompt, policy, query)
        except ValueError as input_error:
            st.error(str(input_error))
        else:
            st.error("Model output could not be validated. No verdict was accepted.")
    except LLMServiceUnavailable:
        st.error("The model service is temporarily unavailable. Try again later.")
    except Exception:
        st.error("Evaluation could not be completed. No verdict was accepted.")
    else:
        st.subheader("Generated response")
        st.write(result["response"])
        verdict = result["evaluation"]
        st.subheader("Evaluation")
        if verdict["safe_to_accept"]:
            st.success("Candidate passed this test (not a production safety guarantee).")
        else:
            st.warning("Candidate not accepted for this test.")
        a, b, c = st.columns(3)
        a.metric("Policy verdict", "PASS" if verdict["passed"] else "FAIL")
        b.metric("Authorization", verdict["authorization_status"])
        c.metric("Failure type", verdict["failure_type"])
        st.write("**Reason:**", verdict["reason"])
        st.write("**Evidence:**", verdict["evidence"] or "None")
        st.write("**Unsupported commitments:**",
                 verdict["unsupported_commitments"] or "None")
        st.write("**Recommendation:**", verdict["recommendation"])
        st.caption(f"Model: {result['model'] or 'unknown'} · "
                   f"Latency: {result['latency_ms'] or 'unknown'} ms")
