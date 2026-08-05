"""Autonomous Swarm Subsystem Freeze Certification Constants (Phase P3.A5).

Declares the frozen status, version, and contract immutability rules for the
Autonomous Swarm Subsystem in OniRoute v1.2.
"""

from __future__ import annotations

from typing import Dict, List

AUTONOMOUS_SWARM_FROZEN: bool = True
SWARM_SUBSYSTEM_VERSION: str = "v1.2.0-P3.A5"
SWARM_SUBSYSTEM_STATUS: str = "CERTIFIED_AND_FROZEN"

FROZEN_SWARM_CONTRACTS: List[str] = [
    "MissionDeploymentPlan",
    "RuntimeExecutionSnapshot",
    "ExecutionTaskQueue",
    "ExecutionTask",
    "SwarmExecutionResult",
    "ExchangeArtifactRecord",
    "SharedContextSnapshot",
    "SwarmHandoffRecord",
    "SwarmConsensusRecord",
]

FROZEN_SWARM_ENGINES: List[str] = [
    "MissionDeploymentPlanner",
    "SwarmInitializationEngine",
    "AutonomousExecutionEngine",
    "SwarmCoordinationEngine",
    "ArtifactExchange",
    "SharedContextManager",
    "HandoffCoordinator",
    "SwarmConsensusEngine",
]

SWARM_FREEZE_MANIFEST: Dict[str, str] = {
    "subsystem": "Autonomous Swarm Subsystem",
    "phase": "P3.A5",
    "version": SWARM_SUBSYSTEM_VERSION,
    "status": SWARM_SUBSYSTEM_STATUS,
    "architecture": "OniRoute Core v1.2",
    "immutability": "STRICT_READ_ONLY_FROZEN",
    "certified_at": "2026-08-05T21:39:19+00:00",
}
