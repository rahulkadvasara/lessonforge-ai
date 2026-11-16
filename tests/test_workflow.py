"""Unit tests for LangGraph workflow orchestration and nodes."""
import pytest
from src.graph.workflow import create_workflow_graph, decide_after_validation, decide_after_evaluation
from src.services.llm_service import MockLLMClient
from src.config.settings import DEFAULT_LEARNER_PROFILE


def test_input_validation_rejection_on_empty_topic():
    """Verify workflow aborts gracefully if topic is invalid."""
    mock_llm = MockLLMClient()
    graph = create_workflow_graph(llm_client=mock_llm)

    state = {
        "run_id": "test-invalid-input",
        "topic": "  ",  # empty
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
    assert result["final_status"] == "FAILED_INPUT"


def test_routing_functions():
    """Test decision logic after evaluation."""
    # When pass
    state_pass = {"evaluation_result": {"overall_status": "PASS"}}
    assert decide_after_evaluation(state_pass) == "memory_update"

    # When fail, attempt 1 <= max_retries 2 -> regeneration
    state_fail_1 = {
        "evaluation_result": {"overall_status": "FAIL"},
        "current_attempt": 1,
        "max_retries": 2
    }
    assert decide_after_evaluation(state_fail_1) == "regeneration"

    # When fail, attempt 3 > max_retries 2 -> record_failure
    state_fail_3 = {
        "evaluation_result": {"overall_status": "FAIL"},
        "current_attempt": 3,
        "max_retries": 2
    }
    assert decide_after_evaluation(state_fail_3) == "record_failure"
