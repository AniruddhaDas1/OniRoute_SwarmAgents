from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from runtime.workspace import TraceStorage


EventType = Literal["WorkflowStarted", "StepStarted", "StepCompleted", "StepSkipped", "ArtifactGenerated", "WorkflowCompleted", "WorkflowFailed"]


class ExecutionEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: EventType
    execution_id: str
    subject_id: str
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


class EventBus:
    """In-memory event bus with optional workspace trace persistence.

    When a :class:`TraceStorage` is supplied, every emitted event is also
    appended to ``.oniroute/traces/<execution_id>.jsonl``.
    """

    def __init__(self, trace_storage: TraceStorage | None = None) -> None:
        self.events: list[ExecutionEvent] = []
        self._trace_storage = trace_storage

    def emit(self, event_type: EventType, execution_id: str, subject_id: str, **data: Any) -> ExecutionEvent:
        event = ExecutionEvent(type=event_type, execution_id=execution_id, subject_id=subject_id, timestamp=datetime.now(timezone.utc), data=data)
        self.events.append(event)
        if self._trace_storage is not None:
            self._trace_storage.append_trace(execution_id, [event.model_dump(mode="json")])
        return event
