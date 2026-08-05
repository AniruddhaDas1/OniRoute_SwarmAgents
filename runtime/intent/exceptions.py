"""Exceptions for Intent Analysis Engine."""

from __future__ import annotations


class IntentAnalysisError(Exception):
    """Base exception for intent analysis operations."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmptyRequestError(IntentAnalysisError):
    """Raised when an empty or whitespace-only request is passed."""
