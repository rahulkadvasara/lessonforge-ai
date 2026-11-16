"""Generation UI: controls topic input, learner profile, and live agent workflow tracking."""
import uuid
import streamlit as st
from datetime import datetime, timezone
from src.config.settings import DEFAULT_TOPIC, DEFAULT_LEARNER_PROFILE
from src.graph.workflow import create_workflow_graph
from src.services.llm_service import BaseLLMClient


def render_generation_interface(llm_client: BaseLLMClient):
    """Render topic input, profile configuration, and live agent workflow execution."""
    st.subheader("Generate & Self-Evaluate Lesson")

    col_topic, col_retries = st.columns([3, 1])
    with col_topic:
        topic = st.text_input(
            "Lesson Topic",
            value=DEFAULT_TOPIC,
            help="Educational concept to teach from first principles."
        )

    with col_retries:
        max_retries = st.selectbox(
            "Max Regeneration Retries",
            options=[1, 2],
            index=1,
            help="Hard upper limit enforced at 2 retries (3 attempts total)."
        )

    with st.expander("Learner Profile Configuration (Default: 12th-grade Indian Graduate)", expanded=False):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            target_audience = st.text_input("Target Audience", value=DEFAULT_LEARNER_PROFILE["target_audience"])
            english_prof = st.text_input("English Proficiency", value=DEFAULT_LEARNER_PROFILE["english_proficiency"])
        with col_p2:
            tech_bg = st.text_input("Technical Background", value=DEFAULT_LEARNER_PROFILE["technical_background"])
            learner_goal = st.text_input("Learner Goal", value=DEFAULT_LEARNER_PROFILE["goal"])

    learner_profile = {
        "target_audience": target_audience,
        "english_proficiency": english_prof,
        "technical_background": tech_bg,
        "goal": learner_goal,
        "teaching_guidelines": DEFAULT_LEARNER_PROFILE["teaching_guidelines"]
    }

    start_button = st.button("🚀 Start Agentic Generation & Evaluation Workflow", type="primary", use_container_width=True)

    if start_button:
        run_id = str(uuid.uuid4())
        st.session_state["active_run_id"] = run_id

        # Workflow status placeholders
        status_box = st.status("Executing Agentic Workflow...", expanded=True)
        
        initial_state = {
            "run_id": run_id,
            "topic": topic,
            "learner_profile": learner_profile,
            "max_retries": max_retries,
            "current_attempt": 1,
            "memory_insights": "",
            "grounding_excerpts": "",
            "current_lesson": "",
            "previous_lessons": [],
            "evaluation_result": None,
            "failed_checkpoints": [],
            "feedback_for_regeneration": "",
            "rejection_history": [],
            "final_status": "IN_PROGRESS",
            "final_lesson": None,
            "execution_logs": []
        }

        try:
            workflow = create_workflow_graph(llm_client=llm_client)

            # Stream execution events
            final_output = None
            step_count = 0
            for output in workflow.stream(initial_state):
                step_count += 1
                for node_name, node_state in output.items():
                    logs = node_state.get("execution_logs", [])
                    latest_log = logs[-1] if logs else f"Executed {node_name}"
                    
                    if node_name == "input_validation":
                        status_box.write(f"🔍 **Stage 1: Input Validation** — {latest_log}")
                    elif node_name == "memory_retrieval":
                        status_box.write(f"🧠 **Stage 2: Persistent Memory & Grounding** — {latest_log}")
                    elif node_name == "lesson_generator":
                        status_box.write(f"✍️ **Stage 3: Lesson Generation** — {latest_log}")
                    elif node_name == "content_evaluator":
                        eval_report = node_state.get("evaluation_result", {})
                        overall = eval_report.get("overall_status", "UNKNOWN")
                        passed = eval_report.get("passed_count", 0)
                        icon = "✅" if overall == "PASS" else "❌"
                        status_box.write(f"⚖️ **Stage 4: Quality Gate Audit** — {icon} Status: {overall} ({passed}/18 checkpoints)")
                    elif node_name == "regeneration":
                        attempt = node_state.get("current_attempt", 2)
                        status_box.write(f"🔄 **Stage 5: Intelligent Regeneration** — Attempt {attempt} revised with evaluator feedback.")
                    elif node_name == "record_failure":
                        status_box.write("⚠️ **Stage 5: Bounded Limit Reached** — Max retries exhausted. Marking for human review.")
                    elif node_name == "memory_update":
                        status_box.write(f"💾 **Stage 6: SQLite Memory Update** — Storing execution trace and updating insights.")
                    elif node_name == "finalize":
                        status_box.write("📦 **Stage 7: Finalization & Export Packaging** — Complete.")

                    final_output = node_state

            final_status = final_output.get("final_status", "UNKNOWN") if final_output else "UNKNOWN"
            if final_status == "APPROVED":
                status_box.update(label="🎉 Workflow Completed Successfully — Lesson APPROVED (18/18 Passed)", state="complete")
                st.success("Lesson successfully satisfied all 18 mandatory quality checkpoints!")
            else:
                status_box.update(label="⚠️ Workflow Completed — NEEDS HUMAN REVIEW", state="error")
                st.warning("Lesson reached retry ceiling without passing 100% of rubric checkpoints. Preserved for human review.")

            st.session_state["latest_workflow_output"] = final_output

        except Exception as e:
            status_box.update(label="Workflow Exception Occurred", state="error")
            st.error(f"Error during workflow execution: {e}")
            logger.exception("Workflow execution crashed.")
