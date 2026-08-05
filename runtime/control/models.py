"""Data Contracts for Mission Control (Phase P6.D3).

Immutable models for mission control commands, inspection results,
session management, and mission lifecycle operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


MissionControlAction = Literal[
    "PAUSE",
    "RESUME",
    "CANCEL",
    "RETRY",
    "APPROVE_REVIEW",
    "REJECT_REVIEW",
    "INSPECT",
]


class MissionControlCommand(BaseModel):
    """Immutable Mission Control command contract."""

    model_config = ConfigDict(frozen=True)

    command_id: str = Field(..., description="Unique command identifier (cmd-xxxxxx)")
    action: MissionControlAction = Field(..., description="Control action to execute")
    mission_id: str = Field(..., description="Target mission identifier")
    session_id: str = Field(default="", description="Target session identifier")
    issued_by: str = Field(default="cli", description="Command issuer (cli, api, vscode)")
    reason: str = Field(default="", description="Optional user-supplied reason for the action")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action-specific payload")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of command issuance")


class MissionControlResult(BaseModel):
    """Immutable result of a Mission Control command execution."""

    model_config = ConfigDict(frozen=True)

    command_id: str = Field(..., description="Originating command identifier")
    action: MissionControlAction = Field(..., description="Executed action")
    mission_id: str = Field(..., description="Target mission identifier")
    success: bool = Field(..., description="True if command executed successfully")
    previous_state: str = Field(default="", description="Mission state before command")
    current_state: str = Field(default="", description="Mission state after command")
    message: str = Field(default="", description="Human-readable result message")
    latency_ms: float = Field(default=0.0, description="Command execution latency in milliseconds")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of result")


class MissionInspection(BaseModel):
    """Immutable Mission Inspection result."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., description="Target mission identifier")
    session_id: str = Field(default="", description="Associated session identifier")
    status: str = Field(..., description="Current mission status")
    current_stage: str = Field(default="", description="Current execution stage")
    current_agent: str = Field(default="", description="Active agent profile ID or role")
    current_contract: str = Field(default="", description="Active engineering contract ID")
    files_created: List[str] = Field(default_factory=list, description="Files created so far")
    files_modified: List[str] = Field(default_factory=list, description="Files modified so far")
    quality_score: float = Field(default=0.0, description="Current quality score")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Total tokens consumed")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost in USD")
    active_mcp_tools: List[str] = Field(default_factory=list, description="Active MCP tool names")
    remaining_contracts: int = Field(default=0, description="Number of remaining engineering contracts")
    progress_percentage: float = Field(default=0.0, description="Overall progress percentage")
    production_ready: bool = Field(default=False, description="True if verified production-ready")
    elapsed_time_ms: float = Field(default=0.0, description="Elapsed execution time in milliseconds")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")


class MissionHistoryEntry(BaseModel):
    """Immutable Mission History entry for search and filtering."""

    model_config = ConfigDict(frozen=True)

    mission_id: str = Field(..., description="Mission identifier")
    session_id: str = Field(default="", description="Session identifier")
    request_text: str = Field(default="", description="Original natural language request")
    status: str = Field(..., description="Final mission status")
    primary_intent: str = Field(default="", description="Detected primary intent")
    quality_score: float = Field(default=0.0, description="Final quality score")
    production_ready: bool = Field(default=False, description="True if certified production-ready")
    files_created_count: int = Field(default=0, description="Total files created")
    files_modified_count: int = Field(default=0, description="Total files modified")
    total_cost_usd: float = Field(default=0.0, description="Total cost in USD")
    elapsed_time_ms: float = Field(default=0.0, description="Total elapsed time")
    workspace_root: str = Field(default="", description="Target workspace path")
    started_at: str = Field(default="", description="ISO-8601 start timestamp")
    completed_at: str = Field(default="", description="ISO-8601 completion timestamp")


class ConcurrentMissionRegistry(BaseModel):
    """Registry tracking all concurrent active missions."""

    model_config = ConfigDict(frozen=True)

    active_missions: List[str] = Field(default_factory=list, description="Active mission IDs")
    paused_missions: List[str] = Field(default_factory=list, description="Paused mission IDs")
    total_active: int = Field(default=0, description="Count of active missions")
    total_paused: int = Field(default=0, description="Count of paused missions")
    total_completed: int = Field(default=0, description="Count of completed missions")
    total_failed: int = Field(default=0, description="Count of failed missions")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
