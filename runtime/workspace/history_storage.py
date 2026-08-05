"""Execution History Storage for OniRoute Workspace Architecture (ACR-003 Phase W3).

Persists execution results as JSON records in ``.oniroute/history/``.
History is strictly workspace-scoped — Engine Root is never written.
"""

from __future__ import annotations

import json
from pathlib import Path

from .engine_safety import assert_no_engine_write
from .models import WorkspaceMetadata
from .storage import WorkspaceStorage


class ExecutionHistoryStorage:
    """Workspace-local persistence for execution history records.

    Each execution result is stored as a JSON file named
    ``<execution_id>.json`` inside ``.oniroute/history/``.
    """

    def __init__(self, workspace_metadata: WorkspaceMetadata) -> None:
        self._metadata = workspace_metadata
        self._storage = WorkspaceStorage(workspace_metadata)

    @property
    def history_root(self) -> Path:
        return self._storage.history_root

    def persist(self, execution_id: str, data: dict) -> Path:
        """Write an execution record to ``.oniroute/history/<execution_id>.json``."""
        target_dir = self._storage.ensure_dir("history")
        target = target_dir / f"{execution_id}.json"
        assert_no_engine_write(
            target,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        with target.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, default=str)
        return target

    def load(self, execution_id: str) -> dict | None:
        """Load a single execution record by ID."""
        target = self.history_root / f"{execution_id}.json"
        if not target.is_file():
            return None
        with target.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def load_all(self) -> list[dict]:
        """Load all execution records, sorted by filename (chronological by ID)."""
        if not self.history_root.is_dir():
            return []
        records: list[dict] = []
        for path in sorted(self.history_root.glob("*.json")):
            with path.open("r", encoding="utf-8") as fh:
                records.append(json.load(fh))
        return records

    def count(self) -> int:
        """Count persisted execution records."""
        if not self.history_root.is_dir():
            return 0
        return sum(1 for _ in self.history_root.glob("*.json"))
