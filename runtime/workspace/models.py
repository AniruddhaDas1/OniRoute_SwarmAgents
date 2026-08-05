"""Canonical models for OniRoute Workspace Architecture Foundation (ACR-003 Phase W1).

This module defines provider-independent, declarative data structures for:
- Workspace Metadata
- Project Metadata
- Artifact Routing & Destinations
- Execution Context
- Workspace Discovery Rules
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ProjectType(str, Enum):
    """Supported provider-independent project types."""
    PYTHON = "python"
    NODE = "node"
    REACT = "react"
    NEXTJS = "nextjs"
    VUE = "vue"
    ANGULAR = "angular"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    DOTNET = "dotnet"
    FLUTTER = "flutter"
    REACT_NATIVE = "react_native"
    EMPTY = "empty"
    UNKNOWN = "unknown"


class WorkspaceLifecycle(str, Enum):
    """Lifecycle states for a Workspace."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class WorkspaceStatus(str, Enum):
    """Operational status of a Workspace."""
    VALID = "valid"
    DEGRADED = "degraded"
    INVALID = "invalid"
    UNVERIFIED = "unverified"


class TrustLevel(str, Enum):
    """Security and execution trust boundary levels."""
    UNTRUSTED = "untrusted"
    RESTRICTED = "restricted"
    TRUSTED = "trusted"
    VERIFIED = "verified"


class ArtifactCategory(str, Enum):
    """Canonical artifact classification types."""
    SOURCE_CODE = "source_code"
    DOCUMENTATION = "documentation"
    IMAGES = "images"
    REPORTS = "reports"
    TESTS = "tests"
    PRESENTATIONS = "presentations"
    ARCHITECTURE = "architecture"
    LOGS = "logs"
    PLANS = "plans"
    SESSIONS = "sessions"
    TEMPORARY_OUTPUTS = "temporary_outputs"


class DiscoveryPriority(int, Enum):
    """Priority order for declarative workspace discovery."""
    EXPLICIT_ARGUMENT = 1
    CURRENT_WORKING_DIRECTORY = 2
    PARENT_PROJECT_DETECTION = 3
    WORKSPACE_CONFIGURATION = 4


class ValidationIssue(BaseModel):
    """Individual workspace or project validation finding."""
    model_config = ConfigDict(extra="allow")

    severity: Literal["error", "warning", "info"] = "warning"
    code: str
    message: str
    target_path: Path | None = None


class ValidationState(BaseModel):
    """Summary of workspace validation and integrity status."""
    model_config = ConfigDict(extra="allow")

    valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)
    last_validated: str | None = None


class ProjectMetadata(BaseModel):
    """Declarative metadata for a project residing within a workspace."""
    model_config = ConfigDict(extra="allow")

    project_id: str
    name: str
    project_type: ProjectType = ProjectType.UNKNOWN
    root_path: Path
    framework_version: str | None = None
    language_version: str | None = None
    manifest_path: Path | None = None
    is_empty: bool = False
    attributes: dict[str, Any] = Field(default_factory=dict)


class WorkspaceMetadata(BaseModel):
    """Canonical Workspace metadata defining boundaries, roots, and lifecycle."""
    model_config = ConfigDict(extra="allow")

    workspace_id: str
    name: str
    workspace_root: Path
    engine_root: Path
    project_type: ProjectType = ProjectType.UNKNOWN
    lifecycle: WorkspaceLifecycle = WorkspaceLifecycle.ACTIVE
    status: WorkspaceStatus = WorkspaceStatus.VALID
    created: str
    version: str = "1.0.0"
    owner: str | None = None
    artifact_root: Path
    session_root: Path
    logs_root: Path
    memory_root: Path
    configuration_root: Path
    plans_root: Path | None = None
    history_root: Path | None = None
    traces_root: Path | None = None
    generated_root: Path | None = None
    temporary_root: Path | None = None
    reports_root: Path | None = None
    approvals_root: Path | None = None
    cache_root: Path | None = None
    context_root: Path | None = None
    knowledge_root: Path | None = None
    runtime_root: Path | None = None
    locks_root: Path | None = None
    validation: ValidationState = Field(default_factory=ValidationState)
    trust: TrustLevel = TrustLevel.TRUSTED
    discovery_method: DiscoveryPriority | str = DiscoveryPriority.CURRENT_WORKING_DIRECTORY
    discovery_source: str = "current_working_directory"
    confidence: float = 1.0


