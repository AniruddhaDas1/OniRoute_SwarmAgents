"""OniRoute Agent Runtime package (ACR-006 Phase R1 & R2)."""

from .contracts import (
    ArtifactCollectorContract,
    EventRecorderContract,
    ExecutionCoordinatorContract,
    ExecutionReporterContract,
    RuntimeInitializerContract,
    SessionManagerContract,
)
from .event_recorder import EventRecorder
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
    # Implementations
    "RuntimeInitializer",
    "SessionManager",
    "SessionRegistry",
    "EventRecorder",
    "SessionCoordinator",
]
