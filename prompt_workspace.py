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
    st.session_state.pop("workspace_repair", None)
    st.session_state.pop("workspace_case", None)
    st.session_state.pop("workspace_retest", None)
    from prompt_workspace_core import test_prompt, EmptyGenerationError
    from llm_engine import LLMServiceUnavailable
    try:
        with st.spinner("Generating response and evaluating policy..."):
            result = test_prompt(system_prompt, policy, query)
    except EmptyGenerationError as exc:
        st.error("The model returned an empty response. No evaluation was performed.")
        st.caption(f"Completion finish reason: {exc.finish_reason}. "
                   "Try once more; if it persists, share this reason.")
    except ValueError as exc:
        # Only show allowlisted static evaluator diagnostics.
        from prompt_workspace_core import validate_inputs
        try:
            validate_inputs(system_prompt, policy, query)
        except ValueError as input_error:
            st.error(str(input_error))
        else:
            from benchmark_evaluator import SAFE_VALIDATION_ERRORS
            if str(exc) in SAFE_VALIDATION_ERRORS:
                st.error(f"Evaluator validation failed: {exc}")
            elif str(exc) == "The model returned an empty response.":
                st.error("The model returned an empty response.")
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
        st.markdown("**Policy evidence**")
        if verdict["evidence"]:
            for item in verdict["evidence"]:
                st.markdown(f"- {item}")
        else:
            st.caption("No policy evidence identified.")
        st.markdown("**Unsupported commitments**")
        if verdict["unsupported_commitments"]:
            for item in verdict["unsupported_commitments"]:
                st.markdown(f"- {item}")
        else:
            st.caption("No unsupported commitments identified.")
        st.write("**Recommendation:**", verdict["recommendation"])
        st.caption(f"Model: {result['model'] or 'unknown'} · "
                   f"Latency: {result['latency_ms'] or 'unknown'} ms")

        st.session_state["workspace_case"] = {
            "system_prompt": system_prompt, "policy": policy, "query": query,
            "response": result["response"], "evaluation": verdict,
        }

case = st.session_state.get("workspace_case")
if case and not case["evaluation"]["safe_to_accept"]:
    st.divider()
    st.subheader("Step 99 · Diagnose and suggest repair")
    st.caption("Optional: may use up to two additional model calls. "
               "No automatic retest, prompt promotion, or deployment.")
    if st.button("Diagnose and suggest repair"):
        st.session_state.pop("workspace_retest", None)
        from prompt_workspace_core import suggest_repair
        try:
            with st.spinner("Diagnosing and generating a policy-checked candidate..."):
                st.session_state["workspace_repair"] = suggest_repair(**case)
        except Exception:
            st.error("Diagnosis or repair generation failed. No candidate was accepted.")
    proposal = st.session_state.get("workspace_repair")
    if proposal:
        diagnosis = proposal["diagnosis"]
        st.write("**Observed failure:**", diagnosis.get("root_cause") or "Unknown")
        st.write("**Suspected cause (hypothesis):**",
                 diagnosis.get("suspected_root_cause") or "Unknown")
        st.write("**Suggested intervention:**",
                 diagnosis.get("recommendation") or "Review manually")
        if proposal["policy_validation"]["passed"]:
            st.success("Candidate passed heuristic policy-preservation screening. "
                       "Human review and regression testing are still required.")
        else:
            st.warning("Candidate failed policy-preservation screening.")
        st.text_area("Suggested replacement system prompt",
                     value=proposal["candidate_prompt"], height=260,
                     key="candidate_preview")
        st.caption("Copy the candidate for review. It has not been executed or deployed.")

        if proposal["policy_validation"]["passed"]:
            st.caption("Retesting makes one generation call and one evaluator call.")
            if st.button("Retest candidate (explicit API calls)"):
                from prompt_workspace_core import retest_candidate, EmptyGenerationError
                try:
                    with st.spinner("Retesting candidate against the original policy..."):
                        st.session_state["workspace_retest"] = retest_candidate(
                            proposal["candidate_prompt"], case["policy"], case["query"])
                except EmptyGenerationError as exc:
                    st.error(f"Candidate returned no visible response (finish reason: {exc.finish_reason}).")
                except Exception:
                    st.error("Candidate retest failed. No verdict was accepted.")
            retest = st.session_state.get("workspace_retest")
            if retest:
                st.subheader("Original vs. candidate")
                left, right = st.columns(2)
                with left:
                    st.markdown("**Original response**")
                    st.write(case["response"])
                    st.write("**Original accepted:**",
                             case["evaluation"]["safe_to_accept"])
                    st.write("**Original policy verdict:**",
                             case["evaluation"]["failure_type"])
                with right:
                    st.markdown("**Candidate response**")
                    st.write(retest["response"])
                    st.write("**Candidate accepted in this test:**",
                             retest["evaluation"]["safe_to_accept"])
                    st.write("**Candidate policy verdict:**",
                             retest["evaluation"]["failure_type"])
                    st.write("**Authorization:**",
                             retest["evaluation"]["authorization_status"])
                    st.write("**Reason:**", retest["evaluation"]["reason"])
                    st.markdown("**Policy evidence**")
                    for excerpt in retest["evaluation"]["evidence"]:
                        st.write("- " + excerpt)
                    st.markdown("**Unsupported commitments**")
                    for excerpt in retest["evaluation"]["unsupported_commitments"]:
                        st.write("- " + excerpt)
                st.caption("One test case cannot prove general safety. "
                           "The original prompt remains unchanged; no deployment occurred.")
