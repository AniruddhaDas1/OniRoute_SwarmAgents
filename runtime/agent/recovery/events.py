"""Recovery-specific event types for the OniRoute Runtime (ACR-006 Phase R4).

Extends the existing RuntimeEventType without modifying the frozen models.py.
These event types are appended to AgentSession.events via the existing
EventRecorder and SessionManager infrastructure.
"""

from __future__ import annotations

from enum import Enum


class RecoveryEventType(str, Enum):
    """Canonical recovery event types.

    These complement the existing RuntimeEventType values and are stored
    as string literals in ExecutionEvent.event_type so that the frozen
    RuntimeEventType enum remains unmodified.
    """

    EXECUTION_PAUSED = "execution_paused"
    """Session execution was paused, persisting reason, timestamp, and actor."""

    EXECUTION_RESUMED = "execution_resumed"
    """Session execution resumed from WAITING back to RUNNING."""

    REVIEW_REQUESTED = "review_requested"
    """Human review was requested for one or more artifacts."""

    REVIEW_APPROVED = "review_approved"
    """Human reviewer approved the session — execution may continue."""

    REVIEW_REJECTED = "review_rejected"
    """Human reviewer rejected the session — execution is failed."""

    REVIEW_CHANGES_REQUESTED = "review_changes_requested"
    """Human reviewer requested changes before approving."""

    RETRY_STARTED = "retry_started"
    """A retry attempt was initiated."""

    RETRY_COMPLETED = "retry_completed"
    """A retry attempt completed (outcome: 'success' or 'failure')."""

    RECOVERY_COMPLETED = "recovery_completed"
    """The full recovery cycle completed — session is either recovered or permanently failed."""
