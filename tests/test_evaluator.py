"""Unit tests for the independent Content Evaluator and strict hard gate."""
import json
import pytest
from src.services.llm_service import MockLLMClient
from src.agents.evaluator import ContentEvaluatorAgent
from src.evaluation.validators import validate_evaluation_report, perform_deterministic_lesson_checks
from src.evaluation.rubric import RUBRIC_CHECKPOINTS, TOTAL_CHECKPOINTS_COUNT
from src.config.settings import DEFAULT_LEARNER_PROFILE


def test_evaluator_all_pass():
    """Verify that when all 18 checkpoints pass, overall status is PASS."""
    mock_llm = MockLLMClient()
    agent = ContentEvaluatorAgent(llm_client=mock_llm)

    sample_lesson = "# Lesson\n## 1. Lesson Title\nIntro to RAG\n"
    report = agent.evaluate_lesson("Introduction to RAG", DEFAULT_LEARNER_PROFILE, sample_lesson)

    assert report.overall_status == "PASS"
    assert report.passed_count == 18
    assert report.failed_count == 0
    assert len(report.checkpoints) == 18


def test_strict_pass_fail_single_failure_fails_all():
    """Requirement: If even one checkpoint fails, overall_status MUST be FAIL. No score averaging."""
    checkpoints = []
    for i, cp in enumerate(RUBRIC_CHECKPOINTS):
        # Fail just the first checkpoint
        status = "FAIL" if i == 0 else "PASS"
        checkpoints.append({
            "id": cp.id,
            "dimension": cp.dimension,
            "name": cp.name,
            "status": status,
            "evidence": "Evidence quote",
            "reason": "Test explanation",
            "suggestion": "Fix it" if status == "FAIL" else None
        })

    raw_json = {
        "overall_status": "PASS",  # Attempting to falsely claim PASS despite failure
        "passed_count": 17,
        "failed_count": 1,
        "checkpoints": checkpoints
    }

    report = validate_evaluation_report(raw_json)
    # The validator must override and enforce FAIL
    assert report.overall_status == "FAIL"
    assert report.passed_count == 17
    assert report.failed_count == 1


def test_malformed_evaluator_output_safe_handling():
    """Requirement: Malformed JSON or missing checkpoints must never falsely approve."""
    mock_llm = MockLLMClient()
    mock_llm.queue_evaluator_response("IRREVOCABLE_GARBAGE_JSON_NOT_A_DICT")
    agent = ContentEvaluatorAgent(llm_client=mock_llm)

    report = agent.evaluate_lesson("Introduction to RAG", DEFAULT_LEARNER_PROFILE, "lesson text")
    assert report.overall_status == "FAIL"
    assert report.passed_count == 0
    assert report.failed_count == TOTAL_CHECKPOINTS_COUNT


def test_missing_checkpoints_treated_as_fails():
    """If evaluator returns only 10 checkpoints instead of 18, missing 8 must fail safe."""
    checkpoints = []
    for cp in RUBRIC_CHECKPOINTS[:10]:
        checkpoints.append({
            "id": cp.id,
            "dimension": cp.dimension,
            "name": cp.name,
            "status": "PASS",
            "evidence": "Good",
            "reason": "Passed",
            "suggestion": None
        })

    raw_json = {
        "overall_status": "PASS",
        "passed_count": 10,
        "failed_count": 0,
        "checkpoints": checkpoints
    }

    report = validate_evaluation_report(raw_json)
    assert report.overall_status == "FAIL"
    assert report.passed_count == 10
    assert report.failed_count == 8
    assert len(report.checkpoints) == 18


def test_deterministic_lesson_checks():
    """Verify deterministic check catches missing mandatory sections."""
    partial_lesson = "## 1. Lesson Title\nIntro to RAG\n## 2. Learning Objectives\nLearn RAG\n"
    checks = perform_deterministic_lesson_checks(partial_lesson)
    assert "Lesson Title" in checks["present_sections"]
    assert "Learning Objectives" in checks["present_sections"]
    assert "Prerequisites" in checks["missing_sections"]
    assert len(checks["missing_sections"]) > 0
