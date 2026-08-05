"""Concrete ArtifactCollector for OniRoute Agent Runtime (ACR-006 Phase R3).

Registers ArtifactRecord entries produced by agent sessions.
No filesystem writes. No AI calls. No execution.
"""

from __future__ import annotations

from .contracts import ArtifactCollectorContract
from .models import AgentSession, ArtifactRecord


class ArtifactCollector(ArtifactCollectorContract):
    """Concrete append-only ArtifactCollector. Stores records in-memory per session."""

    def __init__(self) -> None:
        self._store: dict[str, list[ArtifactRecord]] = {}

    def register_artifact(self, session: AgentSession, artifact: ArtifactRecord) -> ArtifactRecord:
        """Register an artifact produced by an agent session."""
        if session.session_id not in self._store:
            self._store[session.session_id] = []
        self._store[session.session_id].append(artifact)
        session.artifacts.append(artifact)
        return artifact

    def get_artifacts(self, session_id: str) -> list[ArtifactRecord]:
        """Retrieve all artifacts collected for a specific session ID."""
        return list(self._store.get(session_id, []))

    @property
    def total(self) -> int:
        """Total artifact count across all sessions."""
        return sum(len(v) for v in self._store.values())
