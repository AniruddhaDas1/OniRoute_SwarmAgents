"""Autonomous Engineering Worker Subsystem Package (Phase P5.E1).

Consumes EngineeringContractReport and generates source code, configuration, tests, documentation, and assets.
"""

from runtime.engineering.certification import AutonomousEngineeringCertificationEngine
from runtime.engineering.engine import EngineeringWorkerEngine, InvocationPlanner, ResponseAggregator
from runtime.engineering.exceptions import (
    EngineeringBoundaryViolation,
    EngineeringExecutionError,
    EngineeringWorkerError,
)
from runtime.engineering.models import (
    BatchResult,
    EngineeringCertificationReport,
    EngineeringFailure,
    EngineeringResult,
    ExecutionBatch,
    InvocationTask,
    TaskContext,
    TaskState,
)

__all__ = [
    "EngineeringWorkerEngine",
    "EngineeringResult",
    "AutonomousEngineeringCertificationEngine",
    "EngineeringCertificationReport",
    "EngineeringWorkerError",
    "EngineeringBoundaryViolation",
    "EngineeringExecutionError",
    "InvocationTask",
    "ExecutionBatch",
    "BatchResult",
    "EngineeringFailure",
    "InvocationPlanner",
    "ResponseAggregator",
    "TaskState",
    "TaskContext",
]
