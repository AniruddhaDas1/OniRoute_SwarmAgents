"""Validation & Acceptance Exceptions (Phase P5.E4)."""

from __future__ import annotations


class ValidationAcceptanceError(Exception):
    """Base exception for Validation & Acceptance failures."""

    pass


class VerificationExecutionError(ValidationAcceptanceError):
    """Raised when VerificationEngine fails to run verification checks."""

    pass


class AcceptanceEvaluationError(ValidationAcceptanceError):
    """Raised when AcceptanceEngine fails to evaluate acceptance criteria."""

    pass
