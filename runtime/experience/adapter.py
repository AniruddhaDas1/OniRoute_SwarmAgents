"""Presentation Adapter Engine for Phase P6.D2.

Exposes a presentation-agnostic event transformation layer supporting CLI,
VS Code Extension, Web UI, and API channels without embedding UI rendering logic inside Runtime.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from runtime.experience.models import StreamEvent
from runtime.experience.stream import ExecutionEventStream


class PresentationAdapter:
    """Presentation Adapter for Phase P6.D2."""

    def __init__(self, stream: Optional[ExecutionEventStream] = None) -> None:
        """Initialize PresentationAdapter.

        Args:
            stream: Optional ExecutionEventStream to connect with.
        """
        self._stream = stream
        self._subscription_id: Optional[str] = None
        if self._stream is not None:
            self.connect_stream(self._stream)

    def connect_stream(self, stream: ExecutionEventStream) -> None:
        """Connect adapter to an active ExecutionEventStream.

        Args:
            stream: Target ExecutionEventStream.
        """
        if self._stream is not None and self._subscription_id is not None:
            self._stream.unsubscribe(self._subscription_id)
        self._stream = stream
        self._subscription_id = self._stream.subscribe(self._on_event_received)

    def _on_event_received(self, event: StreamEvent) -> None:
        """Internal callback when event is received from stream."""
        pass

    def format_event_for_channel(self, event: StreamEvent, target_channel: str = "cli") -> Dict[str, Any]:
        """Format StreamEvent into a channel-specific payload dictionary.

        Args:
            event: StreamEvent contract.
            target_channel: Target channel identifier ("cli", "vscode", "web", "api").

        Returns:
            Dict[str, Any]: Formatted data dictionary.
        """
        base = event.model_dump(mode="json")
        ch = target_channel.lower()

        if ch == "vscode":
            return {
                "type": "oniroute.event",
                "channel": "vscode-extension",
                "id": event.event_id,
                "eventType": event.event_type,
                "missionId": event.mission_id,
                "stage": event.stage_name,
                "agentRole": event.agent_role,
                "progress": event.progress_percentage,
                "message": event.message,
                "raw": base,
            }
        elif ch == "web":
            return {
                "event": event.event_type,
                "id": event.event_id,
                "data": {
                    "missionId": event.mission_id,
                    "stage": event.stage_name,
                    "agent": event.agent_role or event.agent_id,
                    "task": event.task_description,
                    "progress": event.progress_percentage,
                    "filesCreated": event.files_created,
                    "filesModified": event.files_modified,
                    "qualityScore": event.quality_score,
                    "productionReady": event.production_ready,
                    "message": event.message,
                },
                "timestamp": event.timestamp,
            }
        elif ch == "api":
            return {
                "status": "success",
                "channel": "rest-api",
                "payload": base,
            }
        else:  # "cli" or default
            return {
                "channel": "cli-renderer",
                "title": f"[{event.stage_name}] {event.event_type}",
                "status_line": f"▶ {event.agent_role or 'System'}: {event.message or event.task_description}",
                "progress": event.progress_percentage,
                "raw": base,
            }

    def broadcast_to_adapters(self, event: StreamEvent) -> Dict[str, Dict[str, Any]]:
        """Format and broadcast StreamEvent across all supported channels.

        Args:
            event: StreamEvent contract.

        Returns:
            Dict[str, Dict[str, Any]]: Map of channel name to formatted payload.
        """
        return {
            "cli": self.format_event_for_channel(event, "cli"),
            "vscode": self.format_event_for_channel(event, "vscode"),
            "web": self.format_event_for_channel(event, "web"),
            "api": self.format_event_for_channel(event, "api"),
        }
