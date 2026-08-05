"""Immutable runtime state models for the OniRoute Agent Runtime (ACR-006 Phase R1).

Defines all declarative data models used by the Agent Runtime pipeline.
These are architecture-only specifications. No execution, no AI calls, no scheduling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Runtime Lifecycle States
# ---------------------------------------------------------------------------

class RuntimeState(str, Enum):
    """Canonical lifecycle states for an AgentSession."""

    INITIALIZED = "initialized"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    REVIEW = "review"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Allowed state transitions (deterministic DAG — no backward transitions)
ALLOWED_RUNTIME_TRANSITIONS: dict[RuntimeState, set[RuntimeState]] = {
    RuntimeState.INITIALIZED: {RuntimeState.READY, RuntimeState.CANCELLED},
    RuntimeState.READY:       {RuntimeState.RUNNING, RuntimeState.CANCELLED},
    RuntimeState.RUNNING:     {RuntimeState.WAITING, RuntimeState.REVIEW, RuntimeState.COMPLETED, RuntimeState.FAILED},
    RuntimeState.WAITING:     {RuntimeState.RUNNING, RuntimeState.CANCELLED, RuntimeState.FAILED},
    RuntimeState.REVIEW:      {RuntimeState.RUNNING, RuntimeState.COMPLETED, RuntimeState.FAILED},
    RuntimeState.COMPLETED:   set(),
    RuntimeState.FAILED:      set(),
    RuntimeState.CANCELLED:   set(),
}


def can_runtime_transition(current: RuntimeState, target: RuntimeState) -> bool:
    """Return True if the transition from current to target state is allowed."""
    return target in ALLOWED_RUNTIME_TRANSITIONS.get(current, set())


# ---------------------------------------------------------------------------
# Execution Status
# ---------------------------------------------------------------------------

class ExecutionStatus(str, Enum):
    """High-level execution status emitted on an AgentSession."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    UNDER_REVIEW = "under_review"
    DONE = "done"
    ERROR = "error"
    ABORTED = "aborted"


# ---------------------------------------------------------------------------
# Runtime Metrics
# ---------------------------------------------------------------------------

class RuntimeMetrics(BaseModel):
    """Performance and telemetry metrics for an AgentSession."""

    session_id: str = Field(..., description="Associated session ID")
    start_time: str | None = Field(default=None, description="ISO-8601 UTC session start timestamp")
    end_time: str | None = Field(default=None, description="ISO-8601 UTC session end timestamp")
    duration_seconds: float = Field(default=0.0, description="Total elapsed session duration in seconds")
    artifact_count: int = Field(default=0, description="Total number of artifacts collected")
    event_count: int = Field(default=0, description="Total number of runtime events recorded")
    retry_count: int = Field(default=0, description="Number of session retry attempts")
    memory_bytes_used: int = Field(default=0, description="Peak memory usage in bytes (architecture placeholder)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible metrics metadata")


# ---------------------------------------------------------------------------
# Runtime Events
# ---------------------------------------------------------------------------

class RuntimeEventType(str, Enum):
    """Canonical immutable event types emitted by the Agent Runtime."""

    SESSION_CREATED = "session_created"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_PAUSED = "execution_paused"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    ARTIFACT_PRODUCED = "artifact_produced"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_COMPLETED = "review_completed"
    STATE_TRANSITION = "state_transition"


class ExecutionEvent(BaseModel):
    """Immutable execution event record emitted during agent session lifecycle."""

    event_id: str = Field(..., description="Unique event identifier")
    event_type: RuntimeEventType = Field(..., description="Canonical event type")
    session_id: str = Field(..., description="Source agent session ID")
    member_id: str = Field(..., description="Source organization member ID")
    description: str = Field(default="", description="Human-readable event description")
    event_payload: dict[str, Any] = Field(default_factory=dict, description="Structured event payload data")
    previous_state: RuntimeState | None = Field(default=None, description="State before transition (for state events)")
    next_state: RuntimeState | None = Field(default=None, description="State after transition (for state events)")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC event timestamp",
    )


# ---------------------------------------------------------------------------
# Artifact Management
# ---------------------------------------------------------------------------

class ArtifactType(str, Enum):
    """Categories of runtime artifacts produced by agent sessions."""

    CODE = "code"
    DOCUMENTATION = "documentation"
    TEST_SUITE = "test_suite"
    SCHEMA = "schema"
    CONFIG = "config"
    REPORT = "report"
    REVIEW = "review"
    BINARY = "binary"
    DATA = "data"
    CUSTOM = "custom"


