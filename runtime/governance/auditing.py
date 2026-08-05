from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .models import AuditRecord

if TYPE_CHECKING:
    from runtime.workspace import ReportStorage


class AuditEngine:
    def __init__(self, report_storage: "ReportStorage | None" = None) -> None:
        self.records: list[AuditRecord] = []
        self._report_storage = report_storage
        if report_storage is not None:
            self._load_existing()

    def _load_existing(self) -> None:
        """Populate records from persisted audit reports."""
        for record in self._report_storage.load_reports_by_type("audit"):  # type: ignore[union-attr]
            self.records.append(AuditRecord(**record["data"]))

    def record(self, request, result, outcome: str) -> AuditRecord:
        item = AuditRecord(
            id=f"audit:{len(self.records) + 1}",
            timestamp=datetime.now(timezone.utc),
            request=request,
            result=result,
            outcome=outcome,
        )
        self.records.append(item)
        if self._report_storage is not None:
            self._report_storage.persist_report(
                item.id,
                item.model_dump(mode="json"),
                report_type="audit",
            )
        return item
