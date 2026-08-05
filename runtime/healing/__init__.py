"""Self-Healing Subsystem Package (Phase P5.E3).

Consumes QualityReport and produces RepairPlan & UpdatedEngineeringResult.
"""

from runtime.healing.engine import SelfHealingEngine
from runtime.healing.exceptions import RepairPlanningError, SelfHealingBoundaryViolation, SelfHealingError
from runtime.healing.models import RepairAction, RepairPlan, UpdatedEngineeringResult
from runtime.healing.planner import RepairPlanner

__all__ = [
    "RepairPlanner",
    "SelfHealingEngine",
    "RepairAction",
    "RepairPlan",
    "UpdatedEngineeringResult",
    "SelfHealingError",
    "RepairPlanningError",
    "SelfHealingBoundaryViolation",
]
