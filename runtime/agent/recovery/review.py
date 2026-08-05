"""RuntimeReviewEngine for the OniRoute Recovery Engine (ACR-006 Phase R5).

Determines whether artifacts require human review, pauses the session,
emits REVIEW_REQUESTED, and awaits a decision (APPROVE / REJECT / REQUEST_CHANGES).

As of R5, review eligibility is determined by a declarative ``ReviewPolicy``
rather than a hardcoded set of artifact types.  The default policy preserves
R4 behavior.  Pass a different policy to override review rules without modifying
the engine.

No AI. Pure deterministic human-in-the-loop gate.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Callable

from runtime.agent.models import AgentSession, ArtifactRecord, RuntimeState

from .events import RecoveryEventType
from .models import (
    ReviewDecision,
    ReviewOutcome,
    ReviewRecord,
)
from .policy import DefaultReviewPolicy, ReviewPolicy


# ---------------------------------------------------------------------------
# RuntimeReviewEngine
# ---------------------------------------------------------------------------

class RuntimeReviewEngine:
    """Deterministic human review gate.

    Review eligibility is determined by a declarative ``ReviewPolicy``.
    The default policy preserves R4 behavior (schema, config, binary, review
    artifact types require human approval).

    The engine:
    1. Consults the policy to decide whether review is needed.
    2. If required, records a ReviewRecord and emits REVIEW_REQUESTED.
    3. Awaits a decision delivered via ``submit_decision()``.
    4. On APPROVE  → records ReviewOutcome, emits REVIEW_APPROVED.
    5. On REJECT   → records ReviewOutcome, emits REVIEW_REJECTED.
    6. On REQUEST_CHANGES → records ReviewOutcome, emits REVIEW_CHANGES_REQUESTED.

    Sessions are not modified directly; callers (RecoveryOrchestrator) apply
    state transitions via the existing SessionManager.
    """

    def __init__(self, policy: ReviewPolicy | None = None) -> None:
        self._policy: ReviewPolicy = policy or DefaultReviewPolicy()
        self._pending_reviews: dict[str, ReviewRecord] = {}
        """review_id → ReviewRecord for open reviews."""

        self._completed_reviews: list[ReviewRecord] = []
        """Closed review records (immutable audit trail)."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def policy(self) -> ReviewPolicy:
        """The active review policy."""
        return self._policy

    @property
    def pending_review_ids(self) -> tuple[str, ...]:
        """IDs of all open review requests."""
        return tuple(self._pending_reviews)

    @property
    def all_reviews(self) -> tuple[ReviewRecord, ...]:
        """All review records (pending + completed)."""
        return tuple(self._pending_reviews.values()) + tuple(self._completed_reviews)

    def needs_review(self, session: AgentSession) -> bool:
        """Return True if the session has any artifacts that require review per policy."""
        return any(self._policy.requires_review(art) for art in session.artifacts)

    def request_review(
        self,
        session: AgentSession,
        reason: str = "Artifact requires human approval before proceeding.",
        event_emitter: Callable | None = None,
    ) -> ReviewRecord:
        """Create and register a ReviewRecord for *session*.

        Emits a REVIEW_REQUESTED event via *event_emitter* if provided.

        Parameters
        ----------
        session:
            The AgentSession whose artifacts are under review.
        reason:
            Human-readable description of why review is required.
        event_emitter:
            Optional callable ``(session, event_type_str, description, payload) -> None``
            used to append the event to the session.

        Returns
        -------
        ReviewRecord
            The pending review record.
        """
        review_id = f"rev-{session.session_id}-{uuid.uuid4().hex[:8]}"
        artifact_ids = [
            art.artifact_id
            for art in session.artifacts
            if self._policy.requires_review(art)
        ]

        record = ReviewRecord(
            review_id=review_id,
            session_id=session.session_id,
            member_id=session.member_id,
            review_reason=reason,
            artifacts_under_review=artifact_ids,
            evidence={
                "session_id": session.session_id,
                "role_title": session.role_title,
                "artifact_count": len(artifact_ids),
                "artifact_ids": artifact_ids,
            },
            requested_at=datetime.now(timezone.utc).isoformat(),
        )
        self._pending_reviews[review_id] = record

        if event_emitter is not None:
            event_emitter(
                session,
                RecoveryEventType.REVIEW_REQUESTED.value,
                f"Human review requested for session {session.session_id}: {reason}",
                {
                    "review_id": review_id,
                    "artifact_ids": artifact_ids,
                    "reason": reason,
                },
            )

        return record

    def submit_decision(
        self,
        review_id: str,
        decision: ReviewDecision,
        actor: str,
        notes: str = "",
        session: AgentSession | None = None,
        event_emitter: Callable | None = None,
    ) -> ReviewRecord:
        """Record a human decision for the pending review identified by *review_id*.

        Parameters
        ----------
        review_id:
            The pending ReviewRecord identifier.
        decision:
            APPROVE, REJECT, or REQUEST_CHANGES.
        actor:
            Identity of the human reviewer (CLI user, operator, etc.).
        notes:
            Optional reviewer notes.
        session:
            Optional session for event emission.
        event_emitter:
            Optional callable for appending the review outcome event.

        Returns
        -------
        ReviewRecord
            The closed review record with an attached ReviewOutcome.

        Raises
        ------
        KeyError
            If *review_id* is not a pending review.
        """
        if review_id not in self._pending_reviews:
            raise KeyError(f"No pending review found for ID '{review_id}'.")

        original = self._pending_reviews.pop(review_id)
        outcome = ReviewOutcome(
            review_id=review_id,
            session_id=original.session_id,
            decision=decision,
            actor=actor,
            notes=notes,
            decided_at=datetime.now(timezone.utc).isoformat(),
        )

        # Pydantic frozen model — reconstruct with outcome attached
        closed = ReviewRecord(
            review_id=original.review_id,
            session_id=original.session_id,
            member_id=original.member_id,
            review_reason=original.review_reason,
            artifacts_under_review=list(original.artifacts_under_review),
            evidence=dict(original.evidence),
            requested_at=original.requested_at,
            outcome=outcome,
        )
        self._completed_reviews.append(closed)

        if event_emitter is not None and session is not None:
            event_type_map = {
                ReviewDecision.APPROVE: RecoveryEventType.REVIEW_APPROVED.value,
                ReviewDecision.REJECT: RecoveryEventType.REVIEW_REJECTED.value,
                ReviewDecision.REQUEST_CHANGES: RecoveryEventType.REVIEW_CHANGES_REQUESTED.value,
            }
            event_emitter(
                session,
                event_type_map[decision],
                f"Review {decision.value} by '{actor}' for session {original.session_id}.",
                {
                    "review_id": review_id,
                    "decision": decision.value,
                    "actor": actor,
                    "notes": notes,
                },
            )

        return closed

    def get_review(self, review_id: str) -> ReviewRecord | None:
        """Return a pending or completed ReviewRecord by ID, or None."""
        if review_id in self._pending_reviews:
            return self._pending_reviews[review_id]
        for record in self._completed_reviews:
            if record.review_id == review_id:
                return record
        return None

    def completed_reviews(self) -> tuple[ReviewRecord, ...]:
        """Return all closed review records."""
        return tuple(self._completed_reviews)
