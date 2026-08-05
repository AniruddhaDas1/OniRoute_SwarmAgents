"""Failure classification for the OniRoute Recovery Engine (ACR-006 Phase R4).

Classifies exceptions and execution failures into canonical FailureCategory types.
Each classification carries a reason, evidence, and a recovery recommendation.
No AI. No side-effects. Pure deterministic classification logic.
"""

from __future__ import annotations

from enum import Enum


class FailureCategory(str, Enum):
    """Canonical failure categories for the OniRoute Runtime Recovery Engine."""

    TRANSIENT = "transient"
    """Temporary condition — safe to retry (network blip, timeout, rate limit)."""

    PERMANENT = "permanent"
    """Unrecoverable condition — retrying cannot help (invalid blueprint, bad config)."""

    GOVERNANCE = "governance"
    """Policy or budget denial — must not be retried without human approval."""

    USER = "user"
    """Caller-originated error — bad inputs, invalid command, or explicit rejection."""

    SYSTEM = "system"
    """Internal runtime fault — unexpected state, assertion failure, logic error."""

    NETWORK = "network"
    """Network connectivity or DNS resolution failure."""

    PROVIDER = "provider"
    """Upstream model-provider fault — 5xx response, overload, or unavailability."""

    CONFIGURATION = "configuration"
    """Misconfigured models.yaml, policies.yaml, or missing registry records."""


# ---------------------------------------------------------------------------
# Immutable classification result
# ---------------------------------------------------------------------------

class FailureClassification:
    """Immutable result returned by FailureClassifier.classify()."""

    __slots__ = (
        "category",
        "reason",
        "evidence",
        "recovery_recommendation",
        "is_retryable",
    )

    def __init__(
        self,
        category: FailureCategory,
        reason: str,
        evidence: dict,
        recovery_recommendation: str,
        is_retryable: bool,
    ) -> None:
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "evidence", dict(evidence))
        object.__setattr__(self, "recovery_recommendation", recovery_recommendation)
        object.__setattr__(self, "is_retryable", is_retryable)

    def __setattr__(self, name: str, value: object) -> None:  # noqa: D105
        raise AttributeError("FailureClassification is immutable.")

    def __repr__(self) -> str:
        return (
            f"FailureClassification(category={self.category!r}, "
            f"reason={self.reason!r}, retryable={self.is_retryable})"
        )

    def to_dict(self) -> dict:
        """Serialisable snapshot for RecoveryReport embedding."""
        return {
            "category": self.category.value,
            "reason": self.reason,
            "evidence": self.evidence,
            "recovery_recommendation": self.recovery_recommendation,
            "is_retryable": self.is_retryable,
        }


# ---------------------------------------------------------------------------
# Keywords used by the pattern-matching classifier
# ---------------------------------------------------------------------------

_NETWORK_KEYWORDS = frozenset({
    "connection refused", "connection reset", "connection timed out",
    "name or service not known", "network unreachable", "dns", "socket",
    "timeout", "timed out", "eof occurred", "broken pipe",
})

_PROVIDER_KEYWORDS = frozenset({
    "503", "502", "504", "overloaded", "rate limit", "rate_limit",
    "quota exceeded", "model not found", "adapter unreachable",
    "provider error", "upstream error",
})

_GOVERNANCE_KEYWORDS = frozenset({
    "governance denied", "permission denied", "policy denied",
    "budget exceeded", "approval required", "permissionerror",
})

_CONFIGURATION_KEYWORDS = frozenset({
    "keyerror", "missing key", "no such file", "filenotfounderror",
    "models.yaml", "policies.yaml", "config", "not found in blueprint",
    "invalid blueprint",
})

_PERMANENT_KEYWORDS = frozenset({
    "invalid blueprint", "blueprint sealed", "cannot modify",
    "assertion", "assertionerror", "notimplementederror",
    "invalid transition", "not ready", "not found",
})


