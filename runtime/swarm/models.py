"""Immutable Runtime Execution Snapshot models for OniRoute (Phase P3.A2).

Defines declarative Pydantic schemas for Swarm Initialization and RuntimeExecutionSnapshot
without introducing LLM invocation, session execution, or artifact generation logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from runtime.agent.models import AgentSession, ExecutionStatus, RuntimeState


class ExecutionCursor(BaseModel):
    """Immutable execution cursor tracking initial swarm position."""

    model_config = ConfigDict(frozen=True)

    active_wave_number: int = Field(default=1, ge=1, le=6, description="Currently active execution wave number (1-6)")
    active_profile_id: Optional[str] = Field(default=None, description="Currently executing profile ID (None prior to execution)")
    active_session_id: Optional[str] = Field(default=None, description="Currently active session ID (None prior to execution)")
    current_step_index: int = Field(default=0, ge=0, description="0-indexed step counter")
    execution_state: str = Field(default="READY", description="High-level execution state (READY, RUNNING, PAUSED, COMPLETED, FAILED)")
    is_paused: bool = Field(default=False, description="True if swarm execution is paused")
    is_completed: bool = Field(default=False, description="True if swarm execution has finished")


class WaveExecutionStatus(BaseModel):
    """Immutable execution status record for an individual wave."""

    model_config = ConfigDict(frozen=True)

    wave_number: int = Field(..., ge=1, le=6, description="Wave stage number (1-6)")
    name: str = Field(..., description="Canonical wave name")
    status: str = Field(default="READY", description="Wave state (READY, PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED)")
    profile_ids: List[str] = Field(default_factory=list, description="All profile IDs assigned to this wave")
    completed_profile_ids: List[str] = Field(default_factory=list, description="Profile IDs that have completed execution")
    failed_profile_ids: List[str] = Field(default_factory=list, description="Profile IDs that failed execution")


class SessionStateRecord(BaseModel):
    """Immutable record tracking initial session binding for an agent profile."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Unique AgentSession identifier")
    profile_id: str = Field(..., description="Associated AgentProfile identifier")
    agent_role: str = Field(..., description="Human-readable agent role title")
    primary_discipline: str = Field(..., description="Primary engineering discipline")
    wave_number: int = Field(..., ge=1, le=6, description="Wave number assigned to this session")
    state: RuntimeState = Field(default=RuntimeState.READY, description="Current session state (READY)")
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="High-level execution status")
    retry_count: int = Field(default=0, ge=0, description="Retries attempted so far")
    max_retries: int = Field(default=3, ge=0, description="Max allowed retries for this session")
    allocated_budget_usd: float = Field(default=0.0, ge=0.0, description="USD budget allocated to this session")


class BudgetStatus(BaseModel):
    """Immutable tracking record for execution budget allocation and spending."""

    model_config = ConfigDict(frozen=True)

    total_budget_usd: float = Field(..., ge=0.0, description="Total allocated budget in USD")
    spent_budget_usd: float = Field(default=0.0, ge=0.0, description="USD spent so far (0.0 at initialization)")
    remaining_budget_usd: float = Field(..., ge=0.0, description="Remaining unspent USD budget")
    wave_budget_allocations: Dict[int, float] = Field(default_factory=dict, description="USD budget allocated per wave number")
    profile_budget_allocations: Dict[str, float] = Field(default_factory=dict, description="USD budget allocated per profile ID")
    currency: str = Field(default="USD", description="Currency symbol")
    is_exhausted: bool = Field(default=False, description="True if budget is fully spent")


class RetryStatus(BaseModel):
    """Immutable tracking record for execution retries and limits."""

    model_config = ConfigDict(frozen=True)

    total_retries_attempted: int = Field(default=0, ge=0, description="Total retries attempted across all sessions")
    profile_retry_counters: Dict[str, int] = Field(default_factory=dict, description="Current retry count per profile_id")
    max_retry_limits: Dict[str, int] = Field(default_factory=dict, description="Max retry limit per profile_id")


