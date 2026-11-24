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
from src.services.llm_service import get_llm_client, MockLLMClient, GroqLLMClient, GeminiLLMClient
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

        provider_choice = st.radio(
            "LLM Provider",
            options=["Google Gemini", "Groq Cloud"],
            index=0 if settings.llm_provider.lower() == "gemini" else 1,
            help="Switch between Google Gemini (high throughput) and Groq Cloud."
        )

        if provider_choice == "Google Gemini":
            api_key_input = st.text_input(
                "Gemini API Key",
                type="password",
                value=settings.gemini_api_key or "",
                help="Enter your Google Gemini API Key or configure it in .env"
            )
            gemini_models = [
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
                "gemini-3.5-flash"
            ]
            default_gem_idx = gemini_models.index(settings.gemini_model) if settings.gemini_model in gemini_models else 0
            model_choice = st.selectbox("Gemini Model", options=gemini_models, index=default_gem_idx)

            use_mock_mode = st.checkbox(
                "Offline / Mock Mode",
                value=not bool(api_key_input or settings.gemini_api_key),
                help="Runs deterministic mock responses (ideal for testing without API keys)."
            )

            if use_mock_mode:
                active_llm = MockLLMClient()
                st.info("ℹ️ Running in Offline / Mock Mode")
            else:
                active_llm = GeminiLLMClient(
                    api_key=api_key_input or settings.gemini_api_key,
                    model_name=model_choice
                )
                st.success(f"Connected to Gemini ({model_choice})")

        else:
            api_key_input = st.text_input(
                "Groq API Key",
                type="password",
                value=settings.groq_api_key or "",
                help="Enter your Groq Cloud API Key or configure it in .env"
            )
            groq_models = [
                "openai/gpt-oss-20b",
                "openai/gpt-oss-120b",
                "qwen/qwen3.8-27b"
            ]
            default_groq_idx = groq_models.index(settings.groq_model) if settings.groq_model in groq_models else 0
            model_choice = st.selectbox("Groq Model", options=groq_models, index=default_groq_idx)

            use_mock_mode = st.checkbox(
                "Offline / Mock Mode",
                value=not bool(api_key_input or settings.groq_api_key),
                help="Runs deterministic mock responses (ideal for testing without API keys)."
            )

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
    all_recent_runs = repo.list_runs(limit=30)
    active_run_id = st.session_state.get("active_run_id")
    if not active_run_id and all_recent_runs:
        active_run_id = all_recent_runs[0]["run_id"]
        st.session_state["active_run_id"] = active_run_id

    latest_output = st.session_state.get("latest_workflow_output")

    if nav_choice == "📊 Dashboard Overview":
        render_dashboard_overview(repo)

    elif nav_choice == "✍️ Generate Lesson":
        render_generation_interface(active_llm)

    elif nav_choice == "⚖️ Evaluation Dashboard":
        if all_recent_runs:
            run_options = {f"{r['created_at']} | {r['topic']} ({r['final_status']})": r["run_id"] for r in all_recent_runs}
            default_idx = 0
            if active_run_id:
                for idx, (label, rid) in enumerate(run_options.items()):
                    if rid == active_run_id:
                        default_idx = idx
                        break

            selected_label = st.selectbox("Select Generation Run to Inspect Audit:", list(run_options.keys()), index=default_idx)
            inspect_run_id = run_options[selected_label]
            evals = repo.get_evaluations_for_run(inspect_run_id)

            if evals:
                if len(evals) > 1:
                    attempt_tabs = st.tabs([f"Attempt #{e['attempt_number']} ({e['overall_status']})" for e in evals])
                    for a_idx, e in enumerate(evals):
                        with attempt_tabs[a_idx]:
                            render_evaluation_report_view(e.get("evaluation_report"))
                else:
                    render_evaluation_report_view(evals[-1].get("evaluation_report"))
            else:
                st.info(f"No evaluation records found for run `{inspect_run_id[:12]}...`.")
        elif latest_output and latest_output.get("evaluation_result"):
            render_evaluation_report_view(latest_output.get("evaluation_result"))
        else:
            st.info("No runs found in database. Run a generation first.")

    elif nav_choice == "🛑 Rejection Log":
        render_rejection_logs_view(repo, active_run_id=active_run_id)

    elif nav_choice == "📖 Final Lesson Viewer":
        st.subheader("Final Lesson Artifact")
        
        if all_recent_runs:
            run_options = {f"{r['created_at']} | {r['topic']} ({r['final_status']})": r["run_id"] for r in all_recent_runs}
            default_idx = 0
            if active_run_id:
                for idx, (label, rid) in enumerate(run_options.items()):
                    if rid == active_run_id:
                        default_idx = idx
                        break

            selected_label = st.selectbox("Select Lesson Run to View:", list(run_options.keys()), index=default_idx)
            view_run_id = run_options[selected_label]
            run_meta = repo.get_run(view_run_id)
            versions = repo.get_lesson_versions(view_run_id)
            evals = repo.get_evaluations_for_run(view_run_id)
            rejections = repo.get_rejection_logs(view_run_id)

            if versions:
                final_v = versions[-1]
                lesson_text = final_v.get("lesson_content", "")
                final_status = run_meta.get("final_status", "UNKNOWN") if run_meta else "UNKNOWN"
                last_eval = evals[-1] if evals else {}
                passed_count = last_eval.get("passed_count", 0)

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
                        file_name=f"lessonforge_{view_run_id[:8]}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                with c_down2:
                    audit_pkg = {
                        "run_id": view_run_id,
                        "topic": run_meta.get("topic") if run_meta else "",
                        "final_status": final_status,
                        "attempts_used": run_meta.get("attempts_used") if run_meta else 1,
                        "evaluations": [e.get("evaluation_report") for e in evals],
                        "rejections": rejections
                    }
                    st.download_button(
                        "📥 Download Audit Report (JSON)",
                        data=json.dumps(audit_pkg, indent=2, default=str),
                        file_name=f"lessonforge_{view_run_id[:8]}_audit.json",
                        mime="application/json",
                        use_container_width=True
                    )

                st.markdown("---")
                st.markdown(lesson_text)
            else:
                st.warning(f"No lesson versions recorded for run `{view_run_id[:12]}...`.")
        elif latest_output and (latest_output.get("final_lesson") or latest_output.get("current_lesson")):
            lesson_text = latest_output.get("final_lesson") or latest_output.get("current_lesson") or ""
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
