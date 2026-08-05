"""Exceptions for Natural Language Router (Phase P6.D1)."""

from __future__ import annotations


class RouterError(Exception):
    """Base exception for router errors."""
    pass


class ConfidenceBelowThresholdError(RouterError):
    """Raised when intent analysis confidence is below the required threshold."""
    pass


class RouterExecutionError(RouterError):
    """Raised when execution fails inside NaturalLanguageRouter."""
    pass
