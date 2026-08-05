"""Workspace Scaffold Exceptions (Phase P4.G1)."""

from __future__ import annotations


class WorkspaceScaffoldError(Exception):
    """Base exception for workspace scaffold failures."""

    pass


class ScaffoldCollisionError(WorkspaceScaffoldError):
    """Raised when a scaffold operation encounters an unexpected file/directory collision."""

    pass


class ScaffoldValidationError(WorkspaceScaffoldError):
    """Raised when workspace scaffold validation checks fail."""

    pass


class ScaffoldBoundaryViolation(WorkspaceScaffoldError):
    """Raised when scaffold attempts to write outside the target workspace boundary or inside engine root."""

    pass
