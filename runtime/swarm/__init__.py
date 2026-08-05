"""Swarm Initialization package for OniRoute (Phase P3.A2).

Converts MissionDeploymentPlan into an immutable RuntimeExecutionSnapshot.
"""

from .benchmark import benchmark_swarm_initialization
from .engine import SwarmInitializationEngine
from .exceptions import (
    InvalidSnapshotError,
    SessionInitializationError,
    StorageConnectionError,
    SwarmInitializationError,
)
from .models import (
    BudgetStatus,
    CheckpointStatus,
    EventBusReferences,
    ExecutionCursor,
    RetryStatus,
    RuntimeExecutionSnapshot,
    SessionStateRecord,
    StorageReferences,
    WaveExecutionStatus,
    WorkspaceReferences,
)

__all__ = [
    "BudgetStatus",
    "CheckpointStatus",
    "EventBusReferences",
    "ExecutionCursor",
    "InvalidSnapshotError",
    "RetryStatus",
    "RuntimeExecutionSnapshot",
    "SessionInitializationError",
    "SessionStateRecord",
    "StorageConnectionError",
    "StorageReferences",
    "SwarmInitializationEngine",
    "SwarmInitializationError",
    "WaveExecutionStatus",
    "WorkspaceReferences",
    "benchmark_swarm_initialization",
]
