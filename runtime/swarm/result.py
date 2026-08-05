"""Immutable Swarm Execution Result models for Phase P3.A3."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field

from runtime.agent.models import ArtifactRecord, ExecutionStatus


class SwarmExecutionResult(BaseModel):
    """Immutable execution result produced upon completion of an autonomous swarm task."""

    model_config = ConfigDict(frozen=True)

    task_id: str = Field(..., description="Associated ExecutionTask ID")
    session_id: str = Field(..., description="Associated AgentSession ID")
    profile_id: str = Field(..., description="Associated AgentProfile ID")
    wave_number: int = Field(..., ge=1, le=6, description="Wave number (1-6)")
    execution_status: ExecutionStatus = Field(..., description="Final task execution status (DONE, ERROR, SKIPPED, ABORTED)")
    produced_artifacts: List[ArtifactRecord] = Field(default_factory=list, description="Artifact records produced during task execution")
    consumed_tokens: int = Field(default=0, ge=0, description="Total tokens consumed (prompt + completion)")
    execution_time_seconds: float = Field(default=0.0, ge=0.0, description="Execution elapsed time in seconds")
    provider_used: str = Field(default="ollama", description="LLM/AI Provider used (e.g. ollama, openai-compatible)")
    model_used: str = Field(default="llama3", description="LLM model used")
    cost_usd: float = Field(default=0.0, ge=0.0, description="Execution cost in USD")
    trace_references: List[str] = Field(default_factory=list, description="File paths to execution traces")
    log_references: List[str] = Field(default_factory=list, description="File paths to execution logs")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Execution evidence and audit metadata")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
