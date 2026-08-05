"""Handoff Manager for Engineering Collaboration (ACR-007 Phase C3).

Implements HandoffManagerContract to coordinate artifact and task handoffs between producer
and consumer AgentSession instances.

Supports handoff lifecycle:
  PENDING → ACCEPTED → COMPLETED (or REJECTED, CANCELLED)

Every transition is recorded on the CollaborationTimeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .contracts import HandoffManagerContract
from .models import ArtifactReference, Handoff, HandoffStatus, TimelineEventType
from .timeline import CollaborationTimeline


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class HandoffManager(HandoffManagerContract):
    """Concrete implementation of HandoffManagerContract.

    Manages handoff creation, acceptance, rejection, completion, cancellation, and validation.
    """

    def __init__(self, timeline: CollaborationTimeline | None = None) -> None:
        self._timeline = timeline or CollaborationTimeline()

        self._handoffs: dict[str, Handoff] = {}
        """handoff_id → Handoff"""

        self._session_handoffs: dict[str, list[str]] = {}
        """session_id → list of handoff_ids (as producer or consumer)"""

    @property
    def timeline(self) -> CollaborationTimeline:
        return self._timeline

    @property
    def total_handoffs(self) -> int:
        return len(self._handoffs)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_handoff(
        self,
        producer_session_id: str,
        consumer_session_id: str,
        artifact_reference: ArtifactReference,
        reason: str,
        evidence: dict | None = None,
    ) -> Handoff:
        """Create a new handoff in PENDING state."""
        if not producer_session_id or not consumer_session_id:
            raise ValueError("Producer and Consumer session IDs must be non-empty.")

        if producer_session_id == consumer_session_id:
            raise ValueError("Producer and Consumer session IDs cannot be identical.")

        # Validate that artifact reference belongs to producer
        if artifact_reference.owner_session_id and artifact_reference.owner_session_id != producer_session_id:
            # Advisory warning in evidence
            evidence = dict(evidence or {})
            evidence["ownership_warning"] = (
                f"Producer '{producer_session_id}' differs from artifact owner '{artifact_reference.owner_session_id}'"
            )

        handoff_id = f"hdf-{uuid.uuid4().hex[:8]}"
        handoff = Handoff(
            handoff_id=handoff_id,
            producer_session_id=producer_session_id,
            consumer_session_id=consumer_session_id,
            artifact_reference=artifact_reference,
            reason=reason,
            evidence=evidence or {},
            status=HandoffStatus.PENDING,
            timestamp=_utcnow(),
        )

        self._handoffs[handoff_id] = handoff
        self._session_handoffs.setdefault(producer_session_id, []).append(handoff_id)
        self._session_handoffs.setdefault(consumer_session_id, []).append(handoff_id)

        self._timeline.record_event(
            event_type=TimelineEventType.HANDOFF_CREATED,
            session_id=producer_session_id,
            description=(
                f"Handoff created: '{artifact_reference.artifact_id}' from "
                f"'{producer_session_id}' to '{consumer_session_id}' ({handoff_id})"
            ),
            payload={
                "handoff_id": handoff_id,
                "producer_session_id": producer_session_id,
                "consumer_session_id": consumer_session_id,
                "reference_id": artifact_reference.reference_id,
                "artifact_id": artifact_reference.artifact_id,
                "reason": reason,
            },
        )
        return handoff

    def initiate_handoff(
        self,
        producer_session_id: str,
        consumer_session_id: str,
        artifact_reference: ArtifactReference,
        reason: str,
        evidence: dict | None = None,
    ) -> Handoff:
        """Implement HandoffManagerContract.initiate_handoff."""
        return self.create_handoff(
            producer_session_id=producer_session_id,
            consumer_session_id=consumer_session_id,
            artifact_reference=artifact_reference,
            reason=reason,
            evidence=evidence,
        )

    def accept_handoff(
        self,
        handoff_id: str,
        consumer_session_id: str,
        evidence: dict | None = None,
    ) -> Handoff:
        """Accept a pending handoff."""
        handoff = self.get_handoff(handoff_id)
        if handoff.status != HandoffStatus.PENDING:
            raise ValueError(f"Handoff '{handoff_id}' is not PENDING (current: {handoff.status.value}).")

        if handoff.consumer_session_id != consumer_session_id:
            raise ValueError(
                f"Session '{consumer_session_id}' is not the designated consumer for handoff '{handoff_id}'."
            )

        merged_evidence = dict(handoff.evidence)
        if evidence:
            merged_evidence.update(evidence)

        updated = Handoff(
            handoff_id=handoff.handoff_id,
            producer_session_id=handoff.producer_session_id,
            consumer_session_id=handoff.consumer_session_id,
            artifact_reference=handoff.artifact_reference,
            reason=handoff.reason,
            evidence=merged_evidence,
            status=HandoffStatus.ACCEPTED,
            timestamp=handoff.timestamp,
        )
        self._handoffs[handoff_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.HANDOFF_ACCEPTED,
            session_id=consumer_session_id,
            description=f"Handoff '{handoff_id}' accepted by consumer '{consumer_session_id}'.",
            payload={"handoff_id": handoff_id, "consumer_session_id": consumer_session_id},
        )
        return updated

    def reject_handoff(
        self,
        handoff_id: str,
        consumer_session_id: str,
        reason: str,
        evidence: dict | None = None,
    ) -> Handoff:
        """Reject a pending handoff."""
        handoff = self.get_handoff(handoff_id)
        if handoff.status != HandoffStatus.PENDING:
            raise ValueError(f"Handoff '{handoff_id}' is not PENDING (current: {handoff.status.value}).")

        if handoff.consumer_session_id != consumer_session_id:
            raise ValueError(
                f"Session '{consumer_session_id}' is not the designated consumer for handoff '{handoff_id}'."
            )

        merged_evidence = dict(handoff.evidence)
        merged_evidence["rejection_reason"] = reason
        if evidence:
            merged_evidence.update(evidence)

        updated = Handoff(
            handoff_id=handoff.handoff_id,
            producer_session_id=handoff.producer_session_id,
            consumer_session_id=handoff.consumer_session_id,
            artifact_reference=handoff.artifact_reference,
            reason=handoff.reason,
            evidence=merged_evidence,
            status=HandoffStatus.REJECTED,
            timestamp=handoff.timestamp,
            rejected_at=_utcnow(),
        )
        self._handoffs[handoff_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.HANDOFF_REJECTED,
            session_id=consumer_session_id,
            description=f"Handoff '{handoff_id}' rejected by '{consumer_session_id}': {reason}",
            payload={"handoff_id": handoff_id, "consumer_session_id": consumer_session_id, "rejection_reason": reason},
        )
        return updated

    def complete_handoff(
        self,
        handoff_id: str,
        consumer_session_id: str,
        evidence: dict | None = None,
    ) -> Handoff:
        """Complete an accepted handoff."""
        handoff = self.get_handoff(handoff_id)
        if handoff.status not in (HandoffStatus.ACCEPTED, HandoffStatus.PENDING):
            raise ValueError(
                f"Handoff '{handoff_id}' cannot be completed from state {handoff.status.value}."
            )

        if handoff.consumer_session_id != consumer_session_id:
            raise ValueError(
                f"Session '{consumer_session_id}' is not the consumer for handoff '{handoff_id}'."
            )

        merged_evidence = dict(handoff.evidence)
        if evidence:
            merged_evidence.update(evidence)

        completed_at = _utcnow()
        updated = Handoff(
            handoff_id=handoff.handoff_id,
            producer_session_id=handoff.producer_session_id,
            consumer_session_id=handoff.consumer_session_id,
            artifact_reference=handoff.artifact_reference,
            reason=handoff.reason,
            evidence=merged_evidence,
            status=HandoffStatus.COMPLETED,
            timestamp=handoff.timestamp,
            completed_at=completed_at,
        )
        self._handoffs[handoff_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.HANDOFF_COMPLETED,
            session_id=consumer_session_id,
            description=f"Handoff '{handoff_id}' completed by '{consumer_session_id}'.",
            payload={"handoff_id": handoff_id, "consumer_session_id": consumer_session_id, "completed_at": completed_at},
        )
        return updated

    def cancel_handoff(
        self,
        handoff_id: str,
        producer_session_id: str,
        reason: str,
        evidence: dict | None = None,
    ) -> Handoff:
        """Cancel a pending handoff (by producer)."""
        handoff = self.get_handoff(handoff_id)
        if handoff.status != HandoffStatus.PENDING:
            raise ValueError(f"Handoff '{handoff_id}' is not PENDING (current: {handoff.status.value}).")

        if handoff.producer_session_id != producer_session_id:
            raise ValueError(
                f"Session '{producer_session_id}' is not the producer for handoff '{handoff_id}'."
            )

        merged_evidence = dict(handoff.evidence)
        merged_evidence["cancellation_reason"] = reason
        if evidence:
            merged_evidence.update(evidence)

        cancelled_at = _utcnow()
        updated = Handoff(
            handoff_id=handoff.handoff_id,
            producer_session_id=handoff.producer_session_id,
            consumer_session_id=handoff.consumer_session_id,
            artifact_reference=handoff.artifact_reference,
            reason=handoff.reason,
            evidence=merged_evidence,
            status=HandoffStatus.CANCELLED,
            timestamp=handoff.timestamp,
            cancelled_at=cancelled_at,
        )
        self._handoffs[handoff_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.HANDOFF_CANCELLED,
            session_id=producer_session_id,
            description=f"Handoff '{handoff_id}' cancelled by producer '{producer_session_id}': {reason}",
            payload={"handoff_id": handoff_id, "producer_session_id": producer_session_id, "cancellation_reason": reason},
        )
        return updated

    def update_handoff_status(self, handoff_id: str, status: HandoffStatus) -> Handoff:
        """Implement HandoffManagerContract.update_handoff_status."""
        handoff = self.get_handoff(handoff_id)
        if status == HandoffStatus.ACCEPTED:
            return self.accept_handoff(handoff_id, handoff.consumer_session_id)
        if status == HandoffStatus.COMPLETED:
            return self.complete_handoff(handoff_id, handoff.consumer_session_id)
        if status == HandoffStatus.REJECTED:
            return self.reject_handoff(handoff_id, handoff.consumer_session_id, reason="Status update")
        if status == HandoffStatus.CANCELLED:
            return self.cancel_handoff(handoff_id, handoff.producer_session_id, reason="Status update")

        raise ValueError(f"Unsupported status transition to '{status.value}' via update_handoff_status.")

    def get_handoff(self, handoff_id: str) -> Handoff:
        """Retrieve a Handoff by ID."""
        if handoff_id not in self._handoffs:
            raise KeyError(f"Handoff '{handoff_id}' not found.")
        return self._handoffs[handoff_id]

    def get_handoffs(self, session_id: str) -> list[Handoff]:
        """Retrieve all handoffs involving a specific AgentSession (as producer or consumer)."""
        h_ids = self._session_handoffs.get(session_id, [])
        return [self._handoffs[hid] for hid in h_ids if hid in self._handoffs]

    def get_all_handoffs(self) -> tuple[Handoff, ...]:
        """Return a tuple of all recorded handoffs."""
        return tuple(self._handoffs.values())
