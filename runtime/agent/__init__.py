"""OniRoute Agent Runtime package (ACR-006 Phase R1) — Architecture only."""

from .contracts import (
    ArtifactCollectorContract,
    EventRecorderContract,
    ExecutionCoordinatorContract,
    ExecutionReporterContract,
    RuntimeInitializerContract,
    SessionManagerContract,
)
from .models import (
    AgentSession,
    ArtifactRecord,
    ArtifactType,
    ALLOWED_RUNTIME_TRANSITIONS,
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
]
