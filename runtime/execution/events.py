from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


EventType = Literal["WorkflowStarted", "StepStarted", "StepCompleted", "StepSkipped", "ArtifactGenerated", "WorkflowCompleted", "WorkflowFailed"]


class ExecutionEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: EventType
    execution_id: str
    subject_id: str
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)


class EventBus:
    def __init__(self): self.events: list[ExecutionEvent] = []
    def emit(self, event_type: EventType, execution_id: str, subject_id: str, **data: Any) -> ExecutionEvent:
        event = ExecutionEvent(type=event_type, execution_id=execution_id, subject_id=subject_id, timestamp=datetime.now(timezone.utc), data=data)
        self.events.append(event); return event
