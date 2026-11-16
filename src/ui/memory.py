"""Memory & Self-Evolution UI component: displays learned insights and manages user feedback."""
import streamlit as st
from src.memory.repository import MemoryRepository
from src.memory.learning import SelfEvolutionEngine


def render_memory_and_learning_view(repo: MemoryRepository, evolution: SelfEvolutionEngine, active_run_id: str | None = None):
    """Render self-evolution insights, failure clustering, and user feedback submission."""
    st.subheader("Persistent Memory & Self-Evolution Engine")

    # Refresh insights from rejection logs
    active_insights = evolution.analyze_and_update_insights()

    tab_insights, tab_feedback, tab_prompts = st.tabs([
        "🧠 Learned Insights & Patterns",
        "💬 User Feedback Mechanism",
        "📜 System & Prompt Versions"
    ])

    with tab_insights:
        st.markdown("### Active Continuous-Learning Insights")
        st.caption("Insights automatically extracted from historical rejection patterns and injected into future generation prompts.")

        if active_insights:
            for ins in active_insights:
                with st.container():
                    st.markdown(
                        f"**🎯 Checkpoint: `{ins['checkpoint_id']}` ({ins['dimension']})**  \n"
                        f"*Pattern Detected:* {ins['pattern_description']} (Occurred {ins['occurrence_count']} time(s))  \n"
                        f"**Actionable Recommendation:** `{ins['recommendation']}`  \n"
                        f"<small>Last updated: {ins['last_detected_at']}</small>",
                        unsafe_allow_html=True
                    )
                    st.markdown("---")
        else:
            st.info("No learned insights accumulated yet. Insights are automatically derived when the evaluator rejects lessons.")

    with tab_feedback:
        st.markdown("### Submit User Feedback for Lesson Quality")
        st.caption("Human-in-the-loop signals are persisted in SQLite and incorporated into future generation context.")

        runs = repo.list_runs(limit=20)
        if runs:
            run_dict = {f"{r['topic']} ({r['run_id'][:8]})": r["run_id"] for r in runs}
            target_run_label = st.selectbox("Select Target Run:", list(run_dict.keys()), index=0)
            target_run_id = run_dict[target_run_label]

            col_fb_type, col_comments = st.columns([1, 2])
            with col_fb_type:
                fb_type = st.radio("Rating:", ["👍 POSITIVE (Helpful)", "👎 NEGATIVE (Flawed)"], index=0)
                clean_type = "POSITIVE" if "POSITIVE" in fb_type else "NEGATIVE"
            
            with col_comments:
                comments = st.text_area("Optional Written Feedback:", placeholder="E.g. Great analogy for embeddings, but could explain vector databases more slowly.")

            if st.button("Submit Feedback", type="primary"):
                repo.save_user_feedback(target_run_id, clean_type, comments)
                st.success("Feedback saved successfully to persistent database!")

        st.markdown("#### Historical User Feedback Logs")
        all_feedback = repo.get_user_feedback()
        if all_feedback:
            for fb in all_feedback:
                icon = "👍" if fb["feedback_type"] == "POSITIVE" else "👎"
                st.markdown(
                    f"**{icon} {fb['feedback_type']}** on Run `{fb['run_id'][:8]}...` at `{fb['created_at']}`:  \n"
                    f"> *{fb['comments'] or 'No written comments.'}*"
                )
        else:
            st.info("No human feedback recorded yet.")

    with tab_prompts:
        st.markdown("### Audited Prompt & Rubric Versions")
        st.markdown("""
        - **Generator Prompt**: `v1.2` (Enforces 17 mandatory sections, zero-jargon baseline, 12th-grade Indian graduate persona)
        - **Evaluator Rubric**: `v2.0` (Enforces 18 explicit binary checkpoints across 6 quality dimensions)
        - **Regeneration Prompt**: `v1.1` (Structured delta feedback injection, preserving passed sections)
        - **Knowledge Grounding Reference**: `NeurIPS 2020 Lewis et al. RAG corpus + LangChain vectorstore specs`
        """)
