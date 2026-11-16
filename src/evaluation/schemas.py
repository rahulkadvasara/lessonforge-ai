"""Evaluation data schemas and Pydantic models."""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class CheckpointDefinition(BaseModel):
    id: str
    dimension: str
    name: str
    description: str
    pass_criteria: str
    fail_criteria: str


class CheckpointResult(BaseModel):
    id: str
    dimension: str
    name: str
    status: Literal["PASS", "FAIL"]
    evidence: str = Field(..., description="Citations or textual evidence from the lesson")
    reason: str = Field(..., description="Explanation of why this checkpoint passed or failed")
    suggestion: Optional[str] = Field(None, description="Specific improvement recommendation if failed")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("PASS", "FAIL"):
            raise ValueError(f"Invalid status '{v}'. Must be 'PASS' or 'FAIL'.")
        return v


class EvaluationReport(BaseModel):
    overall_status: Literal["PASS", "FAIL"]
    passed_count: int = Field(..., ge=0, le=18)
    failed_count: int = Field(..., ge=0, le=18)
    checkpoints: List[CheckpointResult]
    evaluator_model: Optional[str] = None
    timestamp: Optional[str] = None

    @field_validator("overall_status")
    @classmethod
    def validate_overall_status(cls, v: str, info) -> str:
        # Strict hard gate rule: if any checkpoint fails, overall_status must be FAIL
        checkpoints = info.data.get("checkpoints", [])
        if checkpoints:
            any_fail = any(cp.status == "FAIL" for cp in checkpoints)
            if any_fail and v == "PASS":
                raise ValueError("Strict Hard Gate Violation: Cannot mark overall_status as PASS when any checkpoint failed.")
        return v


class RejectionReport(BaseModel):
    attempt: int
    failed_checkpoint_ids: List[str]
    failure_reasons: List[str]
    actionable_suggestions: List[str]
    raw_feedback: str
