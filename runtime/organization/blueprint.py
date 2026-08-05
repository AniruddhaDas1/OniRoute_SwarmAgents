"""Immutable Execution Blueprint model for OniRoute Organization Builder (ACR-005 Phase S1).

Defines the final declarative specification produced by the Organization Builder pipeline
prior to agent runtime handoff. Contains zero execution steps or AI invocations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from runtime.mission.models import Mission

from .capability import CapabilityReport
from .models import Organization
from .swarm_graph import SwarmGraph


class ExecutionReadiness(BaseModel):
    """Declarative readiness check status for the execution blueprint."""

    is_ready: bool = Field(default=True, description="Overall blueprint readiness indicator")
    missing_capabilities: list[str] = Field(default_factory=list, description="List of unfulfilled capability IDs if any")
    unresolved_dependencies: list[str] = Field(default_factory=list, description="List of broken dependency IDs if any")
    validation_checks: dict[str, bool] = Field(
        default_factory=dict, description="Map of named validation checks to pass/fail status"
    )
    checked_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of readiness check",
    )


class ExecutionBlueprint(BaseModel):
    """Canonical immutable Execution Blueprint produced by Organization Builder."""

    blueprint_id: str = Field(..., description="Unique execution blueprint identifier (e.g. blp-msn-1001)")
    organization: Organization = Field(..., description="Target validated engineering organization")
    mission: Mission = Field(..., description="Associated validated mission object")
    capabilities: CapabilityReport = Field(..., description="Assessed mission capabilities report")
    dependencies: SwarmGraph = Field(..., description="Swarm graph defining all relationship views")
    readiness: ExecutionReadiness = Field(default_factory=ExecutionReadiness, description="Readiness check assessment")
    execution_metadata: dict[str, Any] = Field(default_factory=dict, description="Execution context metadata snapshot")
    schema_version: str = Field(default="1.0.0", description="Execution Blueprint schema version")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of blueprint creation",
    )
