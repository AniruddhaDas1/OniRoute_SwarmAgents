"""E3.4 Repository & Workspace Integration Models.

Phase E3.4 — Repository & Workspace Integration.

Provides integration models that connect mission requirements to
ArtifactExecutionPlan and orchestrate end-to-end execution through
the existing E3.1/E3.3 runtime layers to produce real project files.

Architecture:
    MissionRequest
        ↓
    MissionRequirements
        ↓
    MissionExecutionContext
        ↓
    ArtifactExecutionPlan (from E2.3)
        ↓
    ArtifactExecutionOrchestrator (from E3.3)
        ↓
    RealCodeGenerationEngine (from E3.1)
        ↓
    RepositoryWriter (from E3.1)
        ↓
    ProjectExecutionResult
        ↓
    REAL PROJECT FILES

Self-contained: depends only on Python stdlib + pydantic + existing E2/E3 models.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# E3.4.1 - Mission Requirements
# ---------------------------------------------------------------------------

class ProjectType(str, Enum):
    """Known project type categories."""

    WEB_APPLICATION = "WEB_APPLICATION"
    API_SERVICE = "API_SERVICE"
    FULLSTACK_APPLICATION = "FULLSTACK_APPLICATION"
    MOBILE_APPLICATION = "MOBILE_APPLICATION"
    DESKTOP_APPLICATION = "DESKTOP_APPLICATION"
    LIBRARY_PACKAGE = "LIBRARY_PACKAGE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    DATA_PIPELINE = "DATA_PIPELINE"
    DOCUMENTATION = "DOCUMENTATION"
    UNKNOWN = "UNKNOWN"


class MissionRequirements(BaseModel):
    """Mission requirements extracted from a natural language mission.

    This is the canonical input that bridges mission intent to the E2
    engineering contract system.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    mission_id: str = Field(
        description="Unique mission identifier"
    )

    # Core requirements
    primary_goal: str = Field(
        description="Primary project goal"
    )
    project_type: ProjectType = Field(
        description="Classified project type"
    )

    # Technology preferences
    technology_stack: List[str] = Field(
        default_factory=list,
        description="Technology stack (languages, frameworks, tools)"
    )
    framework_hint: str = Field(
        default="",
        description="Primary framework hint"
    )
    language_hint: str = Field(
        default="",
        description="Primary language hint"
    )

    # Deliverables
    required_deliverables: List[str] = Field(
        default_factory=list,
        description="Required deliverables"
    )
    required_disciplines: List[str] = Field(
        default_factory=list,
        description="Engineering disciplines required"
    )

    # Constraints
    constraints: List[str] = Field(
        default_factory=list,
        description="Known constraints"
    )
    quality_requirements: List[str] = Field(
        default_factory=list,
        description="Quality requirements"
    )

    # Workspace
    workspace_id: str = Field(
        default="",
        description="Target workspace identifier"
    )
    workspace_root: str = Field(
        default="",
        description="Absolute workspace root path"
    )
    blueprint_id: str = Field(
        default="",
        description="Blueprint identifier"
    )


# ---------------------------------------------------------------------------
# E3.4.3 - Workspace Resolution
# ---------------------------------------------------------------------------

class WorkspaceResolution(BaseModel):
    """Resolved workspace boundaries for artifact generation."""

    model_config = ConfigDict(frozen=True)

    # Identity
    workspace_id: str = Field(
        description="Workspace identifier"
    )
    workspace_root: str = Field(
        description="Absolute workspace root path"
    )
    repository_scope: str = Field(
        description="Primary repository scope"
    )

    # Boundary enforcement
    allowed_scopes: List[str] = Field(
        default_factory=list,
        description="Allowed repository scopes"
    )
    is_boundary_enforced: bool = Field(
        default=True,
        description="True if workspace boundaries are enforced"
    )

    # Project directories
    required_directories: List[str] = Field(
        default_factory=list,
        description="Directories required by the project"
    )

    # Safety
    path_traversal_prevented: bool = Field(
        default=True,
        description="True if path traversal is prevented"
    )
    absolute_paths_allowed: bool = Field(
        default=False,
        description="True if absolute paths are allowed (they should not be)"
    )


# ---------------------------------------------------------------------------
# E3.4.8 - Execution Result
# ---------------------------------------------------------------------------

class ArtifactFileResult(BaseModel):
    """Result of writing a single artifact file."""

    model_config = ConfigDict(frozen=True)

    artifact_execution_id: str = Field(
        description="Source artifact execution unit ID"
    )
    target_path: str = Field(
        description="Repository-relative target path"
    )
    absolute_path: str = Field(
        description="Absolute filesystem path"
    )
    file_written: bool = Field(
        description="True if file was written to disk"
    )
    content_hash: str = Field(
        default="",
        description="SHA-256 hash of written content"
    )
    file_size_bytes: int = Field(
        default=0,
        description="File size in bytes"
    )
    error: str = Field(
        default="",
        description="Error message if write failed"
    )


