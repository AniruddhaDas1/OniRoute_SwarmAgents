"""Report Storage for OniRoute Workspace Architecture (ACR-003 Phase W4).

Persists optimization reports, governance audit records, and planning reports
as JSON files in ``.oniroute/reports/``. Report storage is workspace-local;
Engine Root is never written.
"""

from __future__ import annotations

import json
from pathlib import Path

from .engine_safety import assert_no_engine_write
from .models import WorkspaceMetadata
from .storage import WorkspaceStorage


class ReportStorage:
    """Workspace-local persistence for runtime reports.

    Each report is stored as a JSON file named ``<report_id>.json`` inside
    ``.oniroute/reports/``.  The ``report_type`` field in the JSON payload
    distinguishes between optimization, audit, and planning reports.
    """

    def __init__(self, workspace_metadata: WorkspaceMetadata) -> None:
        self._metadata = workspace_metadata
        self._storage = WorkspaceStorage(workspace_metadata)

    @property
    def reports_root(self) -> Path:
        return self._storage.reports_root

    def persist_report(self, report_id: str, data: dict, report_type: str = "general") -> Path:
        """Write a report to ``.oniroute/reports/<report_id>.json``."""
        target_dir = self._storage.ensure_dir("reports")
        target = target_dir / f"{report_id}.json"
        assert_no_engine_write(
            target,
            self._metadata.workspace_root,
            self._metadata.engine_root,
        )
        payload = {"report_id": report_id, "report_type": report_type, "data": data}
        with target.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)
        return target

    def load_report(self, report_id: str) -> dict | None:
        """Load a single report by ID. Returns None if missing."""
        target = self.reports_root / f"{report_id}.json"
        if not target.is_file():
            return None
        with target.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def load_all_reports(self) -> list[dict]:
        """Load all reports, sorted by filename."""
        if not self.reports_root.is_dir():
            return []
        records: list[dict] = []
        for path in sorted(self.reports_root.glob("*.json")):
            with path.open("r", encoding="utf-8") as fh:
                records.append(json.load(fh))
        return records

    def load_reports_by_type(self, report_type: str) -> list[dict]:
        """Load reports filtered by report_type."""
        return [
            r for r in self.load_all_reports()
            if r.get("report_type") == report_type
        ]

    def count(self) -> int:
        """Count persisted report files."""
        if not self.reports_root.is_dir():
            return 0
        return sum(1 for _ in self.reports_root.glob("*.json"))
