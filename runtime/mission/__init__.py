"""Mission Orchestrator Architecture package for OniRoute (ACR-004 Phase O1 & O2).

Defines canonical Mission models, lifecycle states, evidence schemas, abstract contracts,
and Mission Intake normalizers.
"""

from .contracts import (
    MissionDirectorContract,
    MissionIntakeContract,
    MissionPipelineContract,
)
from .evidence import MissionEvidence
from .exceptions import (
    EmptyCommandError,
    InvalidCommandError,
    MalformedRequestError,
    MissionIntakeError,
    WorkspaceUnavailableError,
)
from .intake import MissionIntake, MissionNormalizer
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
    "EmptyCommandError",
    "InvalidCommandError",
    "MalformedRequestError",
    "Mission",
    "MissionConstraints",
    "MissionContext",
    "MissionDeliverables",
    "MissionDirectorContract",
    "MissionEvidence",
    "MissionIntake",
    "MissionIntakeContract",
    "MissionIntakeError",
    "MissionNormalizer",
    "MissionPipelineContract",
    "MissionReport",
    "MissionRequest",
    "MissionRequirements",
    "MissionResult",
    "MissionState",
    "MissionStatus",
    "WorkspaceUnavailableError",
    "can_transition",
]
