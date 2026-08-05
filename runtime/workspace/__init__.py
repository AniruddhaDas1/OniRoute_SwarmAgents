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
from .report_storage import ReportStorage
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
from .intelligence import WorkspaceContext, WorkspaceIntelligence, WorkspaceState
from .plan import EngineeringExecutionPlan, EngineeringPlanGenerator, RepositoryStrategy
from .project import ProjectDetector
from .repository import RepositoryContext, RepositoryIntelligence
from .session_storage import SessionStorage
from .storage import WorkspaceStorage
from .trace_storage import TraceStorage
from .validation import WorkspaceValidator
from runtime.scaffold import WorkspaceScaffoldEngine, WorkspaceScaffoldReport, WorkspaceScaffoldError
from runtime.blueprint import ProjectBlueprintEngine, ProjectBlueprintReport, ProjectBlueprintError
from runtime.allocation import ImplementationAllocationEngine, ImplementationAllocationReport, ImplementationAllocationError
from runtime.contracts import EngineeringContractEngine, EngineeringContractReport, EngineeringContractError
from runtime.assembly import ProjectAssemblyCertificationEngine, ProjectAssemblyCertificationReport, ProjectAssemblyError

__all__ = [
    "WorkspaceScaffoldEngine",
    "WorkspaceScaffoldReport",
    "WorkspaceScaffoldError",
    "ProjectBlueprintEngine",
    "ProjectBlueprintReport",
    "ProjectBlueprintError",
    "ImplementationAllocationEngine",
    "ImplementationAllocationReport",
    "ImplementationAllocationError",
    "EngineeringContractEngine",
    "EngineeringContractReport",
    "EngineeringContractError",
    "ProjectAssemblyCertificationEngine",
    "ProjectAssemblyCertificationReport",
    "ProjectAssemblyError",
    "WorkspaceValidator",
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
    "EngineeringExecutionPlan",
    "EngineeringPlanGenerator",
    "ExecutionHistoryStorage",
    "ExecutionContext",
    "LogStorage",
    "ProjectDetector",
    "ProjectMetadata",
    "ProjectType",
    "PROTECTED_ENGINE_TARGETS",
    "ReportStorage",
    "RepositoryContext",
    "RepositoryIntelligence",
    "RepositoryStrategy",
    "SessionStorage",
    "TraceStorage",
    "TrustLevel",
    "ValidationIssue",
    "ValidationState",
    "WorkspaceBoundaryViolation",
    "WorkspaceContext",
    "WorkspaceIntelligence",
    "WorkspaceLifecycle",
    "WorkspaceManager",
    "WorkspaceManagerContract",
    "WorkspaceMetadata",
    "WorkspaceResolver",
    "WorkspaceResolverContract",
    "WorkspaceState",
    "WorkspaceStatus",
    "WorkspaceStorage",
    "WorkspaceStorageError",
    "WorkspaceStorageSpec",
    "assert_no_engine_write",
    "assert_outside_engine",
    "assert_within_workspace",
]
