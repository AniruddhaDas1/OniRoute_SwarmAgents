"""Deterministic Session Manager for OniRoute Agent Runtime (ACR-006 Phase R2).

Creates AgentSession records from a sealed ExecutionBlueprint.
Applies deterministic INITIALIZED → READY lifecycle transitions.
Records SESSION_CREATED and STATE_TRANSITION events.
No AI invocation, no task execution, no scheduling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from runtime.organization.blueprint import ExecutionBlueprint
from runtime.organization.models import OrganizationMember

from .contracts import SessionManagerContract
from .event_recorder import EventRecorder
from .models import (
    AgentSession,
    ExecutionEvent,
    ExecutionStatus,
    RuntimeEventType,
    RuntimeMetrics,
    RuntimeState,
    can_runtime_transition,
)


class SessionManager(SessionManagerContract):
    """Concrete Session Manager. Instantiates and initializes AgentSessions
    from OrganizationMember definitions in the sealed ExecutionBlueprint."""

    def __init__(self) -> None:
        self._event_recorder = EventRecorder()
        self._session_counter: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public Contract Methods
    # ------------------------------------------------------------------

    def create_session(self, blueprint: ExecutionBlueprint, member_id: str) -> AgentSession:
        """Create and initialize a single AgentSession for the given member."""
        member = self._resolve_member(blueprint, member_id)
        session = self._build_session(blueprint, member)
        session = self._record_creation_events(session)
        session = self.transition_state(session, RuntimeState.READY)
        return session

    def transition_state(self, session: AgentSession, target_state: RuntimeState) -> AgentSession:
        """Apply a validated lifecycle state transition and record a STATE_TRANSITION event."""
        if not can_runtime_transition(session.state, target_state):
            raise ValueError(
                f"Invalid transition: {session.state.value} → {target_state.value} "
                f"for session {session.session_id}"
            )
        previous = session.state
        session.state = target_state

        if target_state == RuntimeState.READY:
            session.status = ExecutionStatus.PENDING

        event = ExecutionEvent(
            event_id=f"ev-st-{session.session_id}-{len(session.events):03d}",
            event_type=RuntimeEventType.STATE_TRANSITION,
            session_id=session.session_id,
            member_id=session.member_id,
            description=f"State transition: {previous.value} → {target_state.value}",
            previous_state=previous,
            next_state=target_state,
            event_payload={"previous": previous.value, "next": target_state.value},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._event_recorder.record_event(session, event)
        return session

    def terminate_session(self, session: AgentSession) -> AgentSession:
        """Mark session as COMPLETED (or CANCELLED if not running)."""
        target = (
            RuntimeState.COMPLETED
            if session.state == RuntimeState.RUNNING
            else RuntimeState.CANCELLED
        )
        return self.transition_state(session, target)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _resolve_member(self, blueprint: ExecutionBlueprint, member_id: str) -> OrganizationMember:
        for member in blueprint.organization.members:
            if member.member_id == member_id:
                return member
        raise ValueError(f"Member '{member_id}' not found in blueprint '{blueprint.blueprint_id}'")

    def _build_session(self, blueprint: ExecutionBlueprint, member: OrganizationMember) -> AgentSession:
        """Construct an AgentSession from a blueprint member definition."""
        self._session_counter[member.member_id] = (
            self._session_counter.get(member.member_id, 0) + 1
        )
        seq = self._session_counter[member.member_id]
        session_id = f"sess-{member.member_id}-{seq:03d}"

        # Inherit execution constraints from blueprint
        exec_constraints: list[dict[str, Any]] = blueprint.execution_constraints or []

        # Gather member evidence
        session_evidence: list[dict[str, Any]] = [
            ev.model_dump(mode="python") if hasattr(ev, "model_dump") else dict(ev)
            for ev in member.evidence
        ]

        return AgentSession(
            session_id=session_id,
            member_id=member.member_id,
            role_id=member.role.role_id,
            role_title=member.role.title,
            blueprint_id=blueprint.blueprint_id,
            capability_ids=list(member.capability_ids),
            required_skills=list(member.required_skills),
            knowledge_references=list(member.knowledge_references),
            package_references=list(member.package_references),
            workflow_references=list(member.workflow_references),
            execution_constraints=exec_constraints,
            state=RuntimeState.INITIALIZED,
            status=ExecutionStatus.PENDING,
            metrics=RuntimeMetrics(
                session_id=session_id,
                start_time=datetime.now(timezone.utc).isoformat(),
            ),
            evidence=session_evidence,
            metadata={
                "role_type": member.role.role_type,
                "primary_responsibility": member.role.primary_responsibility,
                "responsibilities": member.responsibilities,
            },
        )

    def _record_creation_events(self, session: AgentSession) -> AgentSession:
        """Record SESSION_CREATED event immediately after session construction."""
        event = ExecutionEvent(
            event_id=f"ev-sc-{session.session_id}-000",
            event_type=RuntimeEventType.SESSION_CREATED,
            session_id=session.session_id,
            member_id=session.member_id,
            description=f"Session created for {session.role_title} ({session.member_id})",
            next_state=RuntimeState.INITIALIZED,
            event_payload={
                "role_id": session.role_id,
                "capability_count": len(session.capability_ids),
                "blueprint_id": session.blueprint_id,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._event_recorder.record_event(session, event)
        return session
