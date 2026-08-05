"""Interface contracts for the OniRoute Agent Runtime (ACR-006 Phase R1).

Defines ABC interfaces for all canonical Agent Runtime pipeline components.
All contracts are architecture-only specifications. No execution, AI calls, or scheduling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from runtime.organization.blueprint import ExecutionBlueprint

from .models import (
    AgentSession,
    ArtifactRecord,
    ExecutionEvent,
    ExecutionResult,
    RuntimeContext,
    RuntimeReport,
    RuntimeState,
)


class RuntimeInitializerContract(ABC):
    """Contract for initializing the Agent Runtime from a sealed ExecutionBlueprint."""

    @abstractmethod
    def initialize_runtime(self, blueprint: ExecutionBlueprint) -> RuntimeContext:
        """Establish runtime context from the sealed Execution Blueprint."""
        raise NotImplementedError


class SessionManagerContract(ABC):
    """Contract for creating and managing AgentSession lifecycle."""

    @abstractmethod
    def create_session(self, blueprint: ExecutionBlueprint, member_id: str) -> AgentSession:
        """Instantiate a new AgentSession for the specified organization member."""
        raise NotImplementedError

    @abstractmethod
    def transition_state(self, session: AgentSession, target_state: RuntimeState) -> AgentSession:
        """Apply a validated lifecycle state transition to an AgentSession."""
        raise NotImplementedError

    @abstractmethod
    def terminate_session(self, session: AgentSession) -> AgentSession:
        """Mark a session as COMPLETED or CANCELLED and finalize its state."""
        raise NotImplementedError


class ExecutionCoordinatorContract(ABC):
    """Contract for the Execution Coordinator that orchestrates all agent sessions."""

    @abstractmethod
    def instantiate_sessions(
        self, blueprint: ExecutionBlueprint, context: RuntimeContext
    ) -> list[AgentSession]:
        """Create AgentSession instances for all members in the Organization."""
        raise NotImplementedError

    @abstractmethod
    def collect_results(self, sessions: list[AgentSession]) -> list[ExecutionResult]:
        """Aggregate execution results from all agent sessions."""
        raise NotImplementedError

    @abstractmethod
    def generate_report(
        self, blueprint: ExecutionBlueprint, sessions: list[AgentSession], results: list[ExecutionResult]
    ) -> RuntimeReport:
        """Compile a comprehensive RuntimeReport from session outcomes."""
        raise NotImplementedError


class ArtifactCollectorContract(ABC):
    """Contract for collecting and tracking artifacts across agent sessions."""

    @abstractmethod
    def register_artifact(self, session: AgentSession, artifact: ArtifactRecord) -> ArtifactRecord:
        """Register an artifact produced by an agent session."""
        raise NotImplementedError

    @abstractmethod
    def get_artifacts(self, session_id: str) -> list[ArtifactRecord]:
        """Retrieve all artifacts produced by a specific session."""
        raise NotImplementedError


class EventRecorderContract(ABC):
    """Contract for recording and retrieving runtime events."""

    @abstractmethod
    def record_event(self, session: AgentSession, event: ExecutionEvent) -> ExecutionEvent:
        """Record a runtime event against an agent session."""
        raise NotImplementedError

    @abstractmethod
    def get_events(self, session_id: str) -> list[ExecutionEvent]:
        """Retrieve all events recorded for a specific session."""
        raise NotImplementedError


class ExecutionReporterContract(ABC):
    """Contract for generating final RuntimeReports from completed sessions."""

    @abstractmethod
    def compile_report(
        self, blueprint: ExecutionBlueprint, sessions: list[AgentSession]
    ) -> RuntimeReport:
        """Compile a structured runtime report from a completed set of agent sessions."""
        raise NotImplementedError
