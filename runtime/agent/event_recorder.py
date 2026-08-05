"""Deterministic Event Recorder for OniRoute Agent Runtime (ACR-006 Phase R2).

Append-only in-memory event recorder. No execution, no AI calls.
"""

from __future__ import annotations

from .contracts import EventRecorderContract
from .models import AgentSession, ExecutionEvent


class EventRecorder(EventRecorderContract):
    """Concrete append-only EventRecorder. Stores events in-memory per session."""

    def __init__(self) -> None:
        self._store: dict[str, list[ExecutionEvent]] = {}

    def record_event(self, session: AgentSession, event: ExecutionEvent) -> ExecutionEvent:
        """Append an immutable ExecutionEvent to the session's event log."""
        if session.session_id not in self._store:
            self._store[session.session_id] = []
        self._store[session.session_id].append(event)
        # Also append to the session's own events list (mutable during init)
        session.events.append(event)
        return event

    def get_events(self, session_id: str) -> list[ExecutionEvent]:
        """Retrieve all events recorded for a specific session ID."""
        return list(self._store.get(session_id, []))
