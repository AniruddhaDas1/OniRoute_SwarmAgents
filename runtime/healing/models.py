"""Self-Healing Data Contracts (Phase P5.E3)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class RepairAction(BaseModel):
    """Immutable record defining a single repair action in a RepairPlan."""

    model_config = ConfigDict(frozen=True)

    action_id: str = Field(..., description="Unique repair action identifier (act-xxxxxx)")
    finding_id: str = Field(..., description="Associated QualityFinding identifier")
    target_path: str = Field(..., description="Target file or directory path to repair")
    priority: str = Field(..., description="Priority level (P0_CRITICAL, P1_HIGH, P2_MEDIUM, P3_LOW)")
    required_changes: str = Field(..., description="Detailed code regeneration instructions")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite repair action IDs")
    execution_order: int = Field(..., description="Order of repair execution")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Criteria to verify resolution")


class RepairPlan(BaseModel):
    """Immutable Repair Plan contract produced by RepairPlanner."""

    model_config = ConfigDict(frozen=True)

    plan_id: str = Field(..., description="Unique repair plan identifier (rprplan-xxxxxx)")
    quality_report_id: str = Field(..., description="Associated QualityReport identifier")
    engineering_result_id: str = Field(..., description="Associated EngineeringResult identifier")
    actions: List[RepairAction] = Field(default_factory=list, description="List of deterministic repair actions")
    target_files: List[str] = Field(default_factory=list, description="List of target relative file paths affected by plan")
    timestamp: str = Field(..., description="ISO-8601 UTC creation timestamp")
    plan_hash: str = Field(..., description="SHA-256 hash of repair plan payload")


class UpdatedEngineeringResult(BaseModel):
    """Immutable Updated Engineering Result contract produced by SelfHealingEngine."""

    model_config = ConfigDict(frozen=True)

    updated_result_id: str = Field(..., description="Unique updated result identifier (updres-xxxxxx)")
    original_result_id: str = Field(..., description="Original EngineeringResult identifier")
    repair_plan_id: str = Field(..., description="Associated RepairPlan identifier")
    applied_repairs: List[str] = Field(default_factory=list, description="List of applied repair action IDs")
    modified_files: List[str] = Field(default_factory=list, description="List of modified relative file paths")
    created_files: List[str] = Field(default_factory=list, description="List of created relative file paths")
    resolved_findings: List[str] = Field(default_factory=list, description="List of resolved QualityFinding IDs")
    remaining_findings: List[str] = Field(default_factory=list, description="List of remaining unresolved QualityFinding IDs")
    artifacts: List[str] = Field(default_factory=list, description="Consolidated list of target artifact paths")
    execution_time_ms: float = Field(..., description="Self-healing duration in milliseconds")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Incremental token usage")
    cost_usd: float = Field(default=0.0, description="Incremental cost in USD")
    trace_references: List[str] = Field(default_factory=list, description="Trace IDs recorded during repair execution")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence and safety audit log")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    updated_result_hash: str = Field(..., description="SHA-256 hash of updated result payload")
