"""Exceptions for Swarm Initialization (Phase P3.A2)."""

from __future__ import annotations


class SwarmInitializationError(Exception):
    """Base exception for all Swarm Initialization failures."""
    pass


class SessionInitializationError(SwarmInitializationError):
    """Raised when an agent session cannot be initialized in READY state."""
    pass


class StorageConnectionError(SwarmInitializationError):
    """Raised when workspace storage directories or handles cannot be connected."""
    pass


class InvalidSnapshotError(SwarmInitializationError):
    """Raised when a RuntimeExecutionSnapshot fails validation or integrity checks."""
    pass
