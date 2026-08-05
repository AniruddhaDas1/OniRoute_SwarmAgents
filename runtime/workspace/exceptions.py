"""Workspace storage exceptions for OniRoute (ACR-003 Phase W3).

Exception hierarchy for workspace-local storage, artifact routing,
and Engine Root safety violations.
"""

from __future__ import annotations


class WorkspaceStorageError(Exception):
    """Base exception for all workspace storage operations."""


class EngineWriteViolation(WorkspaceStorageError):
    """Raised when a write targets the Engine Root or a path inside it.

    The Engine Root must remain permanently read-only. Any operation that
    would write artifacts, logs, sessions, history, plans, memory, generated
    files, or temporary files into the Engine Root is blocked by this
    assertion.
    """


class WorkspaceBoundaryViolation(WorkspaceStorageError):
    """Raised when a path resolves outside the Workspace Root."""


class ArtifactCollisionError(WorkspaceStorageError):
    """Raised when an artifact collision cannot be resolved.

    In strict-collision mode, if the target filename already exists in the
    destination directory, this error is raised instead of auto-renaming.
    """
