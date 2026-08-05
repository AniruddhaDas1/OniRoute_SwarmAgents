"""RecoveryOrchestrator for the OniRoute Recovery Engine (ACR-006 Phase R4).

Coordinates the full Pause → Resume → Review → Retry → Recover lifecycle.

Pipeline
--------
  RUNNING → WAITING  (pause)
  WAITING → RUNNING  (resume)
  RUNNING → REVIEW   (review requested)
  REVIEW  → RUNNING  (review approved)
  REVIEW  → FAILED   (review rejected)
  RUNNING → FAILED   (retry exhausted)
  RUNNING → COMPLETED (recovered)

Does NOT modify Mission, Organization, Workspace, or ExecutionBlueprint.
Reuses SessionManager, EventRecorder, and existing UMAL / InvocationLayer.

Note on event storage
---------------------
The frozen ``ExecutionEvent.event_type`` field accepts only the values defined
in ``RuntimeEventType``.  Rather than modifying that frozen enum, recovery
events are stored in a dedicated ``RecoveryEvent`` list managed by
``RecoveryOrchestrator``.  This preserves the frozen architecture while
providing a complete, immutable recovery audit trail.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from runtime.agent.models import (
    AgentSession,
    RuntimeState,
)
from runtime.agent.session_manager import SessionManager

from .classifier import FailureClassification
from .events import RecoveryEventType
from .models import (
    PauseRecord,
    RecoveryMetrics,
    RecoveryReport,
    RetryPolicy,
    ReviewDecision,
)
from .retry import RetryManager
from .review import RuntimeReviewEngine


@dataclass(frozen=True)
class RecoveryEvent:
    """Immutable recovery-specific event record.

    Stored by ``RecoveryOrchestrator`` independently of the frozen
    ``ExecutionEvent`` / ``RuntimeEventType`` infrastructure.
    """

    event_id: str
    event_type: str          # RecoveryEventType value string
    session_id: str
    description: str
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RecoveryOrchestrator:
    """Deterministic coordinator for runtime pause, resume, review, retry, and recovery.

    The orchestrator is session-scoped: one instance per blueprint execution
    (or shared across sessions via the CLI layer).

    Parameters
    ----------
    retry_policy:
        Optional custom retry policy. Defaults to RetryPolicy().
    session_manager:
        Optional SessionManager override (defaults to a fresh instance).
    """

    def __init__(
        self,
        retry_policy: RetryPolicy | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        self._session_manager = session_manager or SessionManager()
        self._retry_manager = RetryManager(retry_policy)
        self._review_engine = RuntimeReviewEngine()

        # Immutable evidence trails (built up during lifecycle)
        self._pause_records: list[PauseRecord] = []
        self._failure_classifications: list[FailureClassification] = []
        # Recovery events are stored separately from AgentSession.events
        # because ExecutionEvent.event_type is constrained to the frozen RuntimeEventType enum.
        self._recovery_events: list[RecoveryEvent] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def retry_manager(self) -> RetryManager:
        return self._retry_manager

    @property
    def review_engine(self) -> RuntimeReviewEngine:
        return self._review_engine

    @property
    def recovery_events(self) -> tuple["RecoveryEvent", ...]:
        """Immutable snapshot of all recovery-specific events emitted."""
        return tuple(self._recovery_events)

    def get_session_events(self, session_id: str) -> tuple["RecoveryEvent", ...]:
        """Return all recovery events for a specific session."""
        return tuple(e for e in self._recovery_events if e.session_id == session_id)

    def get_session_event_types(self, session_id: str) -> list[str]:
        """Return the event_type strings for all recovery events for *session_id*."""
        return [e.event_type for e in self._recovery_events if e.session_id == session_id]

    # ------------------------------------------------------------------
    # Pause / Resume
    # ------------------------------------------------------------------

    def pause(
        self,
        session: AgentSession,
        reason: str,
        actor: str = "runtime",
        evidence: dict | None = None,
    ) -> tuple[AgentSession, PauseRecord]:
        """Transition *session* from RUNNING → WAITING and record a PauseRecord.

        Parameters
        ----------
        session:
            The currently RUNNING AgentSession.
        reason:
            Human-readable pause reason.
        actor:
            Who initiated the pause ('runtime', 'user', 'governance').
        evidence:
            Additional contextual evidence for the pause.

        Returns
        -------
        tuple[AgentSession, PauseRecord]
            Updated session and the immutable pause record.
        """
        # State guard — only RUNNING sessions can be paused
        if session.state != RuntimeState.RUNNING:
            raise ValueError(
                f"Cannot pause session {session.session_id}: "
                f"expected RUNNING, got {session.state.value}."
            )

        pause_id = f"pause-{session.session_id}-{uuid.uuid4().hex[:8]}"
        record = PauseRecord(
            pause_id=pause_id,
            session_id=session.session_id,
            reason=reason,
            actor=actor,
            evidence=evidence or {},
            paused_at=datetime.now(timezone.utc).isoformat(),
        )
        self._pause_records.append(record)

        # Transition RUNNING → WAITING
        session = self._session_manager.transition_state(session, RuntimeState.WAITING)

        # Emit EXECUTION_PAUSED event
        self._emit_recovery_event(
            session,
            RecoveryEventType.EXECUTION_PAUSED.value,
            f"Session paused by '{actor}': {reason}",
            {
                "pause_id": pause_id,
                "actor": actor,
                "reason": reason,
            },
        )

        return session, record

    def resume(
        self,
        session: AgentSession,
        pause_id: str | None = None,
    ) -> tuple[AgentSession, PauseRecord | None]:
        """Transition *session* from WAITING → RUNNING and update the matching PauseRecord.

        Parameters
        ----------
        session:
            The WAITING AgentSession to resume.
        pause_id:
            Optional pause record ID to mark as resumed. If omitted, the most
            recent open pause record for the session is updated.

        Returns
        -------
        tuple[AgentSession, PauseRecord | None]
            Updated session and the (updated) pause record, or None if not found.
        """
        if session.state != RuntimeState.WAITING:
            raise ValueError(
                f"Cannot resume session {session.session_id}: "
                f"expected WAITING, got {session.state.value}."
            )

        # Find the pause record to close
        closed_record: PauseRecord | None = None
        resumed_at = datetime.now(timezone.utc).isoformat()

        for i, record in enumerate(self._pause_records):
            if record.session_id == session.session_id and record.resumed_at is None:
                if pause_id is None or record.pause_id == pause_id:
                    updated = PauseRecord(
                        pause_id=record.pause_id,
                        session_id=record.session_id,
                        reason=record.reason,
                        actor=record.actor,
                        evidence=dict(record.evidence),
                        paused_at=record.paused_at,
                        resumed_at=resumed_at,
                    )
                    self._pause_records[i] = updated
                    closed_record = updated
                    break

        # Transition WAITING → RUNNING
        session = self._session_manager.transition_state(session, RuntimeState.RUNNING)

        # Emit EXECUTION_RESUMED event
        self._emit_recovery_event(
            session,
            RecoveryEventType.EXECUTION_RESUMED.value,
            f"Session {session.session_id} resumed from WAITING.",
            {
                "pause_id": closed_record.pause_id if closed_record else None,
                "resumed_at": resumed_at,
            },
        )

        return session, closed_record

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    def request_review(
        self,
        session: AgentSession,
        reason: str = "Artifact requires human approval.",
    ) -> AgentSession:
        """Transition *session* to REVIEW state and register a review request.

        Returns the updated session in REVIEW state.
        """
        # Transition RUNNING → REVIEW
        session = self._session_manager.transition_state(session, RuntimeState.REVIEW)

        # Create review record via engine
        self._review_engine.request_review(
            session,
            reason=reason,
            event_emitter=self._emit_recovery_event,
        )

        return session

    def apply_review_decision(
        self,
        session: AgentSession,
        review_id: str,
        decision: ReviewDecision,
        actor: str,
        notes: str = "",
    ) -> AgentSession:
        """Submit a review decision and transition the session accordingly.

        APPROVE        → REVIEW → RUNNING
        REJECT         → REVIEW → FAILED
        REQUEST_CHANGES → REVIEW → WAITING

        Returns the updated session.
        """
        # Submit to review engine
        self._review_engine.submit_decision(
            review_id=review_id,
            decision=decision,
            actor=actor,
            notes=notes,
            session=session,
            event_emitter=self._emit_recovery_event,
        )

        if decision == ReviewDecision.APPROVE:
            session = self._session_manager.transition_state(session, RuntimeState.RUNNING)
        elif decision == ReviewDecision.REJECT:
            session = self._session_manager.transition_state(session, RuntimeState.FAILED)
        elif decision == ReviewDecision.REQUEST_CHANGES:
            # REVIEW → WAITING is not in the frozen transition DAG.
            # REQUEST_CHANGES means the work is rejected pending corrections;
            # transition to FAILED so the caller can re-submit after revisions.
            session = self._session_manager.transition_state(session, RuntimeState.FAILED)

        return session

    # ------------------------------------------------------------------
    # Retry
    # ------------------------------------------------------------------

    def attempt_recovery(
        self,
        session: AgentSession,
        classification: FailureClassification,
        execution_fn: Callable[[AgentSession], object],
    ) -> tuple[AgentSession, bool]:
        """Attempt a retry of *session* if eligible, executing *execution_fn*.

        Parameters
        ----------
        session:
            The FAILED AgentSession to recover.
        classification:
            The FailureClassification for the triggering failure.
        execution_fn:
            Callable that accepts an AgentSession and executes it, returning
            any result. May raise exceptions.

        Returns
        -------
        tuple[AgentSession, bool]
            Updated session and True if recovery succeeded, False otherwise.
        """
        self._failure_classifications.append(classification)

        if not self._retry_manager.can_retry(session.session_id, classification):
            # Non-retryable — emit RECOVERY_COMPLETED (failed) and return
            self._emit_recovery_event(
                session,
                RecoveryEventType.RECOVERY_COMPLETED.value,
                f"Recovery not possible: {classification.reason}",
                {
                    "category": classification.category.value,
                    "retryable": False,
                    "reason": classification.reason,
                },
            )
            return session, False

        # Start retry
        retry_record = self._retry_manager.start_retry(session.session_id, classification)

        self._emit_recovery_event(
            session,
            RecoveryEventType.RETRY_STARTED.value,
            f"Retry attempt {retry_record.attempt_number} for session {session.session_id}.",
            {
                "retry_id": retry_record.retry_id,
                "attempt": retry_record.attempt_number,
                "delay_seconds": retry_record.delay_seconds,
                "category": classification.category.value,
            },
        )

        # Transition session to RUNNING for retry (from FAILED → READY → RUNNING
        # requires re-initialization; here we record evidence only — the caller
        # supplies a fresh session or the same session depending on their design.
        # We track the retry outcome via the record.)
        try:
            execution_fn(session)
            self._retry_manager.complete_retry(retry_record.retry_id, "success")
            self._emit_recovery_event(
                session,
                RecoveryEventType.RETRY_COMPLETED.value,
                f"Retry {retry_record.attempt_number} succeeded.",
                {"retry_id": retry_record.retry_id, "outcome": "success"},
            )
            self._emit_recovery_event(
                session,
                RecoveryEventType.RECOVERY_COMPLETED.value,
                f"Session {session.session_id} recovered successfully.",
                {"retry_id": retry_record.retry_id},
            )
            return session, True

        except Exception as exc:  # noqa: BLE001
            self._retry_manager.complete_retry(retry_record.retry_id, "failure")
            self._emit_recovery_event(
                session,
                RecoveryEventType.RETRY_COMPLETED.value,
                f"Retry {retry_record.attempt_number} failed: {exc}",
                {"retry_id": retry_record.retry_id, "outcome": "failure", "error": str(exc)},
            )
            return session, False

    # ------------------------------------------------------------------
    # Recovery Report
    # ------------------------------------------------------------------

    def generate_report(
        self,
        session: AgentSession,
        blueprint_id: str,
        mission_id: str,
    ) -> RecoveryReport:
        """Generate an immutable RecoveryReport for *session*.

        Captures all failures, retries, pauses, reviews, and aggregate metrics.
        """
        retry_records = self._retry_manager.records
        retry_metrics = self._retry_manager.metrics

        all_reviews = self._review_engine.all_reviews
        review_outcomes = [r.outcome for r in all_reviews if r.outcome is not None]
        approved = sum(1 for o in review_outcomes if o.decision == ReviewDecision.APPROVE)
        rejected = sum(1 for o in review_outcomes if o.decision == ReviewDecision.REJECT)

        pauses = [r for r in self._pause_records if r.session_id == session.session_id]
        resumes = sum(1 for r in pauses if r.resumed_at is not None)

        # Determine recovery status
        if session.state == RuntimeState.COMPLETED:
            recovery_status = "recovered"
        elif session.state == RuntimeState.FAILED:
            recovery_status = "failed"
        elif session.state in (RuntimeState.REVIEW, RuntimeState.WAITING):
            recovery_status = "review_required"
        else:
            recovery_status = "pending"

        successful_retries = retry_metrics["successful_retries"]
        failed_retries = retry_metrics["failed_retries"]
        total_retries = retry_metrics["total_retries"]

        metrics = RecoveryMetrics(
            total_failures=len(self._failure_classifications),
            total_retries=total_retries,
            successful_retries=successful_retries,
            failed_retries=failed_retries,
            total_pauses=len(pauses),
            total_resumes=resumes,
            total_reviews_requested=len(all_reviews),
            total_reviews_approved=approved,
            total_reviews_rejected=rejected,
            total_recoveries=successful_retries,
        )

        summary_parts = [
            f"Session: {session.session_id}",
            f"Status: {recovery_status}",
            f"Failures: {metrics.total_failures}",
            f"Retries: {total_retries} (success={successful_retries}, failed={failed_retries})",
            f"Pauses: {metrics.total_pauses}",
            f"Reviews: {len(all_reviews)} (approved={approved}, rejected={rejected})",
        ]

        return RecoveryReport(
            report_id=f"recovery-report-{session.session_id}-{uuid.uuid4().hex[:8]}",
            session_id=session.session_id,
            blueprint_id=blueprint_id,
            mission_id=mission_id,
            failures=[fc.to_dict() for fc in self._failure_classifications],
            retries=list(retry_records),
            pauses=pauses,
            review_requests=list(all_reviews),
            review_outcomes=list(review_outcomes),
            metrics=metrics,
            recovery_status=recovery_status,
            summary=". ".join(summary_parts) + ".",
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit_recovery_event(
        self,
        session: AgentSession,
        event_type_str: str,
        description: str,
        payload: dict | None = None,
    ) -> None:
        """Store a recovery event in the orchestrator's own event list.

        Recovery events use ``RecoveryEvent`` (not ``ExecutionEvent``) because
        ``ExecutionEvent.event_type`` is constrained to the frozen
        ``RuntimeEventType`` enum.  Storing recovery events separately
        preserves the frozen architecture without any modification.
        """
        event = RecoveryEvent(
            event_id=f"ev-rec-{event_type_str}-{session.session_id}-{uuid.uuid4().hex[:6]}",
            event_type=event_type_str,
            session_id=session.session_id,
            description=description,
            payload=payload or {},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._recovery_events.append(event)
