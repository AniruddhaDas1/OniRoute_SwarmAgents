from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .state import ExecutionStatus


def utcnow() -> datetime: return datetime.now(timezone.utc)


class ExecutionStep(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    id: str
    description: str
    workflow: str
    agent: str | None = None
    skill: str | None = None
    context: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    status: ExecutionStatus = ExecutionStatus.PENDING
    duration_ms: float = 0
    execution_order: int
    result: str | None = None
    ai_trace: dict[str, Any] | None = None


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)
    plan_id: str
    workflow_id: str
    steps: tuple[ExecutionStep, ...]
    created_at: datetime


class GeneratedArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    type: str
    workflow_id: str
    content: dict[str, Any]


class ExecutionResult(BaseModel):
    execution_id: str
    workflow_id: str
    status: ExecutionStatus
    plan: ExecutionPlan
    artifacts: tuple[GeneratedArtifact, ...]
    started_at: datetime
    completed_at: datetime
    report: dict[str, Any] = Field(default_factory=dict)
    ai_trace: tuple[dict[str, Any], ...] = ()
