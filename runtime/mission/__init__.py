"""Mission Orchestrator Architecture package for OniRoute (ACR-004 Phase O1, O2 & O3).

Defines canonical Mission models, lifecycle states, evidence schemas, abstract contracts,
Mission Intake normalizers, and Mission Resolution engines.
"""

from .contracts import (
    MissionDirectorContract,
    MissionIntakeContract,
    MissionPipelineContract,
    MissionResolverContract,
)
from .director import MissionDirector
from .evidence import MissionEvidence
from .exceptions import (
    EmptyCommandError,
    InvalidCommandError,
    InvalidMissionStateError,
    MalformedRequestError,
    MissionIntakeError,
    MissionResolutionError,
    MissionValidationError,
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
from .resolution import MissionResolver
from .states import ALLOWED_STATE_TRANSITIONS, MissionState, can_transition

__all__ = [
    "ALLOWED_STATE_TRANSITIONS",
    "EmptyCommandError",
    "InvalidCommandError",
    "InvalidMissionStateError",
    "MalformedRequestError",
    "Mission",
    "MissionConstraints",
    "MissionContext",
    "MissionDeliverables",
    "MissionDirector",
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
    "MissionResolutionError",
    "MissionResolver",
    "MissionResolverContract",
    "MissionResult",
    "MissionState",
    "MissionStatus",
    "MissionValidationError",
    "WorkspaceUnavailableError",
    "can_transition",
]
