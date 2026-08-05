"""Immutable Mission models for OniRoute Mission Orchestrator (ACR-004 Phase O1).

This module defines declarative Pydantic schemas for the Mission Orchestrator without
introducing runtime execution logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .evidence import MissionEvidence
from .states import MissionState


class MissionRequest(BaseModel):
    """Raw mission intake request from CLI or API."""

    request_id: str = Field(..., description="Unique intake request identifier")
    raw_prompt: str = Field(..., description="Unparsed natural language command from CLI")
    explicit_workspace: Path | None = Field(default=None, description="Optional explicit workspace override path")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Additional CLI options or flag parameters")
    requested_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp when request was submitted",
    )


class MissionRequirements(BaseModel):
    """Parsed mission requirements and target objectives."""

    intent_category: str = Field(default="general", description="Categorized user intent (e.g. create, refactor, fix, review)")
    primary_goal: str = Field(..., description="Normalized primary goal description")
    functional_requirements: list[str] = Field(default_factory=list, description="Extracted functional requirements")
    non_functional_requirements: list[str] = Field(default_factory=list, description="Extracted quality/performance requirements")
    target_artifacts: list[str] = Field(default_factory=list, description="Types of deliverables expected (code, docs, tests)")


class MissionConstraints(BaseModel):
    """Operational constraints, budgets, and security boundaries."""

    max_budget_usd: float | None = Field(default=None, description="Maximum budget limit in USD")
    timeout_seconds: int = Field(default=300, description="Execution timeout limit in seconds")
    allowed_providers: list[str] = Field(default_factory=list, description="Permitted LLM providers")
    local_only: bool = Field(default=False, description="Enforce local-only model execution")
    require_human_approval: bool = Field(default=False, description="Flag requiring explicit human sign-off")


class MissionDeliverables(BaseModel):
    """Expected output artifacts and target file destinations."""

    expected_categories: list[str] = Field(default_factory=list, description="List of expected ArtifactCategory names")
    target_paths: list[Path] = Field(default_factory=list, description="Specified target file paths if provided")
    output_summary: str = Field(default="", description="Summary of deliverables generated upon completion")


class MissionContext(BaseModel):
    """Context reference encapsulating resolved workspace and project metadata."""

    workspace_id: str = Field(..., description="Target workspace identifier")
    workspace_root: Path = Field(..., description="Resolved target workspace root path")
    engine_root: Path = Field(..., description="Resolved read-only engine root path")
    project_type: str = Field(default="unknown", description="Detected project framework type")
    read_only_engine_confirmed: bool = Field(default=True, description="Engine read-only safety assertion status")


class MissionStatus(BaseModel):
    """Lifecycle state machine wrapper tracking current state and progress history."""

    current_state: MissionState = Field(default=MissionState.RECEIVED, description="Current lifecycle state")
    state_history: list[dict[str, Any]] = Field(default_factory=list, description="Chronological record of state transitions")
    current_step: str | None = Field(default=None, description="Active execution step description")
    progress_percentage: float = Field(default=0.0, description="Estimated completion progress (0.0 to 100.0)")
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when mission was received",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp of last state update",
    )
    completed_at: str | None = Field(default=None, description="Timestamp when mission reached terminal state")


class MissionResult(BaseModel):
    """Outcome payload generated upon mission termination."""

    outcome: str = Field(..., description="Execution outcome (e.g. COMPLETED, FAILED, CANCELLED)")
    generated_artifacts: list[Path] = Field(default_factory=list, description="List of created artifact paths")
    execution_duration_seconds: float = Field(default=0.0, description="Total execution duration in seconds")
    error_message: str | None = Field(default=None, description="Error message if execution failed")


class MissionReport(BaseModel):
    """Final consolidated mission audit and execution report."""

    mission_id: str = Field(..., description="Associated mission identifier")
    title: str = Field(..., description="Mission display title")
    summary: str = Field(..., description="Executive summary of execution")
    evidence_summary: dict[str, Any] = Field(default_factory=dict, description="Summary of evidence across stages")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Report generation timestamp",
    )


class Mission(BaseModel):
    """Canonical immutable Mission model representing the end-to-end orchestration object."""

    mission_id: str = Field(..., description="Unique canonical mission identifier")
    name: str = Field(..., description="Human-readable mission name")
    request: MissionRequest = Field(..., description="Original intake request")
    requirements: MissionRequirements = Field(..., description="Parsed functional & non-functional requirements")
    constraints: MissionConstraints = Field(..., description="Operational constraints & budget limits")
    deliverables: MissionDeliverables = Field(..., description="Specified output deliverables")
    context: MissionContext = Field(..., description="Resolved workspace & project context")
    evidence: MissionEvidence = Field(default_factory=MissionEvidence, description="Immutable evidence audit log")
    status: MissionStatus = Field(default_factory=MissionStatus, description="Current lifecycle state tracker")
    result: MissionResult | None = Field(default=None, description="Final execution outcome payload")
    report: MissionReport | None = Field(default=None, description="Final consolidated report")
