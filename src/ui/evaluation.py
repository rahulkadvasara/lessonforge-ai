"""Evaluation Report UI component displaying the 18-checkpoint hard gate."""
import streamlit as st
from typing import Dict, Any, List


def render_evaluation_report_view(evaluation_data: Dict[str, Any] | None):
    """Render structured evaluation results with dimension grouping and PASS/FAIL badges."""
    st.subheader("Hard-Gate Quality Evaluation Audit")

    if not evaluation_data:
        st.info("No active evaluation report in session. Run a generation or select a run from history.")
        return

    overall_status = evaluation_data.get("overall_status", "UNKNOWN")
    passed_count = evaluation_data.get("passed_count", 0)
    failed_count = evaluation_data.get("failed_count", 0)
    checkpoints: List[Dict[str, Any]] = evaluation_data.get("checkpoints", [])

    # Overview Banner
    col_stat, col_p, col_f, col_evaluator = st.columns(4)
    with col_stat:
        if overall_status == "PASS":
            st.success("### STATUS: PASS ✅")
        else:
            st.error("### STATUS: FAIL ❌")
    with col_p:
        st.metric("Passed Checkpoints", f"{passed_count} / 18")
    with col_f:
        st.metric("Failed Checkpoints", f"{failed_count} / 18", delta_color="inverse")
    with col_evaluator:
        st.caption(f"Evaluator Model: `{evaluation_data.get('evaluator_model', 'standard')}`")
        st.caption(f"Audit Timestamp: `{evaluation_data.get('timestamp', 'N/A')}`")

    st.markdown("---")

    # Group checkpoints by dimension
    dimensions: Dict[str, List[Dict[str, Any]]] = {}
    for cp in checkpoints:
        dim = cp.get("dimension", "General")
        if dim not in dimensions:
            dimensions[dim] = []
        dimensions[dim].append(cp)

    st.markdown("### Dimension Breakdown")

    for dim_name, cps in dimensions.items():
        dim_passed = sum(1 for c in cps if c.get("status") == "PASS")
        dim_total = len(cps)
        dim_badge = "🟢 ALL PASS" if dim_passed == dim_total else f"🔴 {dim_total - dim_passed} FAILED"

        with st.expander(f"**{dim_name}** ({dim_passed}/{dim_total} Passed) — {dim_badge}", expanded=(dim_passed != dim_total)):
            for cp in cps:
                status = cp.get("status", "FAIL")
                icon = "✅ PASS" if status == "PASS" else "❌ FAIL"
                
                st.markdown(f"#### `{cp.get('id')}`: {cp.get('name')} — **{icon}**")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Evidence from Lesson:**")
                    st.info(cp.get("evidence") or "None cited.")
                with c2:
                    st.markdown("**Evaluator Reasoning:**")
                    st.write(cp.get("reason") or "No reason provided.")

                if status == "FAIL" and cp.get("suggestion"):
                    st.warning(f"💡 **Improvement Recommendation:** {cp.get('suggestion')}")
                
                st.markdown("---")
