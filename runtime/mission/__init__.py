"""Mission Orchestrator Architecture package for OniRoute (ACR-004 Phase O1, O2, O3 & O4).

Defines canonical Mission models, lifecycle states, evidence schemas, abstract contracts,
Mission Intake normalizers, Mission Resolution engines, and Mission Orchestration engines.
"""

from .contracts import (
    MissionDirectorContract,
    MissionIntakeContract,
    MissionOrchestratorContract,
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
    MissionOrchestrationError,
    MissionResolutionError,
    MissionValidationError,
    WorkspaceUnavailableError,
)
from .intake import MissionIntake, MissionNormalizer
from .models import (
    ExecutionRequest,
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
from .orchestration import MissionOrchestrator
from .resolution import MissionResolver
from .states import ALLOWED_STATE_TRANSITIONS, MissionState, can_transition

def __getattr__(name: str):
    if name in ("MissionDeploymentPlan", "MissionDeploymentPlanner"):
        import runtime.deployment as dep
        return getattr(dep, name)
    if name in ("RuntimeExecutionSnapshot", "SwarmInitializationEngine"):
        import runtime.swarm as sw
        return getattr(sw, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "ALLOWED_STATE_TRANSITIONS",
    "EmptyCommandError",
    "ExecutionRequest",
    "InvalidCommandError",
    "InvalidMissionStateError",
    "MalformedRequestError",
    "Mission",
    "MissionConstraints",
    "MissionContext",
    "MissionDeliverables",
    "MissionDeploymentPlan",
    "MissionDeploymentPlanner",
    "MissionDirector",
    "MissionDirectorContract",
    "MissionEvidence",
    "MissionIntake",
    "MissionIntakeContract",
    "MissionIntakeError",
    "MissionNormalizer",
    "MissionOrchestrationError",
    "MissionOrchestrator",
    "MissionOrchestratorContract",
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
    "RuntimeExecutionSnapshot",
    "SwarmInitializationEngine",
    "WorkspaceUnavailableError",
    "can_transition",
]



