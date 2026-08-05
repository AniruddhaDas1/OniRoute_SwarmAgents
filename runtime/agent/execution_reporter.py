"""Execution Reporter for OniRoute Agent Runtime (ACR-006 Phase R3).

Compiles a final RuntimeReport from all completed AgentSessions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from runtime.organization.blueprint import ExecutionBlueprint

from .contracts import ExecutionReporterContract
from .models import (
    AgentSession,
    ExecutionResult,
    ExecutionStatus,
    RuntimeReport,
    RuntimeState,
)


class ExecutionReporter(ExecutionReporterContract):
    """Concrete ExecutionReporter. Compiles RuntimeReports from session outcomes."""

    def compile_report(
        self, blueprint: ExecutionBlueprint, sessions: list[AgentSession]
    ) -> RuntimeReport:
        """Compile a structured RuntimeReport from a completed set of agent sessions."""
        state_counts = {s.value: 0 for s in RuntimeState}
        for session in sessions:
            state_counts[session.state.value] += 1

        total_artifacts = sum(len(s.artifacts) for s in sessions)
        total_events = sum(len(s.events) for s in sessions)

        results: list[ExecutionResult] = []
        for session in sessions:
            final_status = (
                ExecutionStatus.DONE
                if session.state == RuntimeState.COMPLETED
                else (
                    ExecutionStatus.ERROR
                    if session.state == RuntimeState.FAILED
                    else ExecutionStatus.ABORTED
                )
            )
            results.append(
                ExecutionResult(
                    result_id=f"res-{session.session_id}",
                    session_id=session.session_id,
                    member_id=session.member_id,
                    status=final_status,
                    artifacts_produced=[a.artifact_id for a in session.artifacts],
                    events_recorded=len(session.events),
                    summary=(
                        f"{session.role_title} ({session.member_id}): "
                        f"{session.state.value.upper()} with "
                        f"{len(session.artifacts)} artifact(s)."
                    ),
                )
            )

        completed = state_counts.get(RuntimeState.COMPLETED.value, 0)
        failed = state_counts.get(RuntimeState.FAILED.value, 0)
        cancelled = state_counts.get(RuntimeState.CANCELLED.value, 0)

        summary = (
            f"Execution complete for blueprint '{blueprint.blueprint_id}'. "
            f"{completed}/{len(sessions)} sessions completed. "
            f"{failed} failed. {cancelled} cancelled. "
            f"{total_artifacts} artifact(s) produced."
        )

        return RuntimeReport(
            report_id=f"rep-exec-{blueprint.blueprint_id}",
            blueprint_id=blueprint.blueprint_id,
            mission_id=blueprint.mission.mission_id,
            total_sessions=len(sessions),
            completed_sessions=completed,
            failed_sessions=failed,
            cancelled_sessions=cancelled,
            total_artifacts=total_artifacts,
            total_events=total_events,
            execution_results=results,
            runtime_metrics=[s.metrics for s in sessions if s.metrics],
            summary=summary,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
