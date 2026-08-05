"""Quality Gate (Cross-Agent Review) Exceptions (Phase P5.E2)."""

from __future__ import annotations


class QualityGateError(Exception):
    """Base exception for Quality Gate review failures."""

    pass


class ReviewValidationError(QualityGateError):
    """Raised when quality gate input contract validation fails."""

    pass


class ReviewCompletenessError(QualityGateError):
    """Raised when review completeness or finding validation fails."""

    pass
