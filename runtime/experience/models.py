"""Data Contracts for Execution Experience (Phase P6.D2)."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


StreamEventType = Literal[
    "MISSION_STARTED",
    "AGENT_STARTED",
    "AGENT_FINISHED",
    "REVIEW_STARTED",
    "REVIEW_FINISHED",
    "HEALING_STARTED",
    "HEALING_FINISHED",
    "VERIFICATION_STARTED",
    "ACCEPTANCE_COMPLETED",
    "MISSION_COMPLETED",
    "MISSION_FAILED",
    "CANCELLED",
    "STREAM_STARTED",
    "STREAM_CHUNK",
    "STREAM_PROGRESS",
    "STREAM_COMPLETED",
    "STREAM_FAILED",
]


class StreamEvent(BaseModel):
    """Immutable Stream Event contract for presentation-agnostic event distribution."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="Unique event ID (evt-xxxxxx)")
    event_type: StreamEventType = Field(..., description="Type of execution event")
    mission_id: str = Field(..., description="Associated mission identifier")
    session_id: Optional[str] = Field(None, description="Associated session identifier")
    stage_name: str = Field(default="ENGINEERING", description="Current execution stage name")
    agent_id: str = Field(default="", description="ID of current active agent profile")
    agent_role: str = Field(default="", description="Role description of active agent profile")
    task_description: str = Field(default="", description="Description of active task")
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Stage/mission completion percentage")
    files_created: List[str] = Field(default_factory=list, description="Files created up to this event")
    files_modified: List[str] = Field(default_factory=list, description="Files modified up to this event")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Accumulated token usage")
    estimated_cost_usd: float = Field(default=0.0, description="Accumulated cost in USD")
    elapsed_time_ms: float = Field(default=0.0, description="Elapsed execution time in milliseconds")
    estimated_remaining_ms: float = Field(default=0.0, description="Estimated remaining execution time in milliseconds")
    quality_score: float = Field(default=10.0, description="Current quality score (0.0 to 10.0)")
    production_ready: bool = Field(default=False, description="True if project is verified production-ready")
    message: str = Field(default="", description="User-facing status line message")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload dictionary")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")


class SessionStatusReport(BaseModel):
    """Immutable Session Status Report contract for oniroute status CLI command."""

    model_config = ConfigDict(frozen=True)

    session_id: str = Field(..., description="Target session identifier")
    mission_id: str = Field(..., description="Associated mission identifier")
    workspace_root: str = Field(..., description="Target workspace path")
    status: str = Field(..., description="Session state (RUNNING, COMPLETED, FAILED, CANCELLED, PAUSED)")
    current_stage: str = Field(..., description="Current pipeline stage")
    active_agent: str = Field(..., description="Active agent profile ID or role")
    current_task: str = Field(..., description="Description of active task")
    progress_percentage: float = Field(..., description="Current progress percentage")
    files_created_count: int = Field(..., description="Total count of created files")
    files_modified_count: int = Field(..., description="Total count of modified files")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Total tokens consumed")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")
    elapsed_time_ms: float = Field(..., description="Elapsed execution duration")
    quality_score: float = Field(..., description="Current quality score")
    production_ready: bool = Field(..., description="True if production-ready")
    last_event_timestamp: str = Field(..., description="ISO-8601 timestamp of last recorded event")
