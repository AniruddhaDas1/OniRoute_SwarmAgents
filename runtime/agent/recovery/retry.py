"""Retry Manager for the OniRoute Recovery Engine (ACR-006 Phase R4).

Manages retry eligibility, delay policy (exponential backoff), retry metrics,
and the immutable RetryRecord trail.

Never retries
- GOVERNANCE failures (policy denial, permission failure)
- PERMANENT failures (invalid blueprint, configuration error)

Always retries (subject to max_retries)
- NETWORK failures
- TRANSIENT failures
- PROVIDER failures
- SYSTEM failures
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .classifier import FailureCategory, FailureClassification
from .models import RetryPolicy, RetryRecord


_NON_RETRYABLE_CATEGORIES: frozenset[FailureCategory] = frozenset({
    FailureCategory.GOVERNANCE,
    FailureCategory.PERMANENT,
    FailureCategory.CONFIGURATION,
    FailureCategory.USER,
})


class RetryManager:
    """Deterministic retry manager with configurable policy and immutable evidence trail.

    Usage
    -----
    manager = RetryManager(policy=RetryPolicy(max_retries=3))
    if manager.can_retry(session_id, classification):
        record = manager.start_retry(session_id, classification)
        try:
            # ... attempt execution ...
            manager.complete_retry(record.retry_id, outcome="success")
        except Exception as exc:
            manager.complete_retry(record.retry_id, outcome="failure")
    """

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._policy = policy or RetryPolicy()
        self._attempt_counts: dict[str, int] = {}
        self._records: list[RetryRecord] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def policy(self) -> RetryPolicy:
        """The active retry policy."""
        return self._policy

    @property
    def records(self) -> tuple[RetryRecord, ...]:
        """Immutable snapshot of all recorded retry attempts."""
        return tuple(self._records)

    @property
    def metrics(self) -> dict:
        """Aggregate retry metrics."""
        total = len(self._records)
        success = sum(1 for r in self._records if r.outcome == "success")
        failure = sum(1 for r in self._records if r.outcome == "failure")
        return {
            "total_retries": total,
            "successful_retries": success,
            "failed_retries": failure,
            "pending_retries": total - success - failure,
        }

    def can_retry(self, session_id: str, classification: FailureClassification) -> bool:
        """Return True if a retry attempt is eligible for the given session and classification.

        Eligibility requires:
        1. The failure category is retryable.
        2. The session has not exhausted max_retries.
        """
        if classification.category in _NON_RETRYABLE_CATEGORIES:
            return False
        if not classification.is_retryable:
            return False
        attempts = self._attempt_counts.get(session_id, 0)
        return attempts < self._policy.max_retries

    def compute_delay(self, session_id: str) -> float:
        """Compute the exponential backoff delay (seconds) for the next retry.

        Delay = min(base_delay * backoff_factor^(attempt - 1), max_delay)
        """
        attempt = self._attempt_counts.get(session_id, 0)
        delay = self._policy.base_delay_seconds * (self._policy.backoff_factor ** attempt)
        return min(delay, self._policy.max_delay_seconds)

    def start_retry(
        self,
        session_id: str,
        classification: FailureClassification,
    ) -> RetryRecord:
        """Record the start of a retry attempt and increment the attempt counter.

        Returns the immutable RetryRecord for this attempt.
        """
        self._attempt_counts[session_id] = self._attempt_counts.get(session_id, 0) + 1
        attempt_number = self._attempt_counts[session_id]
        delay = self.compute_delay(session_id)

        record = RetryRecord(
            retry_id=f"retry-{session_id}-{attempt_number:03d}-{uuid.uuid4().hex[:6]}",
            session_id=session_id,
            attempt_number=attempt_number,
            failure_category=classification.category.value,
            failure_reason=classification.reason,
            delay_seconds=delay,
            outcome="pending",
            evidence=classification.evidence,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._records.append(record)
        return record

    def complete_retry(self, retry_id: str, outcome: str) -> RetryRecord:
        """Mark a retry attempt as 'success' or 'failure'.

        Returns the updated RetryRecord (the list is updated in place by
        replacing the pending record with a completed one).
        """
        if outcome not in ("success", "failure"):
            raise ValueError(f"Invalid retry outcome '{outcome}'. Must be 'success' or 'failure'.")

        completed_at = datetime.now(timezone.utc).isoformat()
        for i, record in enumerate(self._records):
            if record.retry_id == retry_id:
                updated = RetryRecord(
                    retry_id=record.retry_id,
                    session_id=record.session_id,
                    attempt_number=record.attempt_number,
                    failure_category=record.failure_category,
                    failure_reason=record.failure_reason,
                    delay_seconds=record.delay_seconds,
                    outcome=outcome,
                    evidence=record.evidence,
                    started_at=record.started_at,
                    completed_at=completed_at,
                )
                self._records[i] = updated
                return updated
        raise KeyError(f"RetryRecord '{retry_id}' not found.")

    def attempt_count(self, session_id: str) -> int:
        """Return the number of retry attempts made for *session_id*."""
        return self._attempt_counts.get(session_id, 0)

    def remaining_retries(self, session_id: str) -> int:
        """Return the number of retries remaining for *session_id*."""
        used = self._attempt_counts.get(session_id, 0)
        return max(0, self._policy.max_retries - used)
