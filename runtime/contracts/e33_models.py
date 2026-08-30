"""E3.3 Artifact Execution Orchestration Models.

Phase E3.3 — Artifact Execution Orchestration.

Provides immutable models for dependency-aware multi-artifact execution
orchestration using existing E2 ArtifactExecutionPlan and E3.1
RealCodeGenerationEngine.

Architecture:
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionScheduler
        ↓
    DependencyResolver
        ↓
    WaveExecutor
        ↓
    RealCodeGenerationEngine
        ↓
    ExecutionReport
        ↓
    REAL MULTI-FILE PROJECT

Self-contained: depends only on Python stdlib + pydantic.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from runtime.contracts.e23_models import (
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactExecutionWave,
    ArtifactDependencyEdge,
    GenerationStrategy,
)


# ---------------------------------------------------------------------------
# E3.3 - Exception classes
# ---------------------------------------------------------------------------

class OrchestrationError(Exception):
    """Base exception for orchestration failures."""
    pass


class DependencyCycleError(OrchestrationError):
    """Raised when a dependency cycle is detected."""
    pass


class ExecutionError(OrchestrationError):
    """Raised when execution fails."""
    pass


class BlockedArtifactError(OrchestrationError):
    """Raised when an artifact is blocked by dependencies."""
    pass


# ---------------------------------------------------------------------------
# E3.3.3 - Execution State
# ---------------------------------------------------------------------------

class ExecutionState(str, Enum):
    """Observable lifecycle state for artifact execution.

    Reuses the spirit of E1 TaskState for consistency.
    """

    QUEUED = "QUEUED"           # Waiting to be scheduled
    READY = "READY"             # All dependencies satisfied, can execute
    RUNNING = "RUNNING"        # Currently executing
    COMPLETED = "COMPLETED"     # Successfully completed
    FAILED = "FAILED"           # Execution failed
    BLOCKED = "BLOCKED"         # Waiting for dependencies
    SKIPPED = "SKIPPED"         # Skipped (e.g., overwrite policy)
    CANCELLED = "CANCELLED"     # Cancelled by user


class ExecutionStateTransition(BaseModel):
    """Immutable record of a state transition."""

    model_config = ConfigDict(frozen=True)

    artifact_execution_id: str = Field(
        description="Artifact execution unit ID"
    )
    from_state: Optional[ExecutionState] = Field(
        default=None,
        description="Previous state (None if initial)"
    )
    to_state: ExecutionState = Field(
        description="New state"
    )
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp"
    )
    reason: str = Field(
        default="",
        description="Reason for transition"
    )


# ---------------------------------------------------------------------------
# E3.3.1 - Artifact Execution Status
# ---------------------------------------------------------------------------

class ArtifactExecutionStatus(BaseModel):
    """Immutable status for a single artifact execution unit."""

    model_config = ConfigDict(frozen=False)  # Allow state transitions during execution

    # Identity
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    artifact_id: str = Field(
        description="Associated artifact ID"
    )
    target_path: str = Field(
        description="Target file path"
    )

    # State
    state: ExecutionState = Field(
        description="Current execution state"
    )
    state_history: Tuple[ExecutionStateTransition, ...] = Field(
        default_factory=tuple,
        description="State transition history"
    )

    # Execution
    generation_strategy: GenerationStrategy = Field(
        description="Generation strategy"
    )
    execution_wave: int = Field(
        description="Wave number"
    )
    dependencies: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact execution IDs this depends on"
    )
    dependents: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact execution IDs that depend on this"
    )

    # Result
    success: bool = Field(
        default=False,
        description="True if execution succeeded"
    )
    content: Optional[str] = Field(
        default=None,
        description="Generated content if successful"
    )
    file_written: bool = Field(
        default=False,
        description="True if file was written to disk"
    )
    written_path: str = Field(
        default="",
        description="Actual path where file was written"
    )
    content_hash: str = Field(
        default="",
        description="SHA-256 hash of generated content"
    )
    strategy: GenerationStrategy = Field(
        default=GenerationStrategy.LLM_GENERATED,
        description="Generation strategy used"
    )

    # Errors
    errors: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Error messages"
    )
    warnings: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Warning messages"
    )

    # Timing
    queued_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp when queued"
    )
    started_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp when execution started"
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp when completed"
    )
    duration_ms: float = Field(
        default=0.0,
        description="Execution duration in milliseconds"
    )

    # Determinism
    deterministic_hash: str = Field(
        default="",
        description="SHA-256 hash for determinism verification"
    )


# ---------------------------------------------------------------------------
# E3.3.2 - Wave Execution Status
# ---------------------------------------------------------------------------

class WaveExecutionStatus(BaseModel):
    """Immutable status for a single execution wave."""

    model_config = ConfigDict(frozen=False)  # Allow updates during execution

    wave_number: int = Field(
        description="Wave number"
    )
    wave_name: str = Field(
        description="Wave name"
    )
    total_units: int = Field(
        description="Total units in this wave"
    )
    ready_units: int = Field(
        description="Units ready to execute"
    )
    running_units: int = Field(
        description="Units currently executing"
    )
    completed_units: int = Field(
        description="Units successfully completed"
    )
    failed_units: int = Field(
        description="Units that failed"
    )
    blocked_units: int = Field(
        description="Units still blocked"
    )
    skipped_units: int = Field(
        description="Units skipped"
    )
    files_written: int = Field(
        default=0,
        description="Files written by this wave"
    )
    duration_ms: float = Field(
        default=0.0,
        description="Wave execution duration in milliseconds"
    )
    started_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp when wave started"
    )
    completed_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp when wave completed"
    )


# ---------------------------------------------------------------------------
# E3.3.6 - Dependency Cycle Evidence
# ---------------------------------------------------------------------------

class CycleDetectionResult(BaseModel):
    """Immutable evidence of a dependency cycle."""

    model_config = ConfigDict(frozen=True)

    cycle_detected: bool = Field(
        description="True if cycle was detected"
    )
    cycle_path: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Path of artifact IDs forming the cycle"
    )
    involved_edges: Tuple[ArtifactDependencyEdge, ...] = Field(
        default_factory=tuple,
        description="Edges involved in the cycle"
    )
    message: str = Field(
        default="",
        description="Human-readable cycle description"
    )


# ---------------------------------------------------------------------------
# E3.3.7 - Partial Project Report
# ---------------------------------------------------------------------------

class DependencyFailureInfo(BaseModel):
    """Information about a failed dependency."""

    model_config = ConfigDict(frozen=True)

    failed_artifact_execution_id: str = Field(
        description="Failed artifact execution ID"
    )
    affected_artifact_execution_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifacts that were blocked by this failure"
    )
    reason: str = Field(
        description="Why the dependency failed"
    )


class ExecutionReport(BaseModel):
    """Immutable final execution report.

    Provides complete visibility into multi-artifact execution including
    partial success scenarios.
    """

    model_config = ConfigDict(frozen=False)  # Allow hash update after creation

    # Identity
    report_id: str = Field(
        description="Unique report identifier"
    )
    plan_id: str = Field(
        description="Source ArtifactExecutionPlan ID"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )

    # Summary
    total_artifacts: int = Field(
        description="Total artifacts in plan"
    )
    successful_artifacts: int = Field(
        description="Artifacts successfully generated"
    )
    failed_artifacts: int = Field(
        description="Artifacts that failed"
    )
    blocked_artifacts: int = Field(
        description="Artifacts blocked by failures"
    )
    skipped_artifacts: int = Field(
        description="Artifacts skipped"
    )

    # Files
    total_files_written: int = Field(
        description="Total files written to disk"
    )

    # Execution
    total_waves: int = Field(
        description="Total execution waves"
    )
    waves_executed: int = Field(
        description="Waves that were executed"
    )
    wave_results: Tuple[WaveExecutionStatus, ...] = Field(
        default_factory=tuple,
        description="Per-wave execution results"
    )

    # Detailed results
    artifact_results: Tuple[ArtifactExecutionStatus, ...] = Field(
        default_factory=tuple,
        description="Per-artifact execution results"
    )

    # Dependencies
    dependency_failures: Tuple[DependencyFailureInfo, ...] = Field(
        default_factory=tuple,
        description="Failed dependencies and affected artifacts"
    )

    # Errors
    errors: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Execution errors"
    )

    # Cycle detection
    cycle_result: CycleDetectionResult = Field(
        description="Cycle detection result"
    )

    # Timing
    execution_started: str = Field(
        description="ISO-8601 UTC timestamp when execution started"
    )
    execution_completed: str = Field(
        description="ISO-8601 UTC timestamp when execution completed"
    )
    total_duration_ms: float = Field(
        description="Total execution duration in milliseconds"
    )

    # Status
    is_complete: bool = Field(
        description="True if execution is complete"
    )
    is_success: bool = Field(
        description="True if all artifacts succeeded"
    )
    is_partial_success: bool = Field(
        description="True if some artifacts succeeded"
    )
    is_cancelled: bool = Field(
        default=False,
        description="True if execution was cancelled"
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="True if execution is deterministic"
    )
    deterministic_hash: str = Field(
        default="",
        description="SHA-256 hash for determinism verification"
    )


# ---------------------------------------------------------------------------
# E3.3.8 - Progress Tracking
# ---------------------------------------------------------------------------

class ExecutionProgress(BaseModel):
    """Observable progress for execution monitoring."""

    model_config = ConfigDict(frozen=True)

    # Wave progress
    current_wave: int = Field(
        description="Current wave number (0 if not started)"
    )
    total_waves: int = Field(
        description="Total waves"
    )

    # Artifact progress
    current_artifact: Optional[str] = Field(
        default=None,
        description="Current artifact execution ID"
    )
    completed_artifacts: int = Field(
        description="Artifacts completed"
    )
    active_artifacts: int = Field(
        description="Artifacts currently executing"
    )
    total_artifacts: int = Field(
        description="Total artifacts"
    )

    # Status counts
    successful_artifacts: int = Field(
        description="Successfully completed"
    )
    failed_artifacts: int = Field(
        description="Failed artifacts"
    )
    blocked_artifacts: int = Field(
        description="Blocked artifacts"
    )

    # Files
    files_written: int = Field(
        description="Files written to disk"
    )

    # Timing
    elapsed_ms: float = Field(
        description="Elapsed time in milliseconds"
    )
    started_at: Optional[str] = Field(
        default=None,
        description="ISO-8601 UTC timestamp when started"
    )

    # Progress percentage
    progress_percent: float = Field(
        description="Overall progress (0.0 to 100.0)"
    )


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------

def compute_execution_hash(
    artifact_execution_id: str,
    state: ExecutionState,
    content_hash: str,
) -> str:
    """Compute deterministic SHA-256 hash for execution result."""
    payload = f"{artifact_execution_id}:{state.value}:{content_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_report_hash(report: ExecutionReport) -> str:
    """Compute deterministic SHA-256 hash for execution report."""
    hash_payload = {
        "report_id": report.report_id,
        "plan_id": report.plan_id,
        "total_artifacts": report.total_artifacts,
        "successful_artifacts": report.successful_artifacts,
        "failed_artifacts": report.failed_artifacts,
        "total_files_written": report.total_files_written,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
