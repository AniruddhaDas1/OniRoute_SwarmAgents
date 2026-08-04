"""Workspace Architecture Foundation package for OniRoute (ACR-003 Phase W2)."""

from .contracts import (
    ArtifactRouterContract,
    EngineResolverContract,
    WorkspaceManagerContract,
    WorkspaceResolverContract,
)
from .discovery import WorkspaceResolver
from .engine import EngineResolver
from .manager import WorkspaceManager
from .models import (
    ArtifactCategory,
    ArtifactDestination,
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
    WorkspaceStatus,
)
from .project import ProjectDetector
from .validation import WorkspaceValidator

__all__ = [
    "ArtifactCategory",
    "ArtifactDestination",
    "ArtifactRouterContract",
    "DiscoveryPriority",
    "DiscoveryRuleSpec",
    "EngineResolver",
    "EngineResolverContract",
    "ExecutionContext",
    "ProjectDetector",
    "ProjectMetadata",
    "ProjectType",
    "TrustLevel",
    "ValidationIssue",
    "ValidationState",
    "WorkspaceLifecycle",
    "WorkspaceManager",
    "WorkspaceManagerContract",
    "WorkspaceMetadata",
    "WorkspaceResolver",
    "WorkspaceResolverContract",
    "WorkspaceStatus",
    "WorkspaceValidator",
]
