"""Lesson generation agent implementation."""
import logging
from typing import Dict, Any, List
from src.services.llm_service import BaseLLMClient, get_llm_client
from src.services.grounding_service import GroundingService
from src.prompts.generator_prompt import GENERATOR_SYSTEM_PROMPT, build_generator_user_prompt
from src.prompts.regeneration_prompt import REGENERATION_SYSTEM_PROMPT, build_regeneration_user_prompt

logger = logging.getLogger(__name__)


class LessonGeneratorAgent:
    """Agent responsible for crafting beginner-friendly educational lessons."""

    def __init__(self, llm_client: BaseLLMClient | None = None, grounding_service: GroundingService | None = None):
        self.llm = llm_client or get_llm_client()
        self.grounding = grounding_service or GroundingService()

    def generate_initial_lesson(
        self,
        topic: str,
        learner_profile: Dict[str, Any],
        memory_insights: str = ""
    ) -> str:
        """Synthesize initial complete lesson using grounding context and past insights."""
        logger.info(f"Generating initial lesson for topic: {topic}")
        grounding_context = self.grounding.get_grounding_context(topic)
        user_prompt = build_generator_user_prompt(
            topic=topic,
            learner_profile=learner_profile,
            grounding_context=grounding_context,
            memory_insights=memory_insights
        )

        messages = [
            {"role": "system", "content": GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        lesson_text = self.llm.generate(messages, temperature=0.3, max_tokens=4096)
        return lesson_text

    def regenerate_lesson(
        self,
        topic: str,
        learner_profile: Dict[str, Any],
        previous_lesson: str,
        failed_checkpoints: List[Dict[str, Any]],
        attempt_number: int,
        max_retries: int
    ) -> str:
        """Regenerate complete lesson targeted at correcting previous rejection points."""
        logger.info(f"Regenerating lesson (attempt {attempt_number}) based on {len(failed_checkpoints)} failed checkpoints.")
        user_prompt = build_regeneration_user_prompt(
            topic=topic,
            learner_profile=learner_profile,
            previous_lesson=previous_lesson,
            failed_checkpoints=failed_checkpoints,
            attempt_number=attempt_number,
            max_retries=max_retries
        )

        messages = [
            {"role": "system", "content": REGENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        revised_lesson = self.llm.generate(messages, temperature=0.2, max_tokens=4096)
        return revised_lesson
