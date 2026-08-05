"""Exceptions for OniRoute Mission Intake (ACR-004 Phase O2).

Defines structured error types for Mission Intake processing failures.
"""

from __future__ import annotations


class MissionIntakeError(Exception):
    """Base exception for all Mission Intake failures."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EmptyCommandError(MissionIntakeError):
    """Raised when an empty or whitespace-only command string is submitted."""

    pass


class InvalidCommandError(MissionIntakeError):
    """Raised when a command string is malformed or unparseable."""

    pass


class WorkspaceUnavailableError(MissionIntakeError):
    """Raised when a specified workspace root path does not exist or is invalid."""

    pass


class MalformedRequestError(MissionIntakeError):
    """Raised when request parameters or payload are malformed."""

    pass
