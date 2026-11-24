"""LessonForge AI — Self-Evaluating Learning Content Generator
Main Streamlit Application Entrypoint.
"""
import os
import json
import streamlit as st
from src.config.settings import get_settings
from src.memory.database import get_db_manager
from src.memory.repository import MemoryRepository
from src.memory.learning import SelfEvolutionEngine
from src.services.llm_service import get_llm_client, MockLLMClient, GroqLLMClient
from src.services.export_service import ExportService
from src.evaluation.rubric import RUBRIC_CHECKPOINTS

from src.ui.dashboard import render_dashboard_overview
from src.ui.generation import render_generation_interface
from src.ui.evaluation import render_evaluation_report_view
from src.ui.history import render_run_history_view, render_rejection_logs_view
from src.ui.memory import render_memory_and_learning_view


# Page Configuration
st.set_page_config(
    page_title="LessonForge AI — Self-Evaluating Content Generator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for polished look
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-pass { background-color: #DEF7EC; color: #03543F; }
    .status-fail { background-color: #FDE8E8; color: #9B1C1C; }
</style>
""", unsafe_allow_html=True)


def init_services():
    """Initialize singleton repositories and services."""
    settings = get_settings()
    db = get_db_manager()
    repo = MemoryRepository(db)
    evolution = SelfEvolutionEngine(db)
    export_svc = ExportService()
    return settings, repo, evolution, export_svc


def main():
    settings, repo, evolution, export_svc = init_services()

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("## 🎓 LessonForge AI")
        st.caption("Autonomous Self-Evaluating Educational Content Engine")
        st.markdown("---")

        nav_choice = st.radio(
            "Navigation Menu",
            options=[
                "📊 Dashboard Overview",
                "✍️ Generate Lesson",
                "⚖️ Evaluation Dashboard",
                "🛑 Rejection Log",
                "📖 Final Lesson Viewer",
                "📜 Run History",
                "🧠 Memory & Learning",
                "📋 Evaluation Rubric"
            ],
            index=1  # Default to Generate Lesson
        )

        st.markdown("---")
        st.markdown("### ⚙️ Engine Configuration")

        api_key_input = st.text_input(
            "Groq API Key",
            type="password",
            value=settings.groq_api_key or "",
            help="Enter your Groq Cloud API Key or configure it in .env"
        )

        available_models = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b"
        ]
        default_index = available_models.index(settings.groq_model) if settings.groq_model in available_models else 0

        model_choice = st.selectbox(
            "Groq Model",
            options=available_models,
            index=default_index
        )

        use_mock_mode = st.checkbox(
            "Offline / Mock Mode",
            value=not bool(api_key_input or settings.groq_api_key),
            help="Runs the agent workflow using deterministic mock responses (ideal for testing/demo without API keys)."
        )

        # Instantiate LLM client according to settings
        if use_mock_mode:
            active_llm = MockLLMClient()
            st.info("ℹ️ Running in Offline / Mock Mode")
        else:
            active_llm = GroqLLMClient(
                api_key=api_key_input or settings.groq_api_key,
                model_name=model_choice
            )
            st.success(f"Connected to Groq ({model_choice})")

    # Header
    st.markdown('<div class="main-title">LessonForge AI — Self-Evaluating Content Generator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Closed-loop agentic lesson creation with hard-gate 18-checkpoint binary evaluation and bounded regeneration.</div>', unsafe_allow_html=True)

    # --- ROUTING ---
    active_run_id = st.session_state.get("active_run_id")
    latest_output = st.session_state.get("latest_workflow_output")

    if nav_choice == "📊 Dashboard Overview":
        render_dashboard_overview(repo)

    elif nav_choice == "✍️ Generate Lesson":
        render_generation_interface(active_llm)

    elif nav_choice == "⚖️ Evaluation Dashboard":
        eval_data = None
        if latest_output:
            eval_data = latest_output.get("evaluation_result")
        elif active_run_id:
            evals = repo.get_evaluations_for_run(active_run_id)
            if evals:
                eval_data = evals[-1].get("evaluation_report")
        render_evaluation_report_view(eval_data)

    elif nav_choice == "🛑 Rejection Log":
        render_rejection_logs_view(repo, active_run_id=active_run_id)

    elif nav_choice == "📖 Final Lesson Viewer":
        st.subheader("Final Lesson Artifact")
        if latest_output:
            final_status = latest_output.get("final_status", "UNKNOWN")
            lesson_text = latest_output.get("final_lesson") or latest_output.get("current_lesson") or ""
            eval_res = latest_output.get("evaluation_result", {})
            passed_count = eval_res.get("passed_count", 0)

            if final_status == "APPROVED":
                st.success(f"### ✅ APPROVED CONTENT — Quality Gate Passed ({passed_count}/18 Checkpoints)")
            else:
                st.error(f"### ⚠️ NEEDS HUMAN REVIEW — Quality Gate Incomplete ({passed_count}/18 Checkpoints)")
                st.caption("Content did not satisfy all 18 mandatory checkpoints within the bounded retry limit.")

            c_down1, c_down2 = st.columns(2)
            with c_down1:
                st.download_button(
                    "📥 Download Lesson (Markdown)",
                    data=lesson_text,
                    file_name="lessonforge_lesson.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            with c_down2:
                audit_pkg = {
                    "run_id": latest_output.get("run_id"),
                    "final_status": final_status,
                    "evaluation": eval_res,
                    "rejections": latest_output.get("rejection_history", [])
                }
                st.download_button(
                    "📥 Download Audit Report (JSON)",
                    data=json.dumps(audit_pkg, indent=2, default=str),
                    file_name="lessonforge_audit.json",
                    mime="application/json",
                    use_container_width=True
                )

            st.markdown("---")
            st.markdown(lesson_text)
        else:
            st.info("No lesson generated in this active session. Navigate to '✍️ Generate Lesson' to create one.")

    elif nav_choice == "📜 Run History":
        render_run_history_view(repo, export_svc)

    elif nav_choice == "🧠 Memory & Learning":
        render_memory_and_learning_view(repo, evolution, active_run_id=active_run_id)

    elif nav_choice == "📋 Evaluation Rubric":
        st.subheader("Official 18-Checkpoint Hard-Gate Quality Rubric")
        st.markdown(
            "Every lesson must satisfy **100% of the following 18 criteria** across 6 dimensions. "
            "A failure in any single checkpoint causes an immediate overall `FAIL` and triggers targeted regeneration."
        )
        for cp in RUBRIC_CHECKPOINTS:
            with st.expander(f"**{cp.id}: {cp.name}** — *{cp.dimension}*"):
                st.markdown(f"**Description:** {cp.description}")
                st.markdown(f"**Pass Criteria:** {cp.pass_criteria}")
                st.markdown(f"**Fail Criteria:** {cp.fail_criteria}")


if __name__ == "__main__":
    main()
