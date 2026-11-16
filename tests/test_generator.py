"""Unit tests for the Lesson Generator agent."""
import pytest
from src.agents.generator import LessonGeneratorAgent
from src.services.llm_service import MockLLMClient
from src.config.settings import DEFAULT_LEARNER_PROFILE
from src.evaluation.validators import perform_deterministic_lesson_checks


def test_generator_creates_complete_lesson():
    """Verify that generator agent calls LLM and returns structured lesson."""
    mock_llm = MockLLMClient()
    agent = LessonGeneratorAgent(llm_client=mock_llm)

    lesson = agent.generate_initial_lesson("Introduction to RAG", DEFAULT_LEARNER_PROFILE)
    assert lesson is not None
    assert len(lesson) > 100

    # Verify deterministic section presence
    checks = perform_deterministic_lesson_checks(lesson)
    assert "Lesson Title" in checks["present_sections"]
    assert "Real-World Example" in checks["present_sections"]
    assert "Knowledge Check / Quiz" in checks["present_sections"]


def test_regeneration_agent_receives_feedback():
    """Verify regeneration prompt includes failed checkpoint details."""
    mock_llm = MockLLMClient()
    agent = LessonGeneratorAgent(llm_client=mock_llm)

    failed_cps = [
        {
            "id": "CLR_01",
            "dimension": "Clarity and Jargon Management",
            "name": "Immediate Jargon Demystification",
            "reason": "Embeddings were not explained when introduced.",
            "suggestion": "Provide a simple number fingerprint analogy."
        }
    ]

    revised = agent.regenerate_lesson(
        topic="Introduction to RAG",
        learner_profile=DEFAULT_LEARNER_PROFILE,
        previous_lesson="# Old lesson",
        failed_checkpoints=failed_cps,
        attempt_number=2,
        max_retries=2
    )

    # Check mock history that prompt contained the failed checkpoint
    last_call = mock_llm.call_history[-1]
    user_prompt = last_call["messages"][1]["content"]
    assert "CLR_01" in user_prompt
    assert "Embeddings were not explained" in user_prompt
    assert "Provide a simple number fingerprint analogy" in user_prompt
