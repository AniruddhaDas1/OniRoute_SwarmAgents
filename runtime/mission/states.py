"""Mission lifecycle state definitions for OniRoute Mission Orchestrator (ACR-004 Phase O1)."""

from __future__ import annotations

from enum import Enum


class MissionState(str, Enum):
    """Canonical lifecycle states for a Mission."""

    RECEIVED = "received"
    PARSED = "parsed"
    RESOLVED = "resolved"
    VALIDATED = "validated"
    ORCHESTRATED = "orchestrated"
    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


#: Allowed state transitions dictionary mapping current state to valid next states.
ALLOWED_STATE_TRANSITIONS: dict[MissionState, set[MissionState]] = {
    MissionState.RECEIVED: {MissionState.PARSED, MissionState.FAILED, MissionState.CANCELLED},
    MissionState.PARSED: {MissionState.RESOLVED, MissionState.FAILED, MissionState.CANCELLED},
    MissionState.RESOLVED: {MissionState.VALIDATED, MissionState.FAILED, MissionState.CANCELLED},
    MissionState.VALIDATED: {MissionState.ORCHESTRATED, MissionState.PLANNED, MissionState.FAILED, MissionState.CANCELLED},
    MissionState.ORCHESTRATED: {MissionState.PLANNED, MissionState.FAILED, MissionState.CANCELLED},
    MissionState.PLANNED: {MissionState.EXECUTING, MissionState.FAILED, MissionState.CANCELLED},
    MissionState.EXECUTING: {MissionState.COMPLETED, MissionState.FAILED, MissionState.CANCELLED},
    MissionState.COMPLETED: set(),
    MissionState.FAILED: set(),
    MissionState.CANCELLED: set(),
}


def can_transition(current: MissionState, target: MissionState) -> bool:
    """Validate whether transitioning from *current* to *target* state is allowed."""
    allowed = ALLOWED_STATE_TRANSITIONS.get(current, set())
    return target in allowed
