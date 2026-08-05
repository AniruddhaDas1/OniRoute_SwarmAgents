"""Implementation Allocation Exceptions (Phase P4.G3)."""

from __future__ import annotations


class ImplementationAllocationError(Exception):
    """Base exception for implementation allocation failures."""

    pass


class AllocationValidationError(ImplementationAllocationError):
    """Raised when allocation validation checks fail."""

    pass


class AllocationDependencyError(ImplementationAllocationError):
    """Raised when dependency resolution or topological sorting fails."""

    pass
