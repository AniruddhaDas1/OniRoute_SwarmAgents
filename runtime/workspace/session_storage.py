"""Session Storage for OniRoute Workspace Architecture (ACR-003 Phase W3).

Workspace-local session state management. Sessions live exclusively in
``.oniroute/sessions/`` and are never persisted to Engine Root.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .engine_safety import assert_no_engine_write
from .models import WorkspaceMetadata
from .storage import WorkspaceStorage


class SessionStorage:
    """Manages workspace-local session directories and manifests.

    Each session gets its own subdirectory under ``.oniroute/sessions/<session_id>/``
    containing a ``manifest.yaml`` and arbitrary session data files.
    """

    def __init__(self, workspace_metadata: WorkspaceMetadata) -> None:
        self._metadata = workspace_metadata
        self._storage = WorkspaceStorage(workspace_metadata)

    @property
    def sessions_root(self) -> Path:
        return self._storage.sessions_root

    def _session_path(self, session_id: str) -> Path:
        return self.sessions_root / session_id

    def create_session(
        self, session_id: str, metadata: dict | None = None
    ) -> Path:
        """Create a session directory and write an initial manifest."""
        session_dir = self._session_path(session_id)
        assert_no_engine_write(
            session_dir,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        session_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "session_id": session_id,
            "created": datetime.now(timezone.utc).isoformat(),
            "status": "open",
            "metadata": metadata or {},
        }
        (session_dir / "manifest.yaml").write_text(
            yaml.safe_dump(manifest, default_flow_style=False, sort_keys=True),
            encoding="utf-8",
        )
        return session_dir

    def write_data(self, session_id: str, filename: str, content: str | bytes) -> Path:
        """Write a data file inside a session directory."""
        session_dir = self._session_path(session_id)
        assert_no_engine_write(
            session_dir,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        session_dir.mkdir(parents=True, exist_ok=True)
        target = session_dir / filename
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"
        with target.open(mode, encoding=encoding) as fh:
            fh.write(content)
        return target

    def read_data(self, session_id: str, filename: str) -> str | None:
        """Read a data file from a session directory. Returns None if missing."""
        target = self._session_path(session_id) / filename
        if not target.is_file():
            return None
        return target.read_text(encoding="utf-8")

    def list_sessions(self) -> list[str]:
        """Return session IDs (subdirectory names) that have a manifest."""
        if not self.sessions_root.is_dir():
            return []
        return sorted(
            entry.name
            for entry in self.sessions_root.iterdir()
            if entry.is_dir() and (entry / "manifest.yaml").is_file()
        )

    def session_count(self) -> int:
        return len(self.list_sessions())

    def close_session(self, session_id: str) -> None:
        """Mark a session as closed in its manifest."""
        manifest_path = self._session_path(session_id) / "manifest.yaml"
        if not manifest_path.is_file():
            return
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        data["status"] = "closed"
        data["closed_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(
            yaml.safe_dump(data, default_flow_style=False, sort_keys=True),
            encoding="utf-8",
        )

    def delete_session(self, session_id: str) -> None:
        """Remove a session directory entirely."""
        session_dir = self._session_path(session_id)
        if session_dir.is_dir():
            import shutil

            shutil.rmtree(session_dir)
