"""Implementation Allocation Subsystem Package (Phase P4.G3).

Consumes ProjectBlueprintReport and produces ImplementationAllocationReport.
"""

from runtime.allocation.engine import PROFILE_DISCIPLINE_MAP, ImplementationAllocationEngine
from runtime.allocation.exceptions import (
    AllocationDependencyError,
    AllocationValidationError,
    ImplementationAllocationError,
)
from runtime.allocation.models import (
    AllocationTarget,
    ImplementationAllocationReport,
    ImplementationPriority,
)

__all__ = [
    "ImplementationAllocationEngine",
    "ImplementationAllocationReport",
    "AllocationTarget",
    "ImplementationPriority",
    "PROFILE_DISCIPLINE_MAP",
    "ImplementationAllocationError",
    "AllocationValidationError",
    "AllocationDependencyError",
]