class ArtifactRecord(BaseModel):
    """Immutable artifact record capturing lineage, ownership, and metadata."""

    artifact_id: str = Field(..., description="Unique artifact identifier")
    artifact_type: ArtifactType = Field(..., description="Artifact category")
    owner_session_id: str = Field(..., description="Session ID of the producing agent session")
    owner_member_id: str = Field(..., description="Member ID of the producing organization member")
    capability_id: str = Field(..., description="Capability that produced this artifact")
    name: str = Field(..., description="Human-readable artifact name")
    description: str = Field(default="", description="Artifact description")
    lineage: list[str] = Field(default_factory=list, description="List of parent artifact IDs this artifact depends on")
    references: list[str] = Field(default_factory=list, description="External file path or URI references")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible artifact metadata")
    produced_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC artifact production timestamp",
    )


# ---------------------------------------------------------------------------
# Runtime Context
# ---------------------------------------------------------------------------

class RuntimeContext(BaseModel):
    """Declarative runtime context established at session initialization."""

    context_id: str = Field(..., description="Unique runtime context identifier")
    blueprint_id: str = Field(..., description="Associated ExecutionBlueprint ID")
    mission_id: str = Field(..., description="Associated mission ID")
    organization_id: str = Field(..., description="Associated organization ID")
    workspace_root: str = Field(..., description="Absolute workspace root path string")
    engine_root: str = Field(..., description="Absolute engine root path string")
    active_session_ids: list[str] = Field(default_factory=list, description="List of active AgentSession IDs")
    runtime_constraints: dict[str, Any] = Field(default_factory=dict, description="Execution constraint overrides")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible runtime context metadata")
    initialized_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC context initialization timestamp",
    )


# ---------------------------------------------------------------------------
# Agent Session
# ---------------------------------------------------------------------------

class AgentSession(BaseModel):
    """Canonical declarative agent session representation in the Agent Runtime."""

    session_id: str = Field(..., description="Unique agent session identifier (e.g. sess-mem-backend-01-001)")
    member_id: str = Field(..., description="Bound organization member ID")
    role_id: str = Field(..., description="Bound role ID from Organization")
    role_title: str = Field(..., description="Human-readable role title")
    blueprint_id: str = Field(..., description="Execution Blueprint this session was instantiated from")
    capability_ids: list[str] = Field(default_factory=list, description="Capability IDs this session is responsible for")
    state: RuntimeState = Field(default=RuntimeState.INITIALIZED, description="Current lifecycle state")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="High-level execution status")
    artifacts: list[ArtifactRecord] = Field(default_factory=list, description="Artifacts produced by this session")
    events: list[ExecutionEvent] = Field(default_factory=list, description="Chronological event log")
    metrics: RuntimeMetrics | None = Field(default=None, description="Session performance metrics")
    evidence: list[dict[str, Any]] = Field(default_factory=list, description="Session audit evidence records")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible session metadata")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC session creation timestamp",
    )


# ---------------------------------------------------------------------------
# Execution Result
# ---------------------------------------------------------------------------

class ExecutionResult(BaseModel):
    """Declarative result record produced upon session completion."""

    result_id: str = Field(..., description="Unique execution result identifier")
    session_id: str = Field(..., description="Source session ID")
    member_id: str = Field(..., description="Source member ID")
    status: ExecutionStatus = Field(..., description="Final execution status")
    artifacts_produced: list[str] = Field(default_factory=list, description="IDs of artifacts produced")
    events_recorded: int = Field(default=0, description="Total events recorded in this session")
    summary: str = Field(default="", description="Human-readable result summary")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible result metadata")
    completed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC result completion timestamp",
    )


# ---------------------------------------------------------------------------
# Runtime Report
# ---------------------------------------------------------------------------

class RuntimeReport(BaseModel):
    """Canonical runtime execution report produced upon coordinator completion."""

    report_id: str = Field(..., description="Unique runtime report identifier")
    blueprint_id: str = Field(..., description="Associated Execution Blueprint ID")
    mission_id: str = Field(..., description="Associated mission ID")
    total_sessions: int = Field(default=0, description="Total number of agent sessions instantiated")
    completed_sessions: int = Field(default=0, description="Number of sessions reaching COMPLETED state")
    failed_sessions: int = Field(default=0, description="Number of sessions reaching FAILED state")
    cancelled_sessions: int = Field(default=0, description="Number of sessions reaching CANCELLED state")
    total_artifacts: int = Field(default=0, description="Total artifacts produced across all sessions")
    total_events: int = Field(default=0, description="Total events recorded across all sessions")
    execution_results: list[ExecutionResult] = Field(default_factory=list, description="Ordered execution result records")
    runtime_metrics: list[RuntimeMetrics] = Field(default_factory=list, description="Per-session metrics")
    summary: str = Field(default="", description="Human-readable execution summary")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC report generation timestamp",
    )
