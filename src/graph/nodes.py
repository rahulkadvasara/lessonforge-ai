"""Implementation of LangGraph nodes for lesson generation, evaluation, and iteration."""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from src.graph.state import WorkflowState
from src.agents.generator import LessonGeneratorAgent
from src.agents.evaluator import ContentEvaluatorAgent
from src.agents.memory_agent import MemoryAgent
from src.memory.repository import MemoryRepository
from src.services.export_service import ExportService
from src.services.llm_service import BaseLLMClient, get_llm_client

logger = logging.getLogger(__name__)


class WorkflowNodes:
    """Encapsulates all node functions for the LangGraph workflow with dependency injection."""

    def __init__(
        self,
        llm_client: BaseLLMClient | None = None,
        generator_agent: LessonGeneratorAgent | None = None,
        evaluator_agent: ContentEvaluatorAgent | None = None,
        memory_agent: MemoryAgent | None = None,
        repository: MemoryRepository | None = None,
        export_service: ExportService | None = None
    ):
        self.llm = llm_client or get_llm_client()
        self.generator = generator_agent or LessonGeneratorAgent(self.llm)
        self.evaluator = evaluator_agent or ContentEvaluatorAgent(self.llm)
        self.repo = repository or MemoryRepository()
        self.memory_agent = memory_agent or MemoryAgent(self.repo)
        self.export_service = export_service or ExportService()

    def input_validation_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Validate input topic, learner profile, and initialize run record."""
        logs = list(state.get("execution_logs", []))
        topic = state.get("topic", "").strip()

        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Validating input: '{topic}'")

        if not topic or len(topic) < 3:
            logs.append(f"Validation failed: Topic '{topic}' is too short or empty.")
            return {
                "final_status": "FAILED_INPUT",
                "execution_logs": logs
            }

        # Initialize run in database
        self.repo.create_run(
            run_id=state["run_id"],
            topic=topic,
            learner_profile=state["learner_profile"],
            max_retries=state["max_retries"]
        )

        logs.append(f"Input validated successfully. Initialized Run ID: {state['run_id']}")
        return {
            "execution_logs": logs,
            "current_attempt": 1,
            "previous_lessons": [],
            "rejection_history": []
        }

    def memory_retrieval_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Fetch past quality insights and grounding context."""
        logs = list(state.get("execution_logs", []))
        topic = state["topic"]
        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Querying persistent memory and self-evolution engine...")

        insights_prompt = self.memory_agent.retrieve_context_for_generation(topic)
        grounding_context = self.generator.grounding.get_grounding_context(topic)

        logs.append("Persistent memory insights and authoritative reference context loaded.")
        return {
            "memory_insights": insights_prompt,
            "grounding_excerpts": grounding_context,
            "execution_logs": logs
        }

    def lesson_generator_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate initial complete lesson."""
        logs = list(state.get("execution_logs", []))
        attempt = state["current_attempt"]
        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Generating initial lesson (Attempt {attempt})...")

        lesson_text = self.generator.generate_initial_lesson(
            topic=state["topic"],
            learner_profile=state["learner_profile"],
            memory_insights=state.get("memory_insights", "")
        )

        word_count = len(lesson_text.split())
        logs.append(f"Initial lesson generated ({word_count} words).")

        # Persist version to database
        self.repo.save_lesson_version(
            run_id=state["run_id"],
            attempt_number=attempt,
            lesson_content=lesson_text
        )

        prev_lessons = list(state.get("previous_lessons", []))
        prev_lessons.append({
            "attempt": attempt,
            "content": lesson_text,
            "word_count": word_count
        })

        return {
            "current_lesson": lesson_text,
            "previous_lessons": prev_lessons,
            "execution_logs": logs
        }

    def content_evaluator_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute independent 18-checkpoint evaluation."""
        logs = list(state.get("execution_logs", []))
        attempt = state["current_attempt"]
        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Auditing lesson attempt {attempt} against 18-checkpoint hard-gate rubric...")

        report = self.evaluator.evaluate_lesson(
            topic=state["topic"],
            learner_profile=state["learner_profile"],
            lesson_text=state["current_lesson"]
        )

        report_dict = report.model_dump()
        failed_cps = [cp for cp in report_dict["checkpoints"] if cp["status"] == "FAIL"]

        logs.append(
            f"Audit complete. Status: {report.overall_status} "
            f"({report.passed_count}/18 Passed, {report.failed_count}/18 Failed)"
        )

        # Persist evaluation result to SQLite
        self.repo.save_evaluation_result(
            run_id=state["run_id"],
            attempt_number=attempt,
            overall_status=report.overall_status,
            passed_count=report.passed_count,
            failed_count=report.failed_count,
            evaluation_json=json.dumps(report_dict)
        )

        return {
            "evaluation_result": report_dict,
            "failed_checkpoints": failed_cps,
            "execution_logs": logs
        }

    def regeneration_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Intelligently regenerate lesson targeting failed checkpoints."""
        logs = list(state.get("execution_logs", []))
        current_attempt = state["current_attempt"]
        next_attempt = current_attempt + 1
        failed_cps = state.get("failed_checkpoints", [])

        failed_ids = [cp["id"] for cp in failed_cps]
        reasons = [cp.get("reason", "") for cp in failed_cps]
        suggestions = [cp.get("suggestion", "") for cp in failed_cps]

        logs.append(
            f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Attempt {current_attempt} rejected. "
            f"Failed checkpoints: {', '.join(failed_ids)}. Preparing regeneration attempt {next_attempt}..."
        )

        # Record rejection log in database
        self.repo.save_rejection_log(
            run_id=state["run_id"],
            attempt_number=current_attempt,
            failed_checkpoint_ids=failed_ids,
            reasons=reasons,
            suggestions=suggestions,
            changes_made=f"Targeted repair of checkpoints: {', '.join(failed_ids)}"
        )

        rejection_hist = list(state.get("rejection_history", []))
        rejection_hist.append({
            "attempt": current_attempt,
            "failed_checkpoint_ids": failed_ids,
            "reasons": reasons,
            "suggestions": suggestions
        })

        # Generate revised lesson
        revised_text = self.generator.regenerate_lesson(
            topic=state["topic"],
            learner_profile=state["learner_profile"],
            previous_lesson=state["current_lesson"],
            failed_checkpoints=failed_cps,
            attempt_number=next_attempt,
            max_retries=state["max_retries"]
        )

        word_count = len(revised_text.split())
        logs.append(f"Regenerated lesson version created for Attempt {next_attempt} ({word_count} words).")

        # Save new lesson version
        self.repo.save_lesson_version(
            run_id=state["run_id"],
            attempt_number=next_attempt,
            lesson_content=revised_text
        )

        prev_lessons = list(state.get("previous_lessons", []))
        prev_lessons.append({
            "attempt": next_attempt,
            "content": revised_text,
            "word_count": word_count
        })

        return {
            "current_attempt": next_attempt,
            "current_lesson": revised_text,
            "previous_lessons": prev_lessons,
            "rejection_history": rejection_hist,
            "execution_logs": logs
        }

    def record_failure_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Handle exhausted retry limit without achieving 100% pass."""
        logs = list(state.get("execution_logs", []))
        current_attempt = state["current_attempt"]
        failed_cps = state.get("failed_checkpoints", [])

        failed_ids = [cp["id"] for cp in failed_cps]
        reasons = [cp.get("reason", "") for cp in failed_cps]
        suggestions = [cp.get("suggestion", "") for cp in failed_cps]

        logs.append(
            f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Maximum retries reached. "
            f"Final attempt {current_attempt} failed {len(failed_cps)} checkpoints. Marking as NEEDS_HUMAN_REVIEW."
        )

        # Log final rejection
        self.repo.save_rejection_log(
            run_id=state["run_id"],
            attempt_number=current_attempt,
            failed_checkpoint_ids=failed_ids,
            reasons=reasons,
            suggestions=suggestions,
            changes_made="Terminal attempt failed; requires human review."
        )

        rejection_hist = list(state.get("rejection_history", []))
        rejection_hist.append({
            "attempt": current_attempt,
            "failed_checkpoint_ids": failed_ids,
            "reasons": reasons,
            "suggestions": suggestions
        })

        return {
            "final_status": "NEEDS_HUMAN_REVIEW",
            "final_lesson": state["current_lesson"],
            "rejection_history": rejection_hist,
            "execution_logs": logs
        }

    def memory_update_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Update memory repository, trigger self-evolution, and set final status."""
        logs = list(state.get("execution_logs", []))
        final_status = state.get("final_status")

        if not final_status or final_status == "IN_PROGRESS":
            eval_res = state.get("evaluation_result", {})
            if eval_res.get("overall_status") == "PASS":
                final_status = "APPROVED"
            else:
                final_status = "NEEDS_HUMAN_REVIEW"

        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Updating application memory. Final Status: {final_status}")

        self.memory_agent.record_run_completion(
            run_id=state["run_id"],
            topic=state["topic"],
            learner_profile=state["learner_profile"],
            attempts_used=state["current_attempt"],
            final_status=final_status,
            lesson_versions=state.get("previous_lessons", []),
            evaluation_history=[state.get("evaluation_result", {})],
            rejection_history=state.get("rejection_history", [])
        )

        return {
            "final_status": final_status,
            "final_lesson": state["current_lesson"],
            "execution_logs": logs
        }

    def finalize_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Export artifacts and finalize execution state."""
        logs = list(state.get("execution_logs", []))
        final_status = state.get("final_status", "UNKNOWN")
        topic = state["topic"]
        run_id = state["run_id"]

        logs.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Finalizing run {run_id}. Packaging exports...")

        lesson_text = state.get("final_lesson", state.get("current_lesson", ""))
        md_path = self.export_service.export_markdown(run_id, topic, lesson_text, final_status)
        
        run_meta = self.repo.get_run(run_id) or {"run_id": run_id, "final_status": final_status}
        versions = self.repo.get_lesson_versions(run_id)
        evals = self.repo.get_evaluations_for_run(run_id)
        rejections = self.repo.get_rejection_logs(run_id)

        json_path = self.export_service.export_json_report(run_meta, versions, evals, rejections)
        logs.append(f"Artifacts exported:\n- Markdown: {md_path}\n- JSON Audit Report: {json_path}")
        logs.append(f"Workflow execution finished with status: {final_status}.")

        return {
            "final_status": final_status,
            "final_lesson": lesson_text,
            "execution_logs": logs
        }
