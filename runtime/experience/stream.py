"""Execution Event Stream Engine for Phase P6.D2.

Publishes and distributes immutable execution events across CLI, VS Code Extension,
Web UI, and API presentation adapters without modifying runtime execution behavior.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from runtime.experience.models import StreamEvent, StreamEventType
from runtime.workspace.trace_storage import TraceStorage


class ExecutionEventStream:
    """Thread-safe Execution Event Stream for Phase P6.D2."""

    def __init__(self, trace_storage: Optional[TraceStorage] = None) -> None:
        """Initialize ExecutionEventStream.

        Args:
            trace_storage: Optional TraceStorage instance for persistence.
        """
        self._lock = threading.Lock()
        self._events: List[StreamEvent] = []
        self._listeners: Dict[str, Callable[[StreamEvent], None]] = {}
        self._trace_storage = trace_storage

    def subscribe(self, listener: Callable[[StreamEvent], None]) -> str:
        """Subscribe a callback listener to the stream.

        Args:
            listener: Callable accepting StreamEvent.

        Returns:
            str: Subscription ID.
        """
        with self._lock:
            sub_id = f"sub-{abs(hash(listener)) % 1000000:06d}"
            self._listeners[sub_id] = listener
            return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe a callback listener.

        Args:
            subscription_id: Subscription ID to remove.

        Returns:
            bool: True if subscriber was removed.
        """
        with self._lock:
            if subscription_id in self._listeners:
                del self._listeners[subscription_id]
                return True
            return False

    def publish_event(
        self,
        event_type: StreamEventType,
        mission_id: str,
        session_id: Optional[str] = None,
        stage_name: str = "ENGINEERING",
        agent_id: str = "",
        agent_role: str = "",
        task_description: str = "",
        progress_percentage: float = 0.0,
        files_created: Optional[List[str]] = None,
        files_modified: Optional[List[str]] = None,
        token_usage: Optional[Dict[str, int]] = None,
        estimated_cost_usd: float = 0.0,
        elapsed_time_ms: float = 0.0,
        estimated_remaining_ms: float = 0.0,
        quality_score: float = 10.0,
        production_ready: bool = False,
        message: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> StreamEvent:
        """Publish an immutable StreamEvent onto the stream.

        Returns:
            StreamEvent: Created immutable event.
        """
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        evt_id = f"evt-{abs(hash(f'{mission_id}-{event_type}-{timestamp_iso}')) % 1000000:06d}"

        event = StreamEvent(
            event_id=evt_id,
            event_type=event_type,
            mission_id=mission_id,
            session_id=session_id,
            stage_name=stage_name,
            agent_id=agent_id,
            agent_role=agent_role,
            task_description=task_description,
            progress_percentage=round(progress_percentage, 1),
            files_created=files_created or [],
            files_modified=files_modified or [],
            token_usage=token_usage or {},
            estimated_cost_usd=round(estimated_cost_usd, 6),
            elapsed_time_ms=round(elapsed_time_ms, 2),
            estimated_remaining_ms=round(estimated_remaining_ms, 2),
            quality_score=round(quality_score, 2),
            production_ready=production_ready,
            message=message,
            payload=payload or {},
            timestamp=timestamp_iso,
        )

        with self._lock:
            self._events.append(event)
            listeners_snapshot = list(self._listeners.values())

        # Notify listeners
        for listener in listeners_snapshot:
            try:
                listener(event)
            except Exception:
                pass  # Presentation adapter failures must never crash execution

        # Optional TraceStorage persistence
        if self._trace_storage is not None:
            try:
                self._trace_storage.append_trace(mission_id, [event.model_dump(mode="json")])
            except Exception:
                pass

        return event

    def get_history(self, mission_id: Optional[str] = None) -> List[StreamEvent]:
        """Retrieve recorded stream event history.

        Args:
            mission_id: Optional mission ID filter.

        Returns:
            List[StreamEvent]: List of matching stream events.
        """
        with self._lock:
            if mission_id is None:
                return list(self._events)
            return [e for e in self._events if e.mission_id == mission_id]
