from __future__ import annotations

from runtime.workspace import ExecutionHistoryStorage
from .models import ExecutionResult


class ExecutionHistory:
    """In-memory and/or workspace-persisted execution history.

    When an :class:`ExecutionHistoryStorage` is supplied, records are persisted
    to ``.oniroute/history/`` and loaded on demand.  When omitted, behaviour
    is identical to the original in-memory implementation.
    """

    def __init__(self, history_storage: ExecutionHistoryStorage | None = None) -> None:
        self.records: list[ExecutionResult] = []
        self._history_storage = history_storage

    def add(self, result: ExecutionResult) -> None:
        self.records.append(result)
        if self._history_storage is not None:
            self._history_storage.persist(result.execution_id, result.model_dump(mode="json"))

    def all(self) -> tuple[ExecutionResult, ...]:
        if self._history_storage is not None:
            return tuple(ExecutionResult(**r) for r in self._history_storage.load_all())
        return tuple(self.records)
