"""Autonomous Engineering Worker Subsystem Package (Phase P5.E1).

Consumes EngineeringContractReport and generates source code, configuration, tests, documentation, and assets.
"""

from runtime.engineering.engine import EngineeringWorkerEngine
from runtime.engineering.exceptions import (
    EngineeringBoundaryViolation,
    EngineeringExecutionError,
    EngineeringWorkerError,
)
from runtime.engineering.models import EngineeringResult

__all__ = [
    "EngineeringWorkerEngine",
    "EngineeringResult",
    "EngineeringWorkerError",
    "EngineeringBoundaryViolation",
    "EngineeringExecutionError",
]
