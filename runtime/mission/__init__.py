"""Mission Orchestrator Architecture package for OniRoute (ACR-004 Phase O1).

Defines canonical Mission models, lifecycle states, evidence schemas, and abstract contracts.
This package contains architecture and schemas only — zero execution logic.
"""

from .contracts import (
    MissionDirectorContract,
    MissionIntakeContract,
    MissionPipelineContract,
)
from .evidence import MissionEvidence
from .models import (
    Mission,
    MissionConstraints,
    MissionContext,
    MissionDeliverables,
    MissionReport,
    MissionRequest,
    MissionRequirements,
    MissionResult,
    MissionStatus,
)
from .states import ALLOWED_STATE_TRANSITIONS, MissionState, can_transition

__all__ = [
    "ALLOWED_STATE_TRANSITIONS",
    "Mission",
    "MissionConstraints",
    "MissionContext",
    "MissionDeliverables",
    "MissionDirectorContract",
    "MissionEvidence",
    "MissionIntakeContract",
    "MissionPipelineContract",
    "MissionReport",
    "MissionRequest",
    "MissionRequirements",
    "MissionResult",
    "MissionState",
    "MissionStatus",
    "can_transition",
]
