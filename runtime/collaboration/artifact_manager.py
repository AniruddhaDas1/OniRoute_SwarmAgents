"""Shared Artifact Manager for Engineering Collaboration (ACR-007 Phase C3).

Implements SharedArtifactManagerContract to track shared artifact references across sessions
without duplicating files or copying content.

Artifacts remain strictly owned by the Workspace (ArtifactRecord).
Collaboration creates lightweight, immutable ArtifactReference pointers.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from runtime.agent.models import ArtifactRecord
from .contracts import SharedArtifactManagerContract
from .models import ArtifactReference, TimelineEventType
from .timeline import CollaborationTimeline


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class SharedArtifactManager(SharedArtifactManagerContract):
    """Concrete implementation of SharedArtifactManagerContract.

    Tracks shared artifact references, lineage chains, ownership validation, and sharing history.
    """

    def __init__(self, timeline: CollaborationTimeline | None = None) -> None:
        self._timeline = timeline or CollaborationTimeline()

        self._references: dict[str, ArtifactReference] = {}
        """reference_id → ArtifactReference"""

        self._artifact_to_refs: dict[str, list[str]] = {}
        """artifact_id → list of reference_ids"""

        self._session_to_refs: dict[str, list[str]] = {}
        """session_id → list of reference_ids"""

    @property
    def timeline(self) -> CollaborationTimeline:
        return self._timeline

    @property
    def total_references(self) -> int:
        return len(self._references)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_reference(
        self,
        artifact: ArtifactRecord,
        owner_session_id: str | None = None,
        owner_member_id: str | None = None,
        metadata: dict | None = None,
        evidence: dict | None = None,
        checksum: str | None = None,
        version: int = 1,
        lineage: list[str] | None = None,
    ) -> ArtifactReference:
        """Create a shared ArtifactReference pointing to a workspace ArtifactRecord.

        Never copies or duplicates the file content.
        """
        ref_id = f"ref-{uuid.uuid4().hex[:8]}"
        sid = owner_session_id or artifact.owner_session_id
        mid = owner_member_id or artifact.owner_member_id
        
        # Calculate fallback checksum from metadata or artifact ID if not provided
        calc_checksum = checksum or hashlib.sha256(f"{artifact.artifact_id}:{version}".encode()).hexdigest()[:16]

        merged_metadata = dict(artifact.metadata)
        if metadata:
            merged_metadata.update(metadata)

        ref = ArtifactReference(
            reference_id=ref_id,
            artifact_id=artifact.artifact_id,
            owner_session_id=sid,
            owner_member_id=mid,
            artifact_type=artifact.artifact_type.value if hasattr(artifact.artifact_type, "value") else str(artifact.artifact_type),
            workspace_path=artifact.references[0] if artifact.references else f"artifacts/{artifact.artifact_id}",
            lineage=list(lineage or artifact.lineage or []),
            metadata=merged_metadata,
            evidence=evidence or {},
            checksum=calc_checksum,
            version=version,
            shared_at=_utcnow(),
        )

        self._references[ref_id] = ref
        self._artifact_to_refs.setdefault(artifact.artifact_id, []).append(ref_id)
        self._session_to_refs.setdefault(sid, []).append(ref_id)

        self._timeline.record_event(
            event_type=TimelineEventType.ARTIFACT_SHARED,
            session_id=sid,
            description=f"Shared artifact reference created: '{artifact.name}' ({ref_id})",
            payload={
                "reference_id": ref_id,
                "artifact_id": artifact.artifact_id,
                "owner_session_id": sid,
                "version": version,
                "checksum": calc_checksum,
            },
        )
        return ref

    def share_artifact(
        self,
        artifact_id: str,
        owner_session_id: str,
        owner_member_id: str,
        metadata: dict | None = None,
    ) -> ArtifactReference:
        """Implement SharedArtifactManagerContract.share_artifact."""
        ref_id = f"ref-{uuid.uuid4().hex[:8]}"
        ref = ArtifactReference(
            reference_id=ref_id,
            artifact_id=artifact_id,
            owner_session_id=owner_session_id,
            owner_member_id=owner_member_id,
            metadata=metadata or {},
            shared_at=_utcnow(),
        )
        self._references[ref_id] = ref
        self._artifact_to_refs.setdefault(artifact_id, []).append(ref_id)
        self._session_to_refs.setdefault(owner_session_id, []).append(ref_id)

        self._timeline.record_event(
            event_type=TimelineEventType.ARTIFACT_SHARED,
            session_id=owner_session_id,
            description=f"Artifact '{artifact_id}' shared as reference ({ref_id})",
            payload={"reference_id": ref_id, "artifact_id": artifact_id, "owner_session_id": owner_session_id},
        )
        return ref

    def resolve_reference(self, reference_id: str) -> ArtifactReference:
        """Retrieve an ArtifactReference by its ID."""
        if reference_id not in self._references:
            raise KeyError(f"ArtifactReference '{reference_id}' not found.")
        return self._references[reference_id]

    def get_references(self, artifact_id: str) -> list[ArtifactReference]:
        """Retrieve all shared references pointing to a given workspace artifact ID."""
        ref_ids = self._artifact_to_refs.get(artifact_id, [])
        return [self._references[rid] for rid in ref_ids if rid in self._references]

    def get_references_for_session(self, session_id: str) -> list[ArtifactReference]:
        """Retrieve all shared artifact references owned by a specific session."""
        ref_ids = self._session_to_refs.get(session_id, [])
        return [self._references[rid] for rid in ref_ids if rid in self._references]

    def validate_ownership(self, reference_id: str, session_id: str) -> bool:
        """Return True if session_id is the legitimate owner of the referenced artifact."""
        if reference_id not in self._references:
            return False
        return self._references[reference_id].owner_session_id == session_id

    def verify_lineage(self, reference_id: str) -> list[str]:
        """Verify and return the lineage chain of parent references/artifacts."""
        ref = self.resolve_reference(reference_id)
        chain = [ref.reference_id]
        for parent in ref.lineage:
            if parent in self._references:
                chain.extend(self.verify_lineage(parent))
            else:
                chain.append(parent)
        return list(dict.fromkeys(chain))

    def get_sharing_history(self, reference_id: str) -> list[dict]:
        """Retrieve the timeline history of sharing events for a reference."""
        history = []
        for evt in self._timeline.events:
            if evt.payload.get("reference_id") == reference_id or evt.payload.get("artifact_id") == reference_id:
                history.append(evt.model_dump(mode="json"))
        return history

    def get_all_references(self) -> tuple[ArtifactReference, ...]:
        """Return a tuple of all registered references."""
        return tuple(self._references.values())
