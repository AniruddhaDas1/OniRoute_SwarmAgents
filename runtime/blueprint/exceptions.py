"""Project Blueprint Exceptions (Phase P4.G2)."""

from __future__ import annotations


class ProjectBlueprintError(Exception):
    """Base exception for project blueprint failures."""

    pass


class BlueprintValidationError(ProjectBlueprintError):
    """Raised when blueprint validation checks fail."""

    pass


class BlueprintDependencyError(ProjectBlueprintError):
    """Raised when module dependency resolution fails or circular dependencies are detected."""

    pass
