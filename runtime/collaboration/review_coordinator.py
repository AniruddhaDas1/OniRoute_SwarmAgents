"""Review Coordinator for Engineering Collaboration (ACR-007 Phase C4).

Implements ReviewCoordinatorContract to coordinate inter-agent peer reviews attached
to Conversation Threads and ArtifactReferences.

Review State Machine:
  REQUESTED → IN_PROGRESS → CHANGES_REQUESTED → RESUBMITTED → APPROVED (or REJECTED)

Every transition is recorded on the CollaborationTimeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .contracts import ReviewCoordinatorContract
from .models import (
    ArtifactReference,
    CollaborationReview,
    ReviewRequest,
    ReviewStatus,
    TimelineEventType,
)
from .timeline import CollaborationTimeline


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewCoordinator(ReviewCoordinatorContract):
    """Concrete implementation of ReviewCoordinatorContract.

    Manages peer review lifecycle, comments, requested changes, resubmissions, approvals, and rejections.
    """

    def __init__(self, timeline: CollaborationTimeline | None = None) -> None:
        self._timeline = timeline or CollaborationTimeline()
        self._reviews: dict[str, CollaborationReview] = {}
        """review_id → CollaborationReview"""

        self._reviewer_reviews: dict[str, list[str]] = {}
        """reviewer_session_id → list of review_ids"""

        self._author_reviews: dict[str, list[str]] = {}
        """author_session_id → list of review_ids"""

    @property
    def timeline(self) -> CollaborationTimeline:
        return self._timeline

    @property
    def total_reviews(self) -> int:
        return len(self._reviews)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_review(
        self,
        author_session_id: str,
        reviewer_session_id: str,
        artifact_references: list[ArtifactReference],
        reason: str = "",
        conversation_id: str = "",
        thread_id: str = "",
        evidence: dict | None = None,
    ) -> CollaborationReview:
        """Create a new peer review request in REQUESTED state."""
        if not author_session_id or not reviewer_session_id:
            raise ValueError("Author and Reviewer session IDs must be non-empty.")

        if author_session_id == reviewer_session_id:
            raise ValueError("Author and Reviewer session IDs cannot be identical.")

        review_id = f"rev-{uuid.uuid4().hex[:8]}"
        review = CollaborationReview(
            review_id=review_id,
            conversation_id=conversation_id,
            thread_id=thread_id,
            author_session_id=author_session_id,
            reviewer_session_id=reviewer_session_id,
            artifact_references=list(artifact_references),
            status=ReviewStatus.REQUESTED,
            reason=reason,
            evidence=evidence or {},
            comments=[],
            requested_at=_utcnow(),
        )

        self._reviews[review_id] = review
        self._reviewer_reviews.setdefault(reviewer_session_id, []).append(review_id)
        self._author_reviews.setdefault(author_session_id, []).append(review_id)

        self._timeline.record_event(
            event_type=TimelineEventType.REVIEW_CREATED,
            session_id=author_session_id,
            description=(
                f"Peer review created ({review_id}) for {len(artifact_references)} artifact(s): "
                f"author='{author_session_id}', reviewer='{reviewer_session_id}'"
            ),
            payload={
                "review_id": review_id,
                "author_session_id": author_session_id,
                "reviewer_session_id": reviewer_session_id,
                "conversation_id": conversation_id,
                "thread_id": thread_id,
                "artifact_count": len(artifact_references),
            },
        )
        return review

    def request_peer_review(
        self,
        author_session_id: str,
        reviewer_session_id: str,
        artifact_references: list[ArtifactReference],
        reason: str,
    ) -> ReviewRequest:
        """Implement ReviewCoordinatorContract.request_peer_review."""
        return self.create_review(
            author_session_id=author_session_id,
            reviewer_session_id=reviewer_session_id,
            artifact_references=artifact_references,
            reason=reason,
        )

    def start_review(
        self,
        review_id: str,
        reviewer_session_id: str,
        evidence: dict | None = None,
    ) -> CollaborationReview:
        """Transition review state from REQUESTED to IN_PROGRESS."""
        review = self.get_review(review_id)
        if review.status not in (ReviewStatus.REQUESTED, ReviewStatus.RESUBMITTED):
            raise ValueError(f"Review '{review_id}' cannot be started from state '{review.status.value}'.")

        if review.reviewer_session_id != reviewer_session_id:
            raise ValueError(f"Session '{reviewer_session_id}' is not the assigned reviewer for review '{review_id}'.")

        merged_evidence = dict(review.evidence)
        if evidence:
            merged_evidence.update(evidence)

        started_at = _utcnow()
        updated = CollaborationReview(
            review_id=review.review_id,
            conversation_id=review.conversation_id,
            thread_id=review.thread_id,
            author_session_id=review.author_session_id,
            reviewer_session_id=review.reviewer_session_id,
            artifact_references=review.artifact_references,
            status=ReviewStatus.IN_PROGRESS,
            reason=review.reason,
            evidence=merged_evidence,
            comments=review.comments,
            decision=review.decision,
            requested_at=review.requested_at,
            started_at=started_at,
        )
        self._reviews[review_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.REVIEW_STARTED,
            session_id=reviewer_session_id,
            description=f"Peer review '{review_id}' started by reviewer '{reviewer_session_id}'.",
            payload={"review_id": review_id, "reviewer_session_id": reviewer_session_id, "started_at": started_at},
        )
        return updated

    def request_changes(
        self,
        review_id: str,
        reviewer_session_id: str,
        comments: str | list[str] | list[dict[str, Any]],
        evidence: dict | None = None,
    ) -> CollaborationReview:
        """Transition review state to CHANGES_REQUESTED."""
        review = self.get_review(review_id)
        if review.status not in (ReviewStatus.REQUESTED, ReviewStatus.IN_PROGRESS, ReviewStatus.RESUBMITTED):
            raise ValueError(f"Cannot request changes on review '{review_id}' in state '{review.status.value}'.")

        if review.reviewer_session_id != reviewer_session_id:
            raise ValueError(f"Session '{reviewer_session_id}' is not the reviewer for review '{review_id}'.")

        new_comments = list(review.comments)
        if isinstance(comments, str):
            new_comments.append({"author": reviewer_session_id, "comment": comments, "timestamp": _utcnow()})
        elif isinstance(comments, list):
            for item in comments:
                if isinstance(item, str):
                    new_comments.append({"author": reviewer_session_id, "comment": item, "timestamp": _utcnow()})
                elif isinstance(item, dict):
                    new_comments.append(item)

        merged_evidence = dict(review.evidence)
        if evidence:
            merged_evidence.update(evidence)

        updated = CollaborationReview(
            review_id=review.review_id,
            conversation_id=review.conversation_id,
            thread_id=review.thread_id,
            author_session_id=review.author_session_id,
            reviewer_session_id=review.reviewer_session_id,
            artifact_references=review.artifact_references,
            status=ReviewStatus.CHANGES_REQUESTED,
            reason=review.reason,
            evidence=merged_evidence,
            comments=new_comments,
            decision="changes_requested",
            requested_at=review.requested_at,
            started_at=review.started_at,
        )
        self._reviews[review_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.CHANGES_REQUESTED,
            session_id=reviewer_session_id,
            description=f"Changes requested on review '{review_id}' by reviewer '{reviewer_session_id}'.",
            payload={"review_id": review_id, "reviewer_session_id": reviewer_session_id, "comment_count": len(new_comments)},
        )
        return updated

    def resubmit_review(
        self,
        review_id: str,
        author_session_id: str,
        comments: str = "",
        updated_references: list[ArtifactReference] | None = None,
        evidence: dict | None = None,
    ) -> CollaborationReview:
        """Author resubmits review after making requested changes."""
        review = self.get_review(review_id)
        if review.status != ReviewStatus.CHANGES_REQUESTED:
            raise ValueError(f"Review '{review_id}' is not in CHANGES_REQUESTED state (current: {review.status.value}).")

        if review.author_session_id != author_session_id:
            raise ValueError(f"Session '{author_session_id}' is not the author for review '{review_id}'.")

        new_comments = list(review.comments)
        if comments:
            new_comments.append({"author": author_session_id, "comment": f"Resubmitted: {comments}", "timestamp": _utcnow()})

        merged_evidence = dict(review.evidence)
        if evidence:
            merged_evidence.update(evidence)

        refs = list(updated_references) if updated_references is not None else review.artifact_references

        updated = CollaborationReview(
            review_id=review.review_id,
            conversation_id=review.conversation_id,
            thread_id=review.thread_id,
            author_session_id=review.author_session_id,
            reviewer_session_id=review.reviewer_session_id,
            artifact_references=refs,
            status=ReviewStatus.RESUBMITTED,
            reason=review.reason,
            evidence=merged_evidence,
            comments=new_comments,
            decision=None,
            requested_at=review.requested_at,
            started_at=review.started_at,
        )
        self._reviews[review_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.REVIEW_CREATED,
            session_id=author_session_id,
            description=f"Peer review '{review_id}' resubmitted by author '{author_session_id}'.",
            payload={"review_id": review_id, "author_session_id": author_session_id, "status": "resubmitted"},
        )
        return updated

    def approve_review(
        self,
        review_id: str,
        reviewer_session_id: str,
        comments: str = "",
        evidence: dict | None = None,
    ) -> CollaborationReview:
        """Approve a peer review request."""
        review = self.get_review(review_id)
        if review.status in (ReviewStatus.APPROVED, ReviewStatus.REJECTED):
            raise ValueError(f"Review '{review_id}' is already finalized ({review.status.value}).")

        if review.reviewer_session_id != reviewer_session_id:
            raise ValueError(f"Session '{reviewer_session_id}' is not the reviewer for review '{review_id}'.")

        new_comments = list(review.comments)
        if comments:
            new_comments.append({"author": reviewer_session_id, "comment": comments, "timestamp": _utcnow()})

        merged_evidence = dict(review.evidence)
        if evidence:
            merged_evidence.update(evidence)

        completed_at = _utcnow()
        updated = CollaborationReview(
            review_id=review.review_id,
            conversation_id=review.conversation_id,
            thread_id=review.thread_id,
            author_session_id=review.author_session_id,
            reviewer_session_id=review.reviewer_session_id,
            artifact_references=review.artifact_references,
            status=ReviewStatus.APPROVED,
            reason=review.reason,
            evidence=merged_evidence,
            comments=new_comments,
            decision="approved",
            requested_at=review.requested_at,
            started_at=review.started_at,
            completed_at=completed_at,
        )
        self._reviews[review_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.REVIEW_APPROVED,
            session_id=reviewer_session_id,
            description=f"Peer review '{review_id}' APPROVED by reviewer '{reviewer_session_id}'.",
            payload={"review_id": review_id, "reviewer_session_id": reviewer_session_id, "completed_at": completed_at},
        )
        return updated

    def reject_review(
        self,
        review_id: str,
        reviewer_session_id: str,
        reason: str = "",
        evidence: dict | None = None,
    ) -> CollaborationReview:
        """Reject a peer review request."""
        review = self.get_review(review_id)
        if review.status in (ReviewStatus.APPROVED, ReviewStatus.REJECTED):
            raise ValueError(f"Review '{review_id}' is already finalized ({review.status.value}).")

        if review.reviewer_session_id != reviewer_session_id:
            raise ValueError(f"Session '{reviewer_session_id}' is not the reviewer for review '{review_id}'.")

        new_comments = list(review.comments)
        if reason:
            new_comments.append({"author": reviewer_session_id, "comment": f"Rejected: {reason}", "timestamp": _utcnow()})

        merged_evidence = dict(review.evidence)
        if evidence:
            merged_evidence.update(evidence)

        completed_at = _utcnow()
        updated = CollaborationReview(
            review_id=review.review_id,
            conversation_id=review.conversation_id,
            thread_id=review.thread_id,
            author_session_id=review.author_session_id,
            reviewer_session_id=review.reviewer_session_id,
            artifact_references=review.artifact_references,
            status=ReviewStatus.REJECTED,
            reason=review.reason,
            evidence=merged_evidence,
            comments=new_comments,
            decision="rejected",
            requested_at=review.requested_at,
            started_at=review.started_at,
            completed_at=completed_at,
        )
        self._reviews[review_id] = updated

        self._timeline.record_event(
            event_type=TimelineEventType.REVIEW_REJECTED,
            session_id=reviewer_session_id,
            description=f"Peer review '{review_id}' REJECTED by reviewer '{reviewer_session_id}': {reason}",
            payload={"review_id": review_id, "reviewer_session_id": reviewer_session_id, "completed_at": completed_at, "rejection_reason": reason},
        )
        return updated

    def get_review(self, review_id: str) -> CollaborationReview:
        """Retrieve a CollaborationReview by ID."""
        if review_id not in self._reviews:
            raise KeyError(f"Review '{review_id}' not found.")
        return self._reviews[review_id]

    def get_pending_reviews(self, reviewer_session_id: str) -> list[CollaborationReview]:
        """Retrieve pending review requests assigned to a reviewer session (implements ReviewCoordinatorContract)."""
        r_ids = self._reviewer_reviews.get(reviewer_session_id, [])
        return [
            self._reviews[rid]
            for rid in r_ids
            if rid in self._reviews and self._reviews[rid].status in (ReviewStatus.REQUESTED, ReviewStatus.IN_PROGRESS, ReviewStatus.RESUBMITTED)
        ]

    def get_all_reviews(self) -> tuple[CollaborationReview, ...]:
        """Return a tuple of all recorded reviews."""
        return tuple(self._reviews.values())
