"""Tests verifying the bounded regeneration engine, retry limits, and failure escalation."""
import json
import pytest
from src.services.llm_service import MockLLMClient
from src.graph.workflow import create_workflow_graph
from src.config.settings import DEFAULT_LEARNER_PROFILE
from src.evaluation.rubric import RUBRIC_CHECKPOINTS


def make_eval_json(pass_all: bool = True, fail_ids: list[str] = None) -> str:
    """Helper to synthesize a compliant EvaluationReport JSON string."""
    fail_set = set(fail_ids or [])
    checkpoints = []
    for cp in RUBRIC_CHECKPOINTS:
        is_pass = pass_all and (cp.id not in fail_set)
        checkpoints.append({
            "id": cp.id,
            "dimension": cp.dimension,
            "name": cp.name,
            "status": "PASS" if is_pass else "FAIL",
            "evidence": "Evidence text",
            "reason": "Evaluator reasoning",
            "suggestion": "Fix this checkpoint" if not is_pass else None
        })
    passed_count = sum(1 for c in checkpoints if c["status"] == "PASS")
    failed_count = sum(1 for c in checkpoints if c["status"] == "FAIL")
    overall = "PASS" if failed_count == 0 else "FAIL"

    return json.dumps({
        "overall_status": overall,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "checkpoints": checkpoints
    })


def test_scenario_1_first_attempt_passes():
    """Test 1: Initial generation passes immediately. No regeneration occurs."""
    mock_llm = MockLLMClient()
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=True))

    graph = create_workflow_graph(llm_client=mock_llm)

    state = {
        "run_id": "test-s1-pass",
        "topic": "Introduction to RAG",
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

    result = graph.invoke(state)

    assert result["final_status"] == "APPROVED"
    assert result["current_attempt"] == 1
    assert len(result["previous_lessons"]) == 1
    assert len(result["rejection_history"]) == 0


def test_scenario_2_first_fails_second_passes():
    """Test 2: First attempt fails, feedback provided, second attempt passes."""
    mock_llm = MockLLMClient()
    # Attempt 1: Fail BEG_02
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=False, fail_ids=["BEG_02"]))
    # Attempt 2: Pass all
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=True))

    graph = create_workflow_graph(llm_client=mock_llm)

    state = {
        "run_id": "test-s2-fail-pass",
        "topic": "Introduction to RAG",
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

    result = graph.invoke(state)

    assert result["final_status"] == "APPROVED"
    assert result["current_attempt"] == 2
    assert len(result["previous_lessons"]) == 2
    assert len(result["rejection_history"]) == 1
    assert "BEG_02" in result["rejection_history"][0]["failed_checkpoint_ids"]


def test_scenario_3_two_regenerations_required_then_passes():
    """Test 3: First fails, second fails, third passes."""
    mock_llm = MockLLMClient()
    # Attempt 1: Fail ACC_01
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=False, fail_ids=["ACC_01"]))
    # Attempt 2: Fail CLR_01
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=False, fail_ids=["CLR_01"]))
    # Attempt 3: Pass all
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=True))

    graph = create_workflow_graph(llm_client=mock_llm)

    state = {
        "run_id": "test-s3-two-retries",
        "topic": "Introduction to RAG",
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

    result = graph.invoke(state)

    assert result["final_status"] == "APPROVED"
    assert result["current_attempt"] == 3
    assert len(result["previous_lessons"]) == 3
    assert len(result["rejection_history"]) == 2


def test_scenario_4_and_5_all_attempts_fail_enforces_retry_ceiling():
    """Test 4 & 5: Initial fails, retry 1 fails, retry 2 fails -> NEVER loops, marks NEEDS_HUMAN_REVIEW."""
    mock_llm = MockLLMClient()
    # 3 failures queued
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=False, fail_ids=["ACC_01"]))
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=False, fail_ids=["ACC_01"]))
    mock_llm.queue_evaluator_response(make_eval_json(pass_all=False, fail_ids=["ACC_01"]))

    graph = create_workflow_graph(llm_client=mock_llm)

    state = {
        "run_id": "test-s4-all-fail",
        "topic": "Introduction to RAG",
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

    result = graph.invoke(state)

    # Must terminate with NEEDS_HUMAN_REVIEW
    assert result["final_status"] == "NEEDS_HUMAN_REVIEW"
    # Current attempt reached 3
    assert result["current_attempt"] == 3
    # Exactly 3 versions created (Initial 1 + 2 retries)
    assert len(result["previous_lessons"]) == 3
    # Exactly 3 rejections recorded
    assert len(result["rejection_history"]) == 3
    # Must preserve the latest generated lesson
    assert result["final_lesson"] is not None
    assert len(result["final_lesson"]) > 0
