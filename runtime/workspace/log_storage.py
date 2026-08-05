"""Log Storage for OniRoute Workspace Architecture (ACR-003 Phase W3).

Workspace-local logging in ``.oniroute/logs/``. Logs are never written to
Engine Root.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .engine_safety import assert_no_engine_write
from .models import WorkspaceMetadata
from .storage import WorkspaceStorage


class LogStorage:
    """Workspace-local log writer.

    Appends JSON-lines entries to ``.oniroute/logs/oniroute.log`` and
    supports archival of the current log file.
    """

    LOG_FILENAME = "oniroute.log"

    def __init__(self, workspace_metadata: WorkspaceMetadata) -> None:
        self._metadata = workspace_metadata
        self._storage = WorkspaceStorage(workspace_metadata)

    @property
    def logs_root(self) -> Path:
        return self._storage.logs_root

    @property
    def log_path(self) -> Path:
        return self.logs_root / self.LOG_FILENAME

    def write_log(self, level: str, message: str) -> Path:
        """Append a JSON-lines log entry to the current log file."""
        log_file = self._storage.ensure_dir("logs") / self.LOG_FILENAME
        assert_no_engine_write(
            log_file,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
        return log_file

    def read_logs(self, limit: int | None = None) -> list[dict]:
        """Read log entries, most-recent-first by default."""
        if not self.log_path.is_file():
            return []
        entries: list[dict] = []
        with self.log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        entries.reverse()
        if limit is not None:
            entries = entries[:limit]
        return entries

    def count(self) -> int:
        """Count log lines in the current log file."""
        if not self.log_path.is_file():
            return 0
        with self.log_path.open("r", encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())

    def archive(self) -> Path:
        """Move the current log file to an archived name with a timestamp."""
        if not self.log_path.exists():
            return self.log_path
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        archived = self.logs_root / f"oniroute_{ts}.log.archived"
        assert_no_engine_write(
            archived,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        self.log_path.rename(archived)
        return archived
