"""Validation utilities for evaluating lessons and parsing LLM evaluation reports."""
import json
import re
import logging
from typing import Dict, Any, Tuple, Optional
from src.evaluation.schemas import EvaluationReport, CheckpointResult
from src.evaluation.rubric import RUBRIC_CHECKPOINTS, RUBRIC_MAP, TOTAL_CHECKPOINTS_COUNT

logger = logging.getLogger(__name__)

# Mandatory section titles required in the lesson
MANDATORY_SECTIONS = [
    "Lesson Title",
    "Learning Objectives",
    "Prerequisites",
    "Introduction",
    "What Is This Concept?",
    "Why Is It Important?",
    "How Does It Work?",
    "Step-by-Step Explanation",
    "Real-World Example",
    "Technical Example or Simple Analogy",
    "Key Components",
    "Practical Applications",
    "Common Misconceptions",
    "Summary",
    "Key Terms Explained",
    "Knowledge Check / Quiz",
    "Answers to the Quiz"
]


def validate_evaluation_report(raw_data: Any) -> EvaluationReport:
    """
    Validate, sanitize, and strictly enforce hard-gate constraints on an evaluation report.
    Returns a verified EvaluationReport.
    Raises ValueError if raw_data is irrevocably malformed.
    """
    if isinstance(raw_data, str):
        # Extract JSON if wrapped in markdown code blocks
        clean_str = raw_data.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_str)
        if match:
            clean_str = match.group(1).strip()
        try:
            parsed = json.loads(clean_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON string: {e}")
            raise ValueError(f"Malformed evaluation report: invalid JSON: {e}")
    elif isinstance(raw_data, dict):
        parsed = raw_data
    else:
        raise ValueError(f"Expected dict or JSON str, got {type(raw_data)}")

    raw_checkpoints = parsed.get("checkpoints", [])
    if not isinstance(raw_checkpoints, list):
        raise ValueError("Field 'checkpoints' must be a list.")

    # Index provided checkpoints by id
    provided_map: Dict[str, Dict[str, Any]] = {}
    for item in raw_checkpoints:
        if isinstance(item, dict) and "id" in item:
            provided_map[item["id"]] = item

    validated_checkpoints: list[CheckpointResult] = []

    # Ensure all 18 checkpoints from rubric are accounted for
    for cp_def in RUBRIC_CHECKPOINTS:
        if cp_def.id in provided_map:
            raw_cp = provided_map[cp_def.id]
            status = str(raw_cp.get("status", "FAIL")).upper().strip()
            if status not in ("PASS", "FAIL"):
                status = "FAIL"
            
            evidence = str(raw_cp.get("evidence", "")).strip() or "No evidence cited."
            reason = str(raw_cp.get("reason", "")).strip() or "No explanation provided."
            suggestion = raw_cp.get("suggestion")
            if suggestion:
                suggestion = str(suggestion).strip()
            elif status == "FAIL":
                suggestion = f"Address {cp_def.name}: Ensure {cp_def.pass_criteria}"

            validated_checkpoints.append(
                CheckpointResult(
                    id=cp_def.id,
                    dimension=cp_def.dimension,
                    name=cp_def.name,
                    status=status,
                    evidence=evidence,
                    reason=reason,
                    suggestion=suggestion
                )
            )
        else:
            # Checkpoint was omitted by LLM -> strict fail-safe: mark as FAIL
            validated_checkpoints.append(
                CheckpointResult(
                    id=cp_def.id,
                    dimension=cp_def.dimension,
                    name=cp_def.name,
                    status="FAIL",
                    evidence="Checkpoint omitted in evaluation output.",
                    reason="Evaluator did not provide evaluation for this mandatory checkpoint.",
                    suggestion=f"Provide explicit coverage satisfying: {cp_def.pass_criteria}"
                )
            )

    passed_count = sum(1 for cp in validated_checkpoints if cp.status == "PASS")
    failed_count = sum(1 for cp in validated_checkpoints if cp.status == "FAIL")

    # STRICT HARD GATE: Every single checkpoint must pass
    if passed_count == TOTAL_CHECKPOINTS_COUNT and failed_count == 0:
        overall_status = "PASS"
    else:
        overall_status = "FAIL"

    return EvaluationReport(
        overall_status=overall_status,
        passed_count=passed_count,
        failed_count=failed_count,
        checkpoints=validated_checkpoints,
        evaluator_model=parsed.get("evaluator_model"),
        timestamp=parsed.get("timestamp")
    )


def perform_deterministic_lesson_checks(lesson_text: str) -> Dict[str, Any]:
    """
    Perform deterministic programmatic checks on the generated lesson text:
    - Checks for presence of all 17 mandatory sections.
    - Checks word count (should be thorough, not just a brief summary).
    - Checks for core RAG keywords.
    """
    results = {
        "word_count": len(lesson_text.split()),
        "missing_sections": [],
        "present_sections": [],
        "keyword_checks": {}
    }

    lower_text = lesson_text.lower()

    # Section check
    for section in MANDATORY_SECTIONS:
        # Match case-insensitively, e.g. "## 1. Lesson Title" or "1. Lesson Title" or "Lesson Title"
        pattern = re.escape(section.lower())
        if re.search(pattern, lower_text):
            results["present_sections"].append(section)
        else:
            results["missing_sections"].append(section)

    # Core concept keyword presence
    core_terms = ["retrieval", "augmentation", "generation", "chunk", "embedding", "vector", "analogy"]
    for term in core_terms:
        results["keyword_checks"][term] = term in lower_text

    return results
