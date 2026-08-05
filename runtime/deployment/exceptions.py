"""Exceptions for Mission Deployment Planner (Phase P3.A1)."""

from __future__ import annotations


class DeploymentPlanningError(Exception):
    """Base exception for all Mission Deployment Planner failures."""
    pass


class CyclicDependencyError(DeploymentPlanningError):
    """Raised when cyclic execution dependencies are detected in agent profiles."""
    pass


class UnscheduledProfileError(DeploymentPlanningError):
    """Raised when one or more agent profiles cannot be scheduled into execution waves."""
    pass


class OrphanProfileError(DeploymentPlanningError):
    """Raised when an agent profile lacks wave membership or valid dependency wiring."""
    pass


class InvalidGatePathError(DeploymentPlanningError):
    """Raised when review, approval, or artifact routes are invalid or unreachable."""
    pass
