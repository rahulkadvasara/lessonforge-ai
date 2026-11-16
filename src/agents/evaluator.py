"""Content evaluation agent enforcing the strict 18-checkpoint rubric."""
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any
from src.services.llm_service import BaseLLMClient, get_llm_client
from src.services.grounding_service import GroundingService
from src.evaluation.schemas import EvaluationReport
from src.evaluation.validators import validate_evaluation_report
from src.prompts.evaluator_prompt import EVALUATOR_SYSTEM_PROMPT, build_evaluator_user_prompt
from src.evaluation.rubric import RUBRIC_CHECKPOINTS

logger = logging.getLogger(__name__)


class ContentEvaluatorAgent:
    """Independent auditor evaluating lesson quality against the hard-gate rubric."""

    def __init__(self, llm_client: BaseLLMClient | None = None, grounding_service: GroundingService | None = None):
        self.llm = llm_client or get_llm_client()
        self.grounding = grounding_service or GroundingService()

    def evaluate_lesson(
        self,
        topic: str,
        learner_profile: Dict[str, Any],
        lesson_text: str
    ) -> EvaluationReport:
        """
        Audit lesson text against all 18 binary checkpoints.
        Never falsely approves on parsing error; strictly validates schema.
        """
        logger.info(f"Auditing lesson for topic '{topic}' ({len(lesson_text.split())} words)")
        grounding_context = self.grounding.get_grounding_context(topic)
        user_prompt = build_evaluator_user_prompt(
            topic=topic,
            learner_profile=learner_profile,
            lesson_text=lesson_text,
            grounding_context=grounding_context
        )

        messages = [
            {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        try:
            # Request JSON output
            raw_response = self.llm.generate(
                messages,
                temperature=0.0,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            report = validate_evaluation_report(raw_response)
            report.evaluator_model = self.llm.get_model_name()
            report.timestamp = datetime.now(timezone.utc).isoformat()
            return report

        except Exception as e:
            logger.error(f"Evaluator error or malformed schema: {e}. Executing safe hard-gate rejection.")
            # Fail-safe: Create an explicit failing report indicating schema failure
            failing_checkpoints = []
            for cp in RUBRIC_CHECKPOINTS:
                failing_checkpoints.append({
                    "id": cp.id,
                    "dimension": cp.dimension,
                    "name": cp.name,
                    "status": "FAIL",
                    "evidence": "N/A - Parsing or validation error during evaluation call.",
                    "reason": f"Evaluation parsing/schema failure: {str(e)}",
                    "suggestion": "Re-run evaluation with valid JSON schema output."
                })
            
            return EvaluationReport(
                overall_status="FAIL",
                passed_count=0,
                failed_count=len(RUBRIC_CHECKPOINTS),
                checkpoints=failing_checkpoints,
                evaluator_model=self.llm.get_model_name(),
                timestamp=datetime.now(timezone.utc).isoformat()
            )
