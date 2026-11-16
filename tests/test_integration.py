"""End-to-end integration test verifying full agentic lifecycle and SQLite audit trails."""
import os
import json
import tempfile
import pytest
from src.services.llm_service import MockLLMClient
from src.services.export_service import ExportService
from src.memory.database import DatabaseManager
from src.memory.repository import MemoryRepository
from src.memory.learning import SelfEvolutionEngine
from src.agents.memory_agent import MemoryAgent
from src.graph.nodes import WorkflowNodes
from src.graph.workflow import create_workflow_graph
from src.config.settings import DEFAULT_LEARNER_PROFILE
from tests.test_retry_logic import make_eval_json


def test_full_lifecycle_integration():
    """Execute end-to-end workflow, verify all database tables, state history, and exports."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db_path = f.name
    with tempfile.TemporaryDirectory() as temp_export_dir:
        db_mgr = DatabaseManager(temp_db_path)
        repo = MemoryRepository(db_mgr)
        evolution = SelfEvolutionEngine(db_mgr)
        memory_agent = MemoryAgent(repo, evolution)
        export_svc = ExportService(temp_export_dir)

        mock_llm = MockLLMClient()
        # Attempt 1: Fails on EXA_01
        mock_llm.queue_evaluator_response(make_eval_json(pass_all=False, fail_ids=["EXA_01"]))
        # Attempt 2: Passes all 18
        mock_llm.queue_evaluator_response(make_eval_json(pass_all=True))

        nodes = WorkflowNodes(
            llm_client=mock_llm,
            repository=repo,
            memory_agent=memory_agent,
            export_service=export_svc
        )

        graph = create_workflow_graph(nodes=nodes, llm_client=mock_llm)

        run_id = "integration-run-001"
        initial_state = {
            "run_id": run_id,
            "topic": "Introduction to RAG (Retrieval-Augmented Generation)",
            "learner_profile": DEFAULT_LEARNER_PROFILE,
            "max_retries": 2,
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

        final_state = graph.invoke(initial_state)

        # 1. Verify Final State
        assert final_state["final_status"] == "APPROVED"
        assert final_state["current_attempt"] == 2
        assert len(final_state["previous_lessons"]) == 2

        # 2. Verify Database Records
        db_run = repo.get_run(run_id)
        assert db_run is not None
        assert db_run["final_status"] == "APPROVED"
        assert db_run["attempts_used"] == 2

        versions = repo.get_lesson_versions(run_id)
        assert len(versions) == 2
        assert versions[0]["attempt_number"] == 1
        assert versions[1]["attempt_number"] == 2

        evals = repo.get_evaluations_for_run(run_id)
        assert len(evals) == 2
        assert evals[0]["overall_status"] == "FAIL"
        assert evals[1]["overall_status"] == "PASS"

        rejections = repo.get_rejection_logs(run_id)
        assert len(rejections) == 1
        assert "EXA_01" in rejections[0]["failed_checkpoint_ids"]

        # 3. Verify Self-Evolution Insight Extraction
        insights = evolution.get_active_insights()
        assert len(insights) >= 1
        assert any(ins["checkpoint_id"] == "EXA_01" for ins in insights)

        # 4. Verify Export Files Created
        md_file = os.path.join(temp_export_dir, f"{run_id}_lesson.md")
        json_file = os.path.join(temp_export_dir, f"{run_id}_audit_report.json")
        assert os.path.exists(md_file)
        assert os.path.exists(json_file)

    # Cleanup DB
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)
