"""OniRoute Agent Runtime package (ACR-006 Phase R1, R2, R3, R4 & R5 Certified)."""

from .artifact_collector import ArtifactCollector
from .contracts import (
    ArtifactCollectorContract,
    EventRecorderContract,
    ExecutionCoordinatorContract,
    ExecutionReporterContract,
    RuntimeInitializerContract,
    SessionManagerContract,
)
from .event_recorder import EventRecorder
from .execution_engine import AgentExecutionEngine
from .execution_reporter import ExecutionReporter
from .models import (
    ALLOWED_RUNTIME_TRANSITIONS,
    AgentSession,
    ArtifactRecord,
    ArtifactType,
    ExecutionEvent,
    ExecutionResult,
    ExecutionStatus,
    RuntimeContext,
    RuntimeEventType,
    RuntimeMetrics,
    RuntimeReport,
    RuntimeState,
    can_runtime_transition,
)
from .recovery import (
    DEPLOYMENT_POLICY,
    INFRASTRUCTURE_POLICY,
    SECURITY_POLICY,
    DefaultReviewPolicy,
    FailureCategory,
    FailureClassification,
    FailureClassifier,
    PauseRecord,
    PermissiveReviewPolicy,
    RecoveryEventType,
    RecoveryMetrics,
    RecoveryOrchestrator,
    RecoveryReport,
    RetryManager,
    RetryPolicy,
    RetryRecord,
    ReviewDecision,
    ReviewOutcome,
    ReviewPolicy,
    ReviewRecord,
    ReviewRule,
    RuleBasedReviewPolicy,
    RuntimeReviewEngine,
    StrictReviewPolicy,
)
from .runtime_initializer import RuntimeInitializer
from .session_coordinator import SessionCoordinator
from .session_manager import SessionManager
from .session_registry import SessionRegistry

__all__ = [
    # Runtime States & Transitions
    "RuntimeState",
    "ExecutionStatus",
    "ALLOWED_RUNTIME_TRANSITIONS",
    "can_runtime_transition",
    # Events
    "RuntimeEventType",
    "ExecutionEvent",
    # Artifacts
    "ArtifactType",
    "ArtifactRecord",
    # Metrics
    "RuntimeMetrics",
    # Context
    "RuntimeContext",
    # Session
    "AgentSession",
    # Results & Reports
    "ExecutionResult",
    "RuntimeReport",
    # Contracts
    "RuntimeInitializerContract",
    "SessionManagerContract",
    "ExecutionCoordinatorContract",
    "ArtifactCollectorContract",
    "EventRecorderContract",
    "ExecutionReporterContract",
    # R2 Implementations
    "RuntimeInitializer",
    "SessionManager",
    "SessionRegistry",
    "EventRecorder",
    "SessionCoordinator",
    # R3 Implementations
    "ArtifactCollector",
    "ExecutionReporter",
    "AgentExecutionEngine",
    # R4 — Recovery Engine
    "FailureCategory",
    "FailureClassification",
    "FailureClassifier",
    "PauseRecord",
    "RecoveryEventType",
    "RecoveryMetrics",
    "RecoveryOrchestrator",
    "RecoveryReport",
    "RetryManager",
    "RetryPolicy",
    "RetryRecord",
    "ReviewDecision",
    "ReviewOutcome",
    "ReviewRecord",
    "RuntimeReviewEngine",
    # R5 — Declarative Review Policies
    "ReviewPolicy",
    "DefaultReviewPolicy",
    "StrictReviewPolicy",
    "PermissiveReviewPolicy",
    "RuleBasedReviewPolicy",
    "ReviewRule",
    "SECURITY_POLICY",
    "INFRASTRUCTURE_POLICY",
    "DEPLOYMENT_POLICY",
]
