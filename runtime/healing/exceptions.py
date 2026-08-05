"""Self-Healing Exceptions (Phase P5.E3)."""

from __future__ import annotations


class SelfHealingError(Exception):
    """Base exception for Self-Healing failures."""

    pass


class RepairPlanningError(SelfHealingError):
    """Raised when RepairPlanner fails to generate a RepairPlan."""

    pass


class SelfHealingBoundaryViolation(SelfHealingError):
    """Raised when SelfHealingEngine attempts repairs outside repair plan scope or engine root."""

    pass
