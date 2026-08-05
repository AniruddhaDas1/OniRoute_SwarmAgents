"""Mission Director component for OniRoute Mission Orchestrator (ACR-004 Phase O1 & O3).

The Mission Director supervises pipeline progression and handles engine delegations.

THE MISSION DIRECTOR NEVER EXECUTES AI DIRECTLY.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contracts import MissionDirectorContract
from .exceptions import InvalidMissionStateError
from .models import Mission, MissionReport, MissionRequest, MissionStatus
from .resolution import MissionResolver
from .states import MissionState, can_transition


class MissionDirector(MissionDirectorContract):
    """Concrete supervisor component for Mission Orchestration."""

    def __init__(self, resolver: MissionResolver | None = None) -> None:
        self.resolver = resolver or MissionResolver()

    def receive_mission(self, request: MissionRequest) -> Mission:
        """Parse raw request and resolve it into an immutable Mission object."""
        return self.resolver.resolve_mission(request)

    def supervise_orchestration(self, mission: Mission) -> Mission:
        """Supervise pipeline progression across existing frozen engines.

        During Mission Resolution (Phase O3), ensures mission state is VALIDATED.
        Does NOT execute workflows, agents, or models.
        """
        if mission.status.current_state != MissionState.VALIDATED:
            mission = self.transition_state(
                mission, MissionState.VALIDATED, reason="Mission Director validation supervision"
            )
        return mission

    def transition_state(
        self, mission: Mission, target_state: MissionState, reason: str = ""
    ) -> Mission:
        """Transition mission to a new state and record state history."""
        current = mission.status.current_state
        if current == target_state:
            return mission

        if not can_transition(current, target_state):
            raise InvalidMissionStateError(
                f"Cannot transition mission '{mission.mission_id}' from '{current}' to '{target_state}'."
            )

        now_str = datetime.now(timezone.utc).isoformat()
        history = list(mission.status.state_history)
        history.append(
            {
                "from_state": current.value if hasattr(current, "value") else str(current),
                "to_state": target_state.value if hasattr(target_state, "value") else str(target_state),
                "reason": reason or f"Transitioned to {target_state}",
                "timestamp": now_str,
            }
        )

        new_status = MissionStatus(
            current_state=target_state,
            state_history=history,
            current_step=f"State: {target_state}",
            progress_percentage=100.0 if target_state in (MissionState.VALIDATED, MissionState.COMPLETED) else mission.status.progress_percentage,
            started_at=mission.status.started_at,
            updated_at=now_str,
            completed_at=now_str if target_state in (MissionState.COMPLETED, MissionState.FAILED, MissionState.CANCELLED) else None,
        )

        current_dict = mission.model_dump(mode="python")
        current_dict["status"] = new_status
        return Mission(**current_dict)

    def collect_evidence(
        self, mission: Mission, stage: str, evidence_data: dict[str, Any]
    ) -> Mission:
        """Record stage evidence into the immutable evidence log."""
        updated_evidence = mission.evidence.record_stage(stage, evidence_data)
        current_dict = mission.model_dump(mode="python")
        current_dict["evidence"] = updated_evidence
        return Mission(**current_dict)

    def generate_report(self, mission: Mission) -> MissionReport:
        """Generate a consolidated execution and evidence report."""
        if mission.report is not None:
            return mission.report

        return MissionReport(
            mission_id=mission.mission_id,
            title=f"Mission Report: {mission.name}",
            summary=f"Mission '{mission.mission_id}' state: {mission.status.current_state}.",
            evidence_summary={
                "workspace": bool(mission.evidence.workspace),
                "project": bool(mission.evidence.project),
                "repository": bool(mission.evidence.repository),
                "context": bool(mission.evidence.context),
                "optimization": bool(mission.evidence.optimization),
                "knowledge": bool(mission.evidence.knowledge),
                "constraints": bool(mission.evidence.constraints),
                "requirements": bool(mission.evidence.requirements),
                "validation": bool(mission.evidence.validation),
            },
        )