class CheckpointStatus(BaseModel):
    """Immutable tracking record for state checkpoints and restore points."""

    model_config = ConfigDict(frozen=True)

    current_checkpoint_id: str = Field(..., description="Active checkpoint identifier (e.g. chk-w1-init-001)")
    checkpoint_count: int = Field(default=1, ge=1, description="Total number of checkpoints created")
    checkpoint_history: List[str] = Field(default_factory=list, description="Ordered list of checkpoint IDs")
    rollback_target_wave: int = Field(default=1, ge=1, le=6, description="Default wave number to revert to on rollback")
    is_restorable: bool = Field(default=True, description="True if checkpoint state is restorable")


class EventBusReferences(BaseModel):
    """Immutable references to initialized event channels."""

    model_config = ConfigDict(frozen=True)

    bus_id: str = Field(..., description="Unique event bus identifier")
    active_channels: List[str] = Field(
        default_factory=lambda: ["execution_events", "state_transitions", "artifact_events", "governance_events", "trace_events", "log_events"],
        description="List of active event channels",
    )
    event_count: int = Field(default=0, ge=0, description="Total events emitted on bus")
    listener_count: int = Field(default=0, ge=0, description="Active event listeners attached")


class StorageReferences(BaseModel):
    """Immutable references to workspace storage directories and handles."""

    model_config = ConfigDict(frozen=True)

    workspace_root: str = Field(..., description="Absolute workspace root path string")
    sessions_root: str = Field(..., description="Absolute sessions directory path (.oniroute/sessions)")
    traces_root: str = Field(..., description="Absolute traces directory path (.oniroute/traces)")
    logs_root: str = Field(..., description="Absolute logs directory path (.oniroute/logs)")
    history_root: str = Field(..., description="Absolute history directory path (.oniroute/history)")
    reports_root: str = Field(..., description="Absolute reports directory path (.oniroute/reports)")
    artifacts_root: str = Field(..., description="Absolute artifacts directory path (.oniroute/artifacts)")


class WorkspaceReferences(BaseModel):
    """Immutable references to workspace context and safety assertions."""

    model_config = ConfigDict(frozen=True)

    workspace_id: str = Field(..., description="Target workspace identifier")
    workspace_root: str = Field(..., description="Absolute workspace root path string")
    engine_root: str = Field(..., description="Absolute engine root path string")
    is_engine_read_only: bool = Field(default=True, description="True if engine root is physically protected from writes")
    project_type: str = Field(default="unknown", description="Detected project technology type")


class RuntimeExecutionSnapshot(BaseModel):
    """Immutable Runtime Execution Snapshot.

    Consolidates MissionDeploymentPlan into a fully initialized, execution-ready
    state snapshot without executing work, calling LLMs, or producing code artifacts.
    """

    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(..., description="Unique snapshot identifier (snap-xxxxxx)")
    mission_id: str = Field(..., description="Associated mission identifier")
    deployment_plan_id: str = Field(..., description="Associated MissionDeploymentPlan identifier")
    execution_uuid: str = Field(..., description="Unique execution UUID (exec-uuid-xxxxxx)")
    wave_status: Dict[int, WaveExecutionStatus] = Field(default_factory=dict, description="Execution status mapped per wave number (1-6)")
    session_map: Dict[str, SessionStateRecord] = Field(default_factory=dict, description="Session state mapping profile_id -> SessionStateRecord")
    sessions: List[AgentSession] = Field(default_factory=list, description="All instantiated AgentSession objects in READY state")
    execution_cursor: ExecutionCursor = Field(..., description="Execution position cursor")
    execution_context: Dict[str, Any] = Field(default_factory=dict, description="Consolidated initial execution context")
    budget_status: BudgetStatus = Field(..., description="Budget tracking status")
    retry_status: RetryStatus = Field(..., description="Retry status tracking")
    checkpoint_status: CheckpointStatus = Field(..., description="Checkpoint status tracking")
    event_bus_references: EventBusReferences = Field(..., description="Event bus channel references")
    storage_references: StorageReferences = Field(..., description="Workspace storage directory references")
    workspace_references: WorkspaceReferences = Field(..., description="Workspace metadata and safety references")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Consolidated initialization evidence and validation results")
    timestamp: str = Field(..., description="ISO-8601 UTC initialization timestamp")
    snapshot_hash: str = Field(..., description="SHA-256 Snapshot Hash")
