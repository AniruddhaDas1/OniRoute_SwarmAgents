"""Immutable data models for the OniRoute Recovery Engine (ACR-006 Phase R4).

All models are Pydantic BaseModels with frozen=True where immutability is required.
No execution logic. Pure declarative state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Retry Policy
# ---------------------------------------------------------------------------

class RetryPolicy(BaseModel):
    """Declarative retry configuration for the RetryManager."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(default=3, ge=0, description="Maximum number of retry attempts.")
    base_delay_seconds: float = Field(
        default=1.0, ge=0.0,
        description="Base delay in seconds between retries (exponential backoff applies).",
    )
    backoff_factor: float = Field(
        default=2.0, ge=1.0,
        description="Multiplier applied to base_delay_seconds on each retry.",
    )
    max_delay_seconds: float = Field(
        default=30.0, ge=0.0,
        description="Upper cap on retry delay in seconds.",
    )


# ---------------------------------------------------------------------------
# Retry Record
# ---------------------------------------------------------------------------

class RetryRecord(BaseModel):
    """Immutable record capturing a single retry attempt."""

    model_config = ConfigDict(frozen=True)

    retry_id: str = Field(..., description="Unique retry attempt identifier.")
    session_id: str = Field(..., description="Session being retried.")
    attempt_number: int = Field(..., ge=1, description="1-indexed retry attempt number.")
    failure_category: str = Field(..., description="FailureCategory value that triggered the retry.")
    failure_reason: str = Field(..., description="Human-readable failure reason.")
    delay_seconds: float = Field(default=0.0, description="Delay applied before this retry.")
    outcome: str = Field(default="pending", description="'success', 'failure', or 'pending'.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Structured retry evidence.")
    started_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC retry start timestamp.")
    completed_at: str | None = Field(default=None, description="ISO-8601 UTC retry completion timestamp.")


# ---------------------------------------------------------------------------
# Pause Record
# ---------------------------------------------------------------------------

class PauseRecord(BaseModel):
    """Immutable record capturing a pause event for an AgentSession."""

    model_config = ConfigDict(frozen=True)

    pause_id: str = Field(..., description="Unique pause record identifier.")
    session_id: str = Field(..., description="Session that was paused.")
    reason: str = Field(..., description="Human-readable reason for the pause.")
    actor: str = Field(
        default="runtime",
        description="Actor that initiated the pause ('runtime', 'user', 'governance').",
    )
    evidence: dict[str, Any] = Field(default_factory=dict, description="Contextual pause evidence.")
    paused_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC pause timestamp.")
    resumed_at: str | None = Field(default=None, description="ISO-8601 UTC resume timestamp, if resumed.")


# ---------------------------------------------------------------------------
# Review Decision
# ---------------------------------------------------------------------------

class ReviewDecision(str, Enum):
    """Canonical decision options for the RuntimeReviewEngine."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


# ---------------------------------------------------------------------------
# Review Outcome
# ---------------------------------------------------------------------------

class ReviewOutcome(BaseModel):
    """Immutable record of a completed human review decision."""

    model_config = ConfigDict(frozen=True)

    review_id: str = Field(..., description="Associated ReviewRecord ID.")
    session_id: str = Field(..., description="Session under review.")
    decision: ReviewDecision = Field(..., description="Human review decision.")
    actor: str = Field(..., description="Identity of the human reviewer.")
    notes: str = Field(default="", description="Optional reviewer notes or change requests.")
    decided_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC decision timestamp.")


# ---------------------------------------------------------------------------
# Review Record
# ---------------------------------------------------------------------------

class ReviewRecord(BaseModel):
    """Immutable record capturing a pending or completed review request."""

    model_config = ConfigDict(frozen=True)

    review_id: str = Field(..., description="Unique review record identifier.")
    session_id: str = Field(..., description="Session requesting review.")
    member_id: str = Field(..., description="Member ID associated with the session.")
    review_reason: str = Field(..., description="Why review was requested.")
    artifacts_under_review: list[str] = Field(
        default_factory=list,
        description="Artifact IDs that require human review.",
    )
    evidence: dict[str, Any] = Field(default_factory=dict, description="Review context evidence.")
    requested_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC request timestamp.")
    outcome: ReviewOutcome | None = Field(default=None, description="Populated once reviewed.")

    @property
    def is_pending(self) -> bool:
        """True if no decision has been recorded yet."""
        return self.outcome is None

    @property
    def is_approved(self) -> bool:
        """True if the decision is APPROVE."""
        return self.outcome is not None and self.outcome.decision == ReviewDecision.APPROVE

    @property
    def is_rejected(self) -> bool:
        """True if the decision is REJECT."""
        return self.outcome is not None and self.outcome.decision == ReviewDecision.REJECT


# ---------------------------------------------------------------------------
# Recovery Metrics
# ---------------------------------------------------------------------------

class RecoveryMetrics(BaseModel):
    """Aggregate metrics captured by the RecoveryOrchestrator."""

    model_config = ConfigDict(frozen=True)

    total_failures: int = Field(default=0)
    total_retries: int = Field(default=0)
    successful_retries: int = Field(default=0)
    failed_retries: int = Field(default=0)
    total_pauses: int = Field(default=0)
    total_resumes: int = Field(default=0)
    total_reviews_requested: int = Field(default=0)
    total_reviews_approved: int = Field(default=0)
    total_reviews_rejected: int = Field(default=0)
    total_recoveries: int = Field(default=0)


# ---------------------------------------------------------------------------
# Recovery Report
# ---------------------------------------------------------------------------

class RecoveryReport(BaseModel):
    """Immutable, append-only recovery audit report.

    Generated by RecoveryOrchestrator after a session completes or fails
    recovery. Acts as the authoritative record for all recovery actions taken.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique report identifier.")
    session_id: str = Field(..., description="Session this report covers.")
    blueprint_id: str = Field(..., description="ExecutionBlueprint ID.")
    mission_id: str = Field(..., description="Mission ID.")

    # Failure evidence
    failures: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of FailureClassification.to_dict() snapshots.",
    )

    # Retry trail
    retries: list[RetryRecord] = Field(
        default_factory=list,
        description="Ordered list of RetryRecord objects.",
    )

    # Pause/resume trail
    pauses: list[PauseRecord] = Field(
        default_factory=list,
        description="Ordered list of PauseRecord objects.",
    )

    # Review trail
    review_requests: list[ReviewRecord] = Field(
        default_factory=list,
        description="List of ReviewRecord objects.",
    )
    review_outcomes: list[ReviewOutcome] = Field(
        default_factory=list,
        description="List of ReviewOutcome objects.",
    )

    # Aggregate metrics
    metrics: RecoveryMetrics = Field(
        default_factory=RecoveryMetrics,
        description="Aggregate recovery metrics.",
    )

    # Final recovery status
    recovery_status: str = Field(
        default="pending",
        description="'recovered', 'failed', 'pending', or 'review_required'.",
    )
    summary: str = Field(default="", description="Human-readable recovery summary.")

    # Timestamps
    generated_at: str = Field(
        default_factory=_utcnow,
        description="ISO-8601 UTC report generation timestamp.",
    )
