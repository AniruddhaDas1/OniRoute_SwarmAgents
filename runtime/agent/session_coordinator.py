"""Session Coordinator for OniRoute Agent Runtime (ACR-006 Phase R2).

Orchestrates full session initialization pipeline:
  ExecutionBlueprint → RuntimeContext → AgentSession[] → SessionRegistry → RuntimeReport

No AI invocation, no task execution, no scheduling.
"""

from __future__ import annotations

from datetime import datetime, timezone

from runtime.organization.blueprint import ExecutionBlueprint

from .models import (
    AgentSession,
    ExecutionResult,
    ExecutionStatus,
    RuntimeContext,
    RuntimeReport,
    RuntimeState,
)
from .runtime_initializer import RuntimeInitializer
from .session_manager import SessionManager
from .session_registry import SessionRegistry


class SessionCoordinator:
    """Coordinates full session initialization from a sealed ExecutionBlueprint.

    Produces a populated SessionRegistry and immutable RuntimeReport.
    """

    def __init__(self) -> None:
        self._initializer = RuntimeInitializer()
        self._manager = SessionManager()
        self._registry = SessionRegistry()

    def initialize_sessions(
        self, blueprint: ExecutionBlueprint
    ) -> tuple[RuntimeContext, list[AgentSession], RuntimeReport]:
        """Full initialization pipeline: Blueprint → Context → Sessions → Report."""
        # 1. Establish RuntimeContext
        context = self._initializer.initialize_runtime(blueprint)

        # 2. Create one AgentSession per member
        sessions: list[AgentSession] = []
        for member in blueprint.organization.members:
            session = self._manager.create_session(blueprint, member.member_id)
            self._registry.register(session)
            sessions.append(session)

        # 3. Update context with active session IDs
        context.active_session_ids.extend(s.session_id for s in sessions)

        # 4. Generate initialization RuntimeReport
        report = self._build_report(blueprint, context, sessions)
        return context, sessions, report

    @property
    def registry(self) -> SessionRegistry:
        return self._registry

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_report(
        self,
        blueprint: ExecutionBlueprint,
        context: RuntimeContext,
        sessions: list[AgentSession],
    ) -> RuntimeReport:
        total_events = sum(len(s.events) for s in sessions)
        role_distribution: dict[str, int] = {}
        capability_coverage: dict[str, list[str]] = {}

        for s in sessions:
            role_distribution[s.role_title] = role_distribution.get(s.role_title, 0) + 1
            for cap_id in s.capability_ids:
                capability_coverage.setdefault(cap_id, []).append(s.session_id)

        state_summary = {state.value: 0 for state in RuntimeState}
        for s in sessions:
            state_summary[s.state.value] += 1

        results: list[ExecutionResult] = [
            ExecutionResult(
                result_id=f"res-init-{s.session_id}",
                session_id=s.session_id,
                member_id=s.member_id,
                status=ExecutionStatus.PENDING,
                artifacts_produced=[],
                events_recorded=len(s.events),
                summary=f"Session {s.session_id} initialized and READY ({s.role_title}).",
            )
            for s in sessions
        ]

        summary = (
            f"Initialized {len(sessions)} sessions for blueprint "
            f"'{blueprint.blueprint_id}'. All sessions reached READY state."
        )

        return RuntimeReport(
            report_id=f"rep-rt-{blueprint.blueprint_id}",
            blueprint_id=blueprint.blueprint_id,
            mission_id=blueprint.mission.mission_id,
            total_sessions=len(sessions),
            completed_sessions=state_summary.get("completed", 0),
            failed_sessions=state_summary.get("failed", 0),
            cancelled_sessions=state_summary.get("cancelled", 0),
            total_artifacts=0,
            total_events=total_events,
            execution_results=results,
            runtime_metrics=[s.metrics for s in sessions if s.metrics],
            summary=summary,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
