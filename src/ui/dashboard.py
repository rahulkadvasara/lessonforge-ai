"""Dashboard Overview UI component displaying database metrics and health."""
import streamlit as st
from src.memory.repository import MemoryRepository
from src.evaluation.rubric import RUBRIC_MAP


def render_dashboard_overview(repo: MemoryRepository):
    """Render high-level KPIs and historical quality metrics."""
    st.subheader("System Performance & Quality Metrics")

    metrics = repo.get_system_metrics()
    total_runs = metrics["total_runs"]
    approved_runs = metrics["approved_runs"]
    review_runs = metrics["review_runs"]
    avg_attempts = metrics["average_attempts"]
    failure_freqs = metrics["checkpoint_failure_frequencies"]

    approval_rate = round((approved_runs / total_runs * 100), 1) if total_runs > 0 else 0.0

    # KPI Metric Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Generation Runs", total_runs)
    with col2:
        st.metric("Approved Lessons (18/18)", approved_runs, delta=f"{approval_rate}%" if total_runs > 0 else None)
    with col3:
        st.metric("Needs Human Review", review_runs, delta_color="inverse")
    with col4:
        st.metric("Avg Attempts / Run", avg_attempts)
    with col5:
        st.metric("Active Quality Gate", "18 Checkpoints", help="Hard-gate: 100% pass required")

    st.markdown("---")

    col_chart, col_recent = st.columns([1, 1])

    with col_chart:
        st.markdown("### Most Frequently Failed Rubric Checkpoints")
        if failure_freqs:
            # Sort top failed checkpoints
            sorted_fails = sorted(failure_freqs.items(), key=lambda x: x[1], reverse=True)[:6]
            data_dict = {}
            for cid, count in sorted_fails:
                cp = RUBRIC_MAP.get(cid)
                name = cp.name if cp else cid
                data_dict[f"{cid}: {name}"] = count

            st.bar_chart(data_dict)
        else:
            st.info("No rubric rejections recorded yet. Generate your first lesson to track quality failure distribution.")

    with col_recent:
        st.markdown("### Recent Generation Activity")
        recent_runs = repo.list_runs(limit=5)
        if recent_runs:
            for r in recent_runs:
                status_icon = "✅" if r["final_status"] == "APPROVED" else ("⚠️" if r["final_status"] == "NEEDS_HUMAN_REVIEW" else "🔄")
                st.markdown(
                    f"**{status_icon} {r['topic']}**  \n"
                    f"`Run ID`: `{r['run_id'][:12]}...` | `Status`: `{r['final_status']}` | `Attempts`: `{r['attempts_used']}`"
                )
        else:
            st.info("No runs found in the persistent SQLite database.")
