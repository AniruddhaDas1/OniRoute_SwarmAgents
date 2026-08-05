"""Abstract contracts for OniRoute Mission Orchestrator (ACR-004 Phase O1).

Defines interface specifications for Mission Director, Mission Pipeline, and Mission Intake.
This module contains contracts only — zero execution logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .evidence import MissionEvidence
from .models import ExecutionRequest, Mission, MissionReport, MissionRequest
from .states import MissionState


class MissionDirectorContract(ABC):
    """Abstract contract for the Mission Director.

    The Mission Director supervises orchestration, delegates tasks to existing
    frozen runtime engines (Workspace, Context Engine, ICOE, Planning Engine,
    Governance, UMAL, Invocation, Runtime), collects immutable evidence, maintains
    execution status, and generates reports.

    THE MISSION DIRECTOR NEVER EXECUTES AI DIRECTLY.
    """

    @abstractmethod
    def receive_mission(self, request: MissionRequest) -> Mission:
        """Parse raw request into an immutable Mission object in RECEIVED state."""
        ...

    @abstractmethod
    def supervise_orchestration(self, mission: Mission) -> Mission:
        """Supervise the pipeline progression across existing frozen engines."""
        ...

    @abstractmethod
    def transition_state(self, mission: Mission, target_state: MissionState, reason: str = "") -> Mission:
        """Transition mission to a new state and record state history."""
        ...

    @abstractmethod
    def collect_evidence(self, mission: Mission, stage: str, evidence_data: dict[str, Any]) -> Mission:
        """Record stage evidence into the immutable evidence log."""
        ...

    @abstractmethod
    def generate_report(self, mission: Mission) -> MissionReport:
        """Generate a consolidated execution and evidence report."""
        ...


class MissionPipelineContract(ABC):
    """Abstract contract for the canonical Mission Orchestration Pipeline.

    Pipeline sequence:
    CLI -> Mission Intake -> Workspace Discovery -> Mission Resolution ->
    Context Engine -> ICOE -> Planning Engine -> Governance -> UMAL ->
    Invocation -> Execution Runtime
    """

    @abstractmethod
    def execute_stage(self, stage_name: str, mission: Mission) -> Mission:
        """Process a single pipeline stage without replacing underlying engine implementations."""
        ...


class MissionIntakeContract(ABC):
    """Abstract contract for Mission Intake (CLI / API entry point)."""

    @abstractmethod
    def parse_cli_command(self, raw_args: list[str], explicit_workspace: Any = None) -> MissionRequest:
        """Normalize raw CLI command arguments into a canonical MissionRequest."""
        ...


class MissionResolverContract(ABC):
    """Abstract contract for Mission Resolution (ACR-004 Phase O3)."""

    @abstractmethod
    def resolve_mission(
        self,
        request: MissionRequest,
        workspace_manager: Any = None,
    ) -> Mission:
        """Transform a canonical MissionRequest into a fully validated Mission."""
        ...


class MissionOrchestratorContract(ABC):
    """Abstract contract for Mission Orchestration (ACR-004 Phase O4)."""

    @abstractmethod
    def orchestrate_mission(self, mission: Mission) -> ExecutionRequest:
        """Convert a VALIDATED Mission into a canonical ExecutionRequest."""
        ...
