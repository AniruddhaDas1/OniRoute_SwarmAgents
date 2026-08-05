"""Read-only Session Registry for OniRoute Agent Runtime (ACR-006 Phase R2).

Provides lookup operations over instantiated AgentSessions. No execution.
"""

from __future__ import annotations

from .models import AgentSession, RuntimeState


class SessionRegistry:
    """Immutable read-only registry for tracking registered AgentSessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, AgentSession] = {}

    def register(self, session: AgentSession) -> None:
        """Register a session. Raises on duplicate session ID."""
        if session.session_id in self._sessions:
            raise ValueError(f"Duplicate session ID: {session.session_id}")
        self._sessions[session.session_id] = session

    def get_session(self, session_id: str) -> AgentSession | None:
        """Return a session by ID, or None if not found."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[AgentSession]:
        """Return all registered sessions."""
        return list(self._sessions.values())

    def find_by_role(self, role_id: str) -> list[AgentSession]:
        """Return all sessions bound to a specific role ID."""
        return [s for s in self._sessions.values() if s.role_id == role_id]

    def find_by_member(self, member_id: str) -> list[AgentSession]:
        """Return all sessions bound to a specific organization member ID."""
        return [s for s in self._sessions.values() if s.member_id == member_id]

    def find_by_state(self, state: RuntimeState) -> list[AgentSession]:
        """Return all sessions in a specific lifecycle state."""
        return [s for s in self._sessions.values() if s.state == state]

    @property
    def total(self) -> int:
        """Total number of registered sessions."""
        return len(self._sessions)
