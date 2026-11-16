"""Unit tests for SQLite persistent memory, learning insights, and export services."""
import os
import json
import tempfile
import pytest
from src.memory.database import DatabaseManager
from src.memory.repository import MemoryRepository
from src.memory.learning import SelfEvolutionEngine
from src.services.export_service import ExportService


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file for isolation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name
    db_mgr = DatabaseManager(temp_path)
    yield db_mgr
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_persistent_memory_survives_restart(temp_db):
    """Test 8: Verify runs and data survive application restart/reinitialization."""
    repo = MemoryRepository(temp_db)
    run_id = "test-run-123"
    repo.create_run(run_id, "Intro to RAG", {"learner": "test"}, max_retries=2)
    repo.save_lesson_version(run_id, 1, "Content of attempt 1")
    repo.update_run_status(run_id, "APPROVED", 1)

    # Reinitialize a new DatabaseManager pointing to the exact same database file
    new_db_mgr = DatabaseManager(temp_db.db_path)
    new_repo = MemoryRepository(new_db_mgr)

    retrieved = new_repo.get_run(run_id)
    assert retrieved is not None
    assert retrieved["run_id"] == run_id
    assert retrieved["final_status"] == "APPROVED"

    versions = new_repo.get_lesson_versions(run_id)
    assert len(versions) == 1
    assert versions[0]["lesson_content"] == "Content of attempt 1"


def test_learning_from_failures_and_insights(temp_db):
    """Test 9: Introduce repeated failures, verify recurring insights generated and formatted."""
    repo = MemoryRepository(temp_db)
    engine = SelfEvolutionEngine(temp_db)

    run_id = "run-fail-test"
    repo.create_run(run_id, "RAG Concepts", {}, max_retries=2)

    # Simulate 2 rejections on checkpoint BEG_02 (vocabulary too complex)
    repo.save_rejection_log(
        run_id=run_id,
        attempt_number=1,
        failed_checkpoint_ids=["BEG_02"],
        reasons=["Vocabulary too complex for 12th grader."],
        suggestions=["Use simpler everyday terms for embeddings."]
    )
    repo.save_rejection_log(
        run_id=run_id,
        attempt_number=2,
        failed_checkpoint_ids=["BEG_02"],
        reasons=["Still contains high-level jargon."],
        suggestions=["Explain terms immediately upon appearance."]
    )

    insights = engine.analyze_and_update_insights()
    assert len(insights) >= 1
    
    beg_insight = next((ins for ins in insights if ins["checkpoint_id"] == "BEG_02"), None)
    assert beg_insight is not None
    assert beg_insight["occurrence_count"] == 2

    # Check formatted prompt context injection
    prompt_context = engine.format_insights_for_prompt()
    assert "BEG_02" in prompt_context
    assert "CRITICAL LESSONS LEARNED" in prompt_context


def test_user_feedback_persistence(temp_db):
    """Test 10: Submit positive and negative feedback, verify persistence and retrieval."""
    repo = MemoryRepository(temp_db)
    run_id = "run-fb-test"
    repo.create_run(run_id, "RAG", {}, 2)

    repo.save_user_feedback(run_id, "POSITIVE", "Very clear explanation!")
    repo.save_user_feedback(run_id, "NEGATIVE", "Needs more quiz questions.")

    feedback_list = repo.get_user_feedback(run_id)
    assert len(feedback_list) == 2
    assert feedback_list[0]["feedback_type"] == "POSITIVE"
    assert feedback_list[0]["comments"] == "Very clear explanation!"
    assert feedback_list[1]["feedback_type"] == "NEGATIVE"


def test_version_history_retention(temp_db):
    """Test 11: Verify all versions and evaluations are retained."""
    repo = MemoryRepository(temp_db)
    run_id = "run-versions"
    repo.create_run(run_id, "RAG", {}, 2)

    repo.save_lesson_version(run_id, 1, "Attempt 1 content")
    repo.save_lesson_version(run_id, 2, "Attempt 2 content")
    repo.save_lesson_version(run_id, 3, "Attempt 3 content")

    versions = repo.get_lesson_versions(run_id)
    assert len(versions) == 3
    assert [v["attempt_number"] for v in versions] == [1, 2, 3]


def test_export_service(tmp_path):
    """Test 12: Verify Markdown and JSON exports."""
    export_svc = ExportService(exports_dir=str(tmp_path))
    run_id = "test-export-run"

    md_path = export_svc.export_markdown(run_id, "Introduction to RAG", "## Lesson Text", "APPROVED")
    assert os.path.exists(md_path)
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "APPROVED" in content
        assert "## Lesson Text" in content

    json_path = export_svc.export_json_report(
        run_data={"run_id": run_id, "status": "APPROVED"},
        lesson_versions=[{"attempt": 1, "text": "Lesson"}],
        evaluations=[{"overall_status": "PASS"}],
        rejections=[]
    )
    assert os.path.exists(json_path)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["run_metadata"]["run_id"] == run_id
        assert data["version_count"] == 1
