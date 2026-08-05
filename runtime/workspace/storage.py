"""Workspace Storage Manager for OniRoute (ACR-003 Phase W3).

Manages the canonical `.oniroute/` directory structure, lazy directory
creation, ``workspace.yaml`` serialization, and per-subdirectory introspection.

Every directory-creating or file-writing operation passes through the engine
safety guards in :mod:`engine_safety` to guarantee the Engine Root is never
mutated.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .engine_safety import assert_no_engine_write
from .exceptions import WorkspaceStorageError
from .models import WorkspaceMetadata, WorkspaceStorageSpec


class WorkspaceStorage:
    """Manages the canonical ``<workspace_root>/.oniroute/`` directory tree.

    Subdirectories are created lazily on first access. All paths are validated
    against engine-safety assertions before any filesystem write.
    """

    ONIROUTE_SUBDIR: str = ".oniroute"

    # Canonical subdirectory name → WorkspaceMetadata field name.
    _ROOT_MAP: dict[str, str] = {
        "sessions": "session_root",
        "history": "history_root",
        "traces": "traces_root",
        "artifacts": "artifact_root",
        "generated": "generated_root",
        "temporary": "temporary_root",
        "reports": "reports_root",
        "approvals": "approvals_root",
        "cache": "cache_root",
        "logs": "logs_root",
        "memory": "memory_root",
        "context": "context_root",
        "knowledge": "knowledge_root",
        "runtime": "runtime_root",
        "locks": "locks_root",
        "plans": "plans_root",
    }

    def __init__(self, workspace_metadata: WorkspaceMetadata) -> None:
        self._metadata = workspace_metadata
        self._spec = WorkspaceStorageSpec()
        self._root_dir = workspace_metadata.workspace_root / self.ONIROUTE_SUBDIR
        self._engine_root = workspace_metadata.engine_root

    # ── root paths ──────────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        """The ``.oniroute/`` base directory."""
        return self._root_dir

    @property
    def workspace_yaml_path(self) -> Path:
        """Path to ``.oniroute/workspace.yaml``."""
        return self._root_dir / "workspace.yaml"

    def _resolve_root(self, dir_name: str) -> Path:
        """Resolve a subdirectory root from metadata or derive from workspace_root."""
        field_name = self._ROOT_MAP.get(dir_name)
        if field_name is not None:
            value = getattr(self._metadata, field_name, None)
            if value is not None:
                return value
        return self._root_dir / dir_name

    # ── subdirectory root properties ───────────────────────────────────

    @property
    def sessions_root(self) -> Path:
        return self._resolve_root("sessions")

    @property
    def history_root(self) -> Path:
        return self._resolve_root("history")

    @property
    def traces_root(self) -> Path:
        return self._resolve_root("traces")

    @property
    def artifacts_root(self) -> Path:
        return self._resolve_root("artifacts")

    @property
    def generated_root(self) -> Path:
        return self._resolve_root("generated")

    @property
    def temporary_root(self) -> Path:
        return self._resolve_root("temporary")

    @property
    def reports_root(self) -> Path:
        return self._resolve_root("reports")

    @property
    def approvals_root(self) -> Path:
        return self._resolve_root("approvals")

    @property
    def cache_root(self) -> Path:
        return self._resolve_root("cache")

    @property
    def logs_root(self) -> Path:
        return self._resolve_root("logs")

    @property
    def memory_root(self) -> Path:
        return self._resolve_root("memory")

    @property
    def plans_root(self) -> Path:
        return self._resolve_root("plans")

    @property
    def context_root(self) -> Path:
        return self._resolve_root("context")

    @property
    def knowledge_root(self) -> Path:
        return self._resolve_root("knowledge")

    @property
    def runtime_root(self) -> Path:
        return self._resolve_root("runtime")

    @property
    def locks_root(self) -> Path:
        return self._resolve_root("locks")

    # ── introspection ──────────────────────────────────────────────────

    @property
    def all_subdir_names(self) -> tuple[str, ...]:
        """Return all canonical subdirectory names."""
        return tuple(self._ROOT_MAP.keys())

    def exists(self) -> bool:
        """Check whether the ``.oniroute/`` directory exists on disk."""
        return self._root_dir.exists()

    def storage_status(self) -> dict[str, bool]:
        """Map each subdirectory name to its existence on disk."""
        return {name: self._resolve_root(name).exists() for name in self._ROOT_MAP}

    def count_entries(self, dir_name: str) -> int:
        """Count direct entries (files and subdirectories) in a subdirectory."""
        if dir_name not in self._ROOT_MAP:
            return 0
        target = self._resolve_root(dir_name)
        if not target.is_dir():
            return 0
        try:
            return sum(1 for _ in target.iterdir())
        except OSError:
            return 0

    # ── lazy directory creation ────────────────────────────────────────

    def ensure_dir(self, dir_name: str) -> Path:
        """Create ``.oniroute/<dir_name>`` if it does not exist.

        Validates engine safety before writing. Idempotent.
        """
        if dir_name not in self._ROOT_MAP:
            raise WorkspaceStorageError(f"Unknown workspace subdirectory: {dir_name}")
        target = self._resolve_root(dir_name)
        assert_no_engine_write(
            target,
            self._metadata.workspace_root,
            self._engine_root,
        )
        target.mkdir(parents=True, exist_ok=True)
        return target

    def ensure_all(self) -> dict[str, Path]:
        """Create every canonical subdirectory. Returns a name → path mapping."""
        return {name: self.ensure_dir(name) for name in self._ROOT_MAP}

    def ensure_workspace_root(self) -> Path:
        """Create the ``.oniroute/`` base directory if it does not exist."""
        assert_no_engine_write(
            self._root_dir,
            self._metadata.workspace_root,
            self._engine_root,
        )
        self._root_dir.mkdir(parents=True, exist_ok=True)
        return self._root_dir

    # ── workspace.yaml I/O ─────────────────────────────────────────────

    def write_workspace_yaml(self, metadata: WorkspaceMetadata | None = None) -> Path:
        """Serialize ``WorkspaceMetadata`` to ``.oniroute/workspace.yaml``."""
        meta = metadata or self._metadata
        target = self.workspace_yaml_path
        assert_no_engine_write(
            target,
            self._metadata.workspace_root,
            self._engine_root,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        data = meta.model_dump(mode="json")
        with target.open("w", encoding="utf-8") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False, sort_keys=True)
        return target

    def read_workspace_yaml(self) -> WorkspaceMetadata | None:
        """Read and parse ``.oniroute/workspace.yaml`` into ``WorkspaceMetadata``."""
        target = self.workspace_yaml_path
        if not target.is_file():
            return None
        with target.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return WorkspaceMetadata(**data)
