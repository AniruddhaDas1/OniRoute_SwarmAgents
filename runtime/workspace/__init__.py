"""Workspace Architecture Foundation package for OniRoute (ACR-003 Phase W1)."""

from .contracts import (
    ArtifactRouterContract,
    EngineResolverContract,
    WorkspaceManagerContract,
    WorkspaceResolverContract,
)
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

__all__ = [
    "ArtifactCategory",
    "ArtifactDestination",
    "ArtifactRouterContract",
    "DiscoveryPriority",
    "DiscoveryRuleSpec",
    "EngineResolverContract",
    "ExecutionContext",
    "ProjectMetadata",
    "ProjectType",
    "TrustLevel",
    "ValidationIssue",
    "ValidationState",
    "WorkspaceLifecycle",
    "WorkspaceManagerContract",
    "WorkspaceMetadata",
    "WorkspaceResolverContract",
    "WorkspaceStatus",
]