class ProjectExecutionResult(BaseModel):
    """Complete result of a project execution run.

    This is the canonical output that surfaces everything from the
    mission → files execution path.
    """

    model_config = ConfigDict(frozen=False)  # Allow hash update after creation

    # Identity
    execution_id: str = Field(
        description="Unique execution identifier"
    )
    mission_id: str = Field(
        description="Source mission identifier"
    )
    plan_id: str = Field(
        description="Source ArtifactExecutionPlan ID"
    )
    workspace_id: str = Field(
        description="Target workspace identifier"
    )

    # Status
    execution_status: str = Field(
        default="PENDING",
        description="Overall execution status"
    )
    is_success: bool = Field(
        default=False,
        description="True if all artifacts succeeded"
    )
    is_partial_success: bool = Field(
        default=False,
        description="True if some artifacts succeeded"
    )

    # Counts
    total_artifacts: int = Field(
        default=0,
        description="Total artifacts in plan"
    )
    artifacts_completed: int = Field(
        default=0,
        description="Artifacts successfully generated"
    )
    artifacts_failed: int = Field(
        default=0,
        description="Artifacts that failed"
    )
    artifacts_blocked: int = Field(
        default=0,
        description="Artifacts blocked by failures"
    )

    # Files
    files_written: int = Field(
        default=0,
        description="Files written to disk"
    )
    file_results: List[ArtifactFileResult] = Field(
        default_factory=list,
        description="Per-artifact file results"
    )

    # Execution details
    total_waves: int = Field(
        default=0,
        description="Total execution waves"
    )
    waves_executed: int = Field(
        default=0,
        description="Waves actually executed"
    )

    # Timing
    execution_started: str = Field(
        default="",
        description="ISO-8601 UTC timestamp when execution started"
    )
    execution_completed: str = Field(
        default="",
        description="ISO-8601 UTC timestamp when execution completed"
    )
    total_duration_ms: float = Field(
        default=0.0,
        description="Total execution duration in milliseconds"
    )

    # Error summary
    errors: List[str] = Field(
        default_factory=list,
        description="All execution errors"
    )
    failure_evidence: List[str] = Field(
        default_factory=list,
        description="Evidence of failures for debugging"
    )

    # Workspace info
    workspace_root: str = Field(
        default="",
        description="Absolute workspace root path"
    )
    repository_scope: str = Field(
        default="",
        description="Primary repository scope"
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
# E3.4.5 - Project Initialization
# ---------------------------------------------------------------------------

class ProjectInitializer:
    """Minimal project/workspace initialization for artifact generation.

    Creates only directories that are required by the ArtifactExecutionPlan.
    Does NOT generate arbitrary scaffolding.
    """

    @staticmethod
    def get_required_directories(workspace_root: str, plan: Any) -> List[str]:
        """Extract required directories from an ArtifactExecutionPlan.

        Args:
            workspace_root: Absolute workspace root path
            plan: ArtifactExecutionPlan

        Returns:
            List of directory paths (relative to workspace root)
        """
        directories = set()

        for unit in plan.execution_units:
            path = PurePosixPath(unit.target_path)
            if len(path.parts) > 1:
                # Add parent directories
                for i in range(1, len(path.parts)):
                    directories.add(str(PurePosixPath(*path.parts[:i])))

        return sorted(directories)


# ---------------------------------------------------------------------------
# E3.4.10 - Error Handling
# ---------------------------------------------------------------------------

class ExecutionError(Exception):
    """Raised when project execution fails."""
    pass


class InvalidMissionError(ExecutionError):
    """Raised when mission requirements are invalid."""
    pass


class InvalidPlanError(ExecutionError):
    """Raised when the ArtifactExecutionPlan is invalid."""
    pass


class WorkspaceBoundaryError(ExecutionError):
    """Raised when artifact path violates workspace boundaries."""
    pass


class WorkspaceResolutionError(ExecutionError):
    """Raised when workspace cannot be resolved."""
    pass


# ---------------------------------------------------------------------------
# E3.4.11 - Idempotency
# ---------------------------------------------------------------------------

def compute_execution_result_hash(
    execution_id: str,
    mission_id: str,
    plan_id: str,
    files_written: int,
) -> str:
    """Compute deterministic SHA-256 hash for execution result."""
    payload = f"{execution_id}:{mission_id}:{plan_id}:{files_written}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
