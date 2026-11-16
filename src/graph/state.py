"""LangGraph State definition for the lesson generation and evaluation workflow."""
from typing import TypedDict, List, Dict, Any, Optional
from src.evaluation.schemas import EvaluationReport


class WorkflowState(TypedDict):
    # Workflow Metadata & Configuration
    run_id: str
    topic: str
    learner_profile: Dict[str, Any]
    max_retries: int
    current_attempt: int  # 1, 2, 3 (Max attempts = max_retries + 1)

    # Retrieval Context
    memory_insights: str
    grounding_excerpts: str

    # Active & Historical Content
    current_lesson: str
    previous_lessons: List[Dict[str, Any]]  # [{attempt, content, word_count}]

    # Evaluation Artifacts
    evaluation_result: Optional[Dict[str, Any]]  # Serialized EvaluationReport
    failed_checkpoints: List[Dict[str, Any]]
    feedback_for_regeneration: str
    rejection_history: List[Dict[str, Any]]

    # Final Outcome
    final_status: str  # "IN_PROGRESS", "APPROVED", "NEEDS_HUMAN_REVIEW", "FAILED_INPUT"
    final_lesson: Optional[str]
    execution_logs: List[str]