def _lower(exc: Exception) -> str:
    return f"{type(exc).__name__} {exc}".lower()


# ---------------------------------------------------------------------------
# FailureClassifier
# ---------------------------------------------------------------------------

class FailureClassifier:
    """Pure deterministic failure classifier.

    Inspects the exception type and message to assign a FailureCategory,
    populate evidence, and produce a recovery recommendation.
    """

    def classify(self, exc: Exception, context: dict | None = None) -> FailureClassification:
        """Classify *exc* into a FailureClassification.

        Parameters
        ----------
        exc:
            The exception to classify.
        context:
            Optional execution context for richer evidence (session_id, etc.).

        Returns
        -------
        FailureClassification
            Immutable classification record.
        """
        msg = _lower(exc)
        ctx = context or {}
        exc_type = type(exc).__name__

        evidence: dict = {
            "exception_type": exc_type,
            "exception_message": str(exc),
            "session_id": ctx.get("session_id", "unknown"),
            "member_id": ctx.get("member_id", "unknown"),
        }

        # -- Governance -------------------------------------------------------
        if isinstance(exc, PermissionError) or any(kw in msg for kw in _GOVERNANCE_KEYWORDS):
            return FailureClassification(
                category=FailureCategory.GOVERNANCE,
                reason=f"Governance or permission policy denied execution: {exc}",
                evidence=evidence,
                recovery_recommendation=(
                    "Request human approval via `oniroute review <session-id> --approve` "
                    "or adjust policy configuration."
                ),
                is_retryable=False,
            )

        # -- Network ----------------------------------------------------------
        if any(kw in msg for kw in _NETWORK_KEYWORDS):
            return FailureClassification(
                category=FailureCategory.NETWORK,
                reason=f"Network connectivity failure: {exc}",
                evidence=evidence,
                recovery_recommendation=(
                    "Check network connectivity and provider endpoint. "
                    "Retry via `oniroute retry <session-id>` after resolving connectivity."
                ),
                is_retryable=True,
            )

        # -- Provider ---------------------------------------------------------
        if any(kw in msg for kw in _PROVIDER_KEYWORDS):
            return FailureClassification(
                category=FailureCategory.PROVIDER,
                reason=f"Upstream model-provider failure: {exc}",
                evidence=evidence,
                recovery_recommendation=(
                    "Retry via `oniroute retry <session-id>` after provider recovers. "
                    "Consider switching model endpoint in config/models.yaml."
                ),
                is_retryable=True,
            )

        # -- Configuration ----------------------------------------------------
        if any(kw in msg for kw in _CONFIGURATION_KEYWORDS):
            return FailureClassification(
                category=FailureCategory.CONFIGURATION,
                reason=f"Configuration or registry error: {exc}",
                evidence=evidence,
                recovery_recommendation=(
                    "Review config/models.yaml and config/policies.yaml. "
                    "Ensure all referenced agents, skills, and workflows exist."
                ),
                is_retryable=False,
            )

        # -- Permanent --------------------------------------------------------
        if isinstance(exc, (ValueError, NotImplementedError, AssertionError)) or any(
            kw in msg for kw in _PERMANENT_KEYWORDS
        ):
            return FailureClassification(
                category=FailureCategory.PERMANENT,
                reason=f"Permanent non-recoverable failure: {exc}",
                evidence=evidence,
                recovery_recommendation=(
                    "Manual intervention required. "
                    "Review blueprint, organization, and mission definitions."
                ),
                is_retryable=False,
            )

        # -- System (catch-all for unexpected internal faults) ----------------
        return FailureClassification(
            category=FailureCategory.SYSTEM,
            reason=f"Unexpected system failure: {exc}",
            evidence=evidence,
            recovery_recommendation=(
                "Inspect runtime logs and session events. "
                "If transient, retry via `oniroute retry <session-id>`."
            ),
            is_retryable=True,
        )
