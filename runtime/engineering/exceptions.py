"""Autonomous Engineering Worker Exceptions (Phase P5.E1)."""

from __future__ import annotations


class EngineeringWorkerError(Exception):
    """Base exception for engineering worker failures."""

    pass


class EngineeringBoundaryViolation(EngineeringWorkerError):
    """Raised when an engineering worker attempts to write outside contract boundaries or engine root."""

    pass


class EngineeringExecutionError(EngineeringWorkerError):
    """Raised when engineering contract execution or code generation fails."""

    pass
