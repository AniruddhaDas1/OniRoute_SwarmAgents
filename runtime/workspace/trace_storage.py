"""Trace Storage for OniRoute Workspace Architecture (ACR-003 Phase W3).

Persists execution trace events as JSONL files in ``.oniroute/traces/``.
Trace storage is workspace-local; Engine Root is never written.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .engine_safety import assert_no_engine_write
from .models import WorkspaceMetadata
from .storage import WorkspaceStorage


class TraceStorage:
    """Workspace-local persistence for execution trace event streams.

    Each execution produces a trace file ``<execution_id>.jsonl`` inside
    ``.oniroute/traces/`` containing one JSON object per line.
    """

    def __init__(self, workspace_metadata: WorkspaceMetadata) -> None:
        self._metadata = workspace_metadata
        self._storage = WorkspaceStorage(workspace_metadata)

    @property
    def traces_root(self) -> Path:
        return self._storage.traces_root

    def write_trace(self, execution_id: str, events: list[dict]) -> Path:
        """Write trace events to ``.oniroute/traces/<execution_id>.jsonl``."""
        target_dir = self._storage.ensure_dir("traces")
        target = target_dir / f"{execution_id}.jsonl"
        assert_no_engine_write(
            target,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        with target.open("w", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(event, default=str) + "\n")
        return target

    def read_trace(self, execution_id: str) -> list[dict]:
        """Read all events from a trace file. Returns empty list if missing."""
        target = self.traces_root / f"{execution_id}.jsonl"
        if not target.is_file():
            return []
        events: list[dict] = []
        with target.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def list_traces(self) -> list[str]:
        """Return execution IDs that have trace files."""
        if not self.traces_root.is_dir():
            return []
        return sorted(
            path.stem for path in self.traces_root.glob("*.jsonl")
        )

    def count(self) -> int:
        """Count trace files."""
        if not self.traces_root.is_dir():
            return 0
        return sum(1 for _ in self.traces_root.glob("*.jsonl"))

    def append_trace(self, execution_id: str, events: list[dict]) -> Path:
        """Append events to an existing trace file (or create it)."""
        target_dir = self._storage.ensure_dir("traces")
        target = target_dir / f"{execution_id}.jsonl"
        assert_no_engine_write(
            target,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        with target.open("a", encoding="utf-8") as fh:
            for event in events:
                fh.write(json.dumps(event, default=str) + "\n")
        return target
