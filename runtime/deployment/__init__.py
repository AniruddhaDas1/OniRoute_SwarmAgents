"""Mission Deployment Planner package for OniRoute (Phase P3.A1).

Converts EngineeringExecutionPlan and AgentProfileReport into an immutable MissionDeploymentPlan.
"""

from .benchmark import benchmark_deployment_planner
from .exceptions import (
    CyclicDependencyError,
    DeploymentPlanningError,
    InvalidGatePathError,
    OrphanProfileError,
    UnscheduledProfileError,
)
from .models import (
    ApprovalGate,
    ArtifactRoute,
    ExecutionBudgetAllocation,
    ExecutionWave,
    FailureHandlingPolicy,
    HumanApprovalCheckpoint,
    MissionDeploymentPlan,
    ParallelGroup,
    RetryPolicy,
    ReviewGate,
    RollbackPolicy,
    SequentialDependency,
    TimeoutPolicy,
    WaveName,
    WaveNumber,
)
from .planner import MissionDeploymentPlanner

__all__ = [
    "ApprovalGate",
    "ArtifactRoute",
    "CyclicDependencyError",
    "DeploymentPlanningError",
    "ExecutionBudgetAllocation",
    "ExecutionWave",
    "FailureHandlingPolicy",
    "HumanApprovalCheckpoint",
    "InvalidGatePathError",
    "MissionDeploymentPlan",
    "MissionDeploymentPlanner",
    "OrphanProfileError",
    "ParallelGroup",
    "RetryPolicy",
    "ReviewGate",
    "RollbackPolicy",
    "SequentialDependency",
    "TimeoutPolicy",
    "UnscheduledProfileError",
    "WaveName",
    "WaveNumber",
    "benchmark_deployment_planner",
]
