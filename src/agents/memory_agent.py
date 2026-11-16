"""Memory and self-evolution agent coordinating SQLite persistence and pattern learning."""
import logging
from typing import Dict, Any, List
from src.memory.repository import MemoryRepository
from src.memory.learning import SelfEvolutionEngine

logger = logging.getLogger(__name__)


class MemoryAgent:
    """Agent in charge of context retrieval from past runs and continuous self-evolution."""

    def __init__(self, repository: MemoryRepository | None = None, evolution_engine: SelfEvolutionEngine | None = None):
        self.repo = repository or MemoryRepository()
        self.evolution = evolution_engine or SelfEvolutionEngine(self.repo.db)

    def retrieve_context_for_generation(self, topic: str) -> str:
        """Fetch past failure insights and format guidance for the generation prompt."""
        insights_prompt = self.evolution.format_insights_for_prompt()
        return insights_prompt

    def record_run_completion(
        self,
        run_id: str,
        topic: str,
        learner_profile: dict,
        attempts_used: int,
        final_status: str,
        lesson_versions: List[Dict[str, Any]],
        evaluation_history: List[Dict[str, Any]],
        rejection_history: List[Dict[str, Any]]
    ) -> None:
        """Persist all execution artifacts into relational SQLite tables."""
        logger.info(f"Persisting run {run_id} to database. Status: {final_status}, Attempts: {attempts_used}")
        self.repo.update_run_status(run_id, final_status, attempts_used)

        # Trigger self-evolution insight update if any rejections occurred
        if rejection_history:
            self.evolution.analyze_and_update_insights()