class ArtifactDestination(BaseModel):
    """Resolved routing destination for generated artifacts."""
    model_config = ConfigDict(extra="allow")

    category: ArtifactCategory
    relative_path: Path
    absolute_path: Path
    workspace_root: Path
    engine_root: Path
    read_only_engine_asserted: bool = True

    def validate_boundary(self) -> bool:
        """Verify destination path resides strictly inside workspace_root and outside engine_root."""
        try:
            abs_dest = self.absolute_path.resolve()
            abs_ws = self.workspace_root.resolve()
            abs_eng = self.engine_root.resolve()

            # Destination must be relative to workspace_root
            abs_dest.relative_to(abs_ws)

            # Destination must NOT be inside engine_root unless engine_root is equal to workspace_root (disallowed)
            if abs_eng in abs_dest.parents or abs_dest == abs_eng:
                return False
            return True
        except ValueError:
            return False


class ExecutionContext(BaseModel):
    """Runtime context binding Engine Root and Workspace Root locations."""
    model_config = ConfigDict(extra="allow")

    engine_root: Path
    workspace_root: Path
    cwd: Path
    workspace_metadata: WorkspaceMetadata | None = None
    project_metadata: ProjectMetadata | None = None
    discovery_method: DiscoveryPriority | str = DiscoveryPriority.CURRENT_WORKING_DIRECTORY
    discovery_source: str = "current_working_directory"
    confidence: float = 1.0

    @computed_field
    @property
    def project_type(self) -> ProjectType:
        if self.project_metadata:
            return self.project_metadata.project_type
        if self.workspace_metadata:
            return self.workspace_metadata.project_type
        return ProjectType.UNKNOWN

    @computed_field
    @property
    def project_name(self) -> str:
        if self.project_metadata and self.project_metadata.name:
            return self.project_metadata.name
        if self.workspace_metadata and self.workspace_metadata.name:
            return self.workspace_metadata.name
        return self.workspace_root.name

    @computed_field
    @property
    def validation_status(self) -> WorkspaceStatus:
        if self.workspace_metadata:
            return self.workspace_metadata.status
        return WorkspaceStatus.VALID

    def is_engine_read_only(self) -> bool:
        """Assert that Engine Root is separated and protected from workspace writes."""
        return self.engine_root.resolve() != self.workspace_root.resolve()


class DiscoveryRuleSpec(BaseModel):
    """Declarative specification for workspace discovery priority and candidate evaluation."""
    model_config = ConfigDict(extra="allow")

    priority: DiscoveryPriority
    name: str
    description: str
    enabled: bool = True


class ArtifactOwnership(BaseModel):
    """Provenance and ownership metadata declared by every generated artifact.

    Fields required by ACR-003 Phase W3:
    Workspace, Owner, Mission, Workflow, Agent, Timestamp, Artifact Type,
    Generation Source, Provenance, Validation.
    """

    model_config = ConfigDict(extra="allow")

    workspace_id: str
    owner: str
    mission: str | None = None
    workflow: str | None = None
    agent: str | None = None
    timestamp: str
    artifact_type: ArtifactCategory
    generation_source: str
    provenance: str
    validation: ValidationState = Field(default_factory=ValidationState)


class ArtifactRecord(BaseModel):
    """A routed artifact paired with its ownership provenance."""

    model_config = ConfigDict(extra="allow")

    destination: ArtifactDestination
    ownership: ArtifactOwnership
    filename: str


class WorkspaceStorageSpec(BaseModel):
    """Canonical specification of all `.oniroute/` subdirectory names.

    Used by ``WorkspaceStorage`` to derive root paths from the workspace root.
    Centralized here so new categories can be added in one place.
    """

    model_config = ConfigDict(extra="allow")

    sessions: str = "sessions"
    history: str = "history"
    traces: str = "traces"
    artifacts: str = "artifacts"
    generated: str = "generated"
    temporary: str = "temporary"
    reports: str = "reports"
    approvals: str = "approvals"
    cache: str = "cache"
    logs: str = "logs"
    memory: str = "memory"
    context: str = "context"
    knowledge: str = "knowledge"
    plans: str = "plans"
    runtime: str = "runtime"
    locks: str = "locks"

    @property
    def all_names(self) -> tuple[str, ...]:
        return (
            self.sessions,
            self.history,
            self.traces,
            self.artifacts,
            self.generated,
            self.temporary,
            self.reports,
            self.approvals,
            self.cache,
            self.logs,
            self.memory,
            self.context,
            self.knowledge,
            self.plans,
            self.runtime,
            self.locks,
        )
