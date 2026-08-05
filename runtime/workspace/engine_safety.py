"""Engine Root safety assertions for OniRoute Workspace Architecture (ACR-003 Phase W3).

These assertions enforce the read-only Engine Root boundary. Every subsystem
that writes to disk — artifact routing, session storage, history, traces, logs,
cache, and all other `.oniroute/` subdirectories — must pass through these guards.

Nothing except framework maintenance may ever write into Engine Root.
"""

from __future__ import annotations

from pathlib import Path

from .exceptions import EngineWriteViolation, WorkspaceBoundaryViolation

PROTECTED_ENGINE_TARGETS: tuple[str, ...] = (
    "artifacts",
    "logs",
    "sessions",
    "plans",
    "memory",
    "history",
    "generated",
    "temporary",
    "traces",
    "reports",
    "approvals",
    "cache",
    "context",
    "knowledge",
    "runtime",
    "locks",
)


def assert_within_workspace(path: Path, workspace_root: Path) -> Path:
    """Resolve *path* and assert it resides inside *workspace_root*.

    Returns the resolved absolute path on success.
    Raises ``WorkspaceBoundaryViolation`` if the path escapes the workspace.
    """
    abs_path = path.resolve()
    abs_ws = workspace_root.resolve()
    try:
        abs_path.relative_to(abs_ws)
    except ValueError as exc:
        raise WorkspaceBoundaryViolation(
            f"Path '{abs_path}' is outside workspace root '{abs_ws}'."
        ) from exc
    return abs_path


def assert_outside_engine(path: Path, engine_root: Path) -> Path:
    """Resolve *path* and assert it does NOT reside inside *engine_root*.

    The path must be neither the Engine Root itself nor any descendant of it.
    Raises ``EngineWriteViolation`` if the path is inside the Engine Root.
    """
    abs_path = path.resolve()
    abs_eng = engine_root.resolve()
    if abs_path == abs_eng or abs_eng in abs_path.parents:
        raise EngineWriteViolation(
            f"Write blocked: '{abs_path}' is inside Engine Root '{abs_eng}'. "
            f"Engine Root is permanently read-only."
        )
    return abs_path


def assert_no_engine_write(
    path: Path, workspace_root: Path, engine_root: Path
) -> Path:
    """Combined guard: *path* must be within the workspace AND outside the engine.

    This is the single entry point every write operation should call before
    touching the filesystem. Returns the resolved absolute path on success.
    """
    abs_path = assert_within_workspace(path, workspace_root)
    assert_outside_engine(abs_path, engine_root)
    return abs_path
