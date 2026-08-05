"""Workspace Scaffold Subsystem Package (Phase P4.G1).

Consumes RuntimeExecutionSnapshot and produces WorkspaceScaffoldReport.
"""

from runtime.scaffold.engine import WorkspaceScaffoldEngine, MANDATORY_DIRECTORIES
from runtime.scaffold.exceptions import (
    ScaffoldBoundaryViolation,
    ScaffoldCollisionError,
    ScaffoldValidationError,
    WorkspaceScaffoldError,
)
from runtime.scaffold.models import WorkspaceScaffoldReport

__all__ = [
    "WorkspaceScaffoldEngine",
    "WorkspaceScaffoldReport",
    "WorkspaceScaffoldError",
    "ScaffoldCollisionError",
    "ScaffoldValidationError",
    "ScaffoldBoundaryViolation",
    "MANDATORY_DIRECTORIES",
]
