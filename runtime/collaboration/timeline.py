"""Append-Only Timeline Logger for Engineering Collaboration (ACR-007 Phase C2).

Records chronological events for conversations, threads, messages, delivery, and closures.
Produces immutable Timeline objects.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .models import Timeline, TimelineEvent, TimelineEventType


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class CollaborationTimeline:
    """Append-only event logger capturing all collaboration activities into a Timeline."""

    def __init__(self, timeline_id: str | None = None, session_id: str = "collaboration-session") -> None:
        self._timeline_id = timeline_id or f"tl-{uuid.uuid4().hex[:8]}"
        self._session_id = session_id
        self._events: list[TimelineEvent] = []

    @property
    def timeline_id(self) -> str:
        return self._timeline_id

    @property
    def events(self) -> tuple[TimelineEvent, ...]:
        """Immutable snapshot tuple of all timeline events."""
        return tuple(self._events)

    def record_event(
        self,
        event_type: TimelineEventType,
        session_id: str,
        description: str,
        payload: dict | None = None,
    ) -> TimelineEvent:
        """Append an immutable TimelineEvent to the timeline."""
        event = TimelineEvent(
            event_id=f"evt-{event_type.value}-{uuid.uuid4().hex[:6]}",
            event_type=event_type,
            session_id=session_id,
            description=description,
            payload=payload or {},
            timestamp=_utcnow(),
        )
        self._events.append(event)
        return event

    def to_timeline(self) -> Timeline:
        """Return an immutable Timeline object representing the current state of the log."""
        return Timeline(
            timeline_id=self._timeline_id,
            session_id=self._session_id,
            events=list(self._events),
            created_at=_utcnow(),
        )
