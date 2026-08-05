"""Workspace Architecture Foundation package for OniRoute (ACR-003 Phase W2).

Phase W3 adds workspace-local storage management, the Artifact Router,
artifact ownership, session/history/trace/log storage, and engine-safety
assertions.
"""

from .artifact_router import ArtifactRouter
from .contracts import (
    ArtifactRouterContract,
    EngineResolverContract,
    WorkspaceManagerContract,
    WorkspaceResolverContract,
)
from .discovery import WorkspaceResolver
from .engine import EngineResolver
from .engine_safety import (
    PROTECTED_ENGINE_TARGETS,
    assert_no_engine_write,
    assert_outside_engine,
    assert_within_workspace,
)
from .exceptions import (
    ArtifactCollisionError,
    EngineWriteViolation,
    WorkspaceBoundaryViolation,
    WorkspaceStorageError,
)
from .history_storage import ExecutionHistoryStorage
from .log_storage import LogStorage
from .manager import WorkspaceManager
from .models import (
    ArtifactCategory,
    ArtifactDestination,
    ArtifactOwnership,
    ArtifactRecord,
    DiscoveryPriority,
    DiscoveryRuleSpec,
    ExecutionContext,
    ProjectMetadata,
    ProjectType,
    TrustLevel,
    ValidationIssue,
    ValidationState,
    WorkspaceLifecycle,
    WorkspaceMetadata,
    WorkspaceStorageSpec,
    WorkspaceStatus,
)
from .project import ProjectDetector
from .session_storage import SessionStorage
from .storage import WorkspaceStorage
from .trace_storage import TraceStorage
from .validation import WorkspaceValidator

__all__ = [
    "ArtifactCategory",
    "ArtifactCollisionError",
    "ArtifactDestination",
    "ArtifactOwnership",
    "ArtifactRecord",
    "ArtifactRouter",
    "ArtifactRouterContract",
    "DiscoveryPriority",
    "DiscoveryRuleSpec",
    "EngineResolver",
    "EngineResolverContract",
    "EngineWriteViolation",
    "ExecutionHistoryStorage",
    "ExecutionContext",
    "LogStorage",
    "ProjectDetector",
    "ProjectMetadata",
    "ProjectType",
    "PROTECTED_ENGINE_TARGETS",
    "SessionStorage",
    "TraceStorage",
    "TrustLevel",
    "ValidationIssue",
    "ValidationState",
    "WorkspaceBoundaryViolation",
    "WorkspaceLifecycle",
    "WorkspaceManager",
    "WorkspaceManagerContract",
    "WorkspaceMetadata",
    "WorkspaceResolver",
    "WorkspaceResolverContract",
    "WorkspaceStatus",
    "WorkspaceStorage",
    "WorkspaceStorageError",
    "WorkspaceStorageSpec",
    "assert_no_engine_write",
    "assert_outside_engine",
    "assert_within_workspace",
]
