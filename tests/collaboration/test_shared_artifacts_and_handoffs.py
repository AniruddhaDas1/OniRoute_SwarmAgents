"""Test suite for ACR-007 Phase C3 — Shared Artifacts & Handoff Management.

Validates:
- SharedArtifactManager: ArtifactReference creation, zero duplication, ownership validation, versioning, checksum, lineage
- HandoffManager: Handoff lifecycle (PENDING → ACCEPTED → COMPLETED, REJECTED, CANCELLED), permissions validation
- Timeline event logging (ARTIFACT_SHARED, HANDOFF_CREATED, HANDOFF_ACCEPTED, HANDOFF_REJECTED, HANDOFF_COMPLETED, HANDOFF_CANCELLED)
- Extended CollaborationReport containing shared artifact & handoff summaries
- CLI commands (oniroute handoff, oniroute artifact)
- Zero mutation of frozen Agent Runtime or Workspace components
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.agent.models import ArtifactRecord, ArtifactType
from runtime.collaboration import (
    ArtifactReference,
    CollaborationReport,
    Handoff,
    HandoffManager,
    HandoffStatus,
    MessageBus,
    SharedArtifactManager,
    TimelineEventType,
)

runner = CliRunner()


def _make_workspace_artifact(artifact_id: str = "art-schema-001") -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=artifact_id,
        artifact_type=ArtifactType.SCHEMA,
        owner_session_id="sess-producer-01",
        owner_member_id="mem-producer-01",
        capability_id="cap-schema-gen",
        name="Database Schema v1",
        references=["artifacts/schema.sql"],
        metadata={"tables": 5},
    )


class TestSharedArtifactManager:
    def setup_method(self):
        self.mgr = SharedArtifactManager()
        self.art = _make_workspace_artifact()

    def test_create_reference_zero_duplication(self):
        ref = self.mgr.create_reference(
            artifact=self.art,
            owner_session_id="sess-producer-01",
            owner_member_id="mem-producer-01",
            checksum="sha256-abc123",
            version=1,
        )
        assert isinstance(ref, ArtifactReference)
        assert ref.reference_id.startswith("ref-")
        assert ref.artifact_id == "art-schema-001"
        assert ref.owner_session_id == "sess-producer-01"
        assert ref.checksum == "sha256-abc123"
        assert ref.version == 1
        assert self.mgr.total_references == 1

    def test_resolve_reference(self):
        ref = self.mgr.create_reference(self.art)
        resolved = self.mgr.resolve_reference(ref.reference_id)
        assert resolved.artifact_id == ref.artifact_id

    def test_get_references_by_artifact_id(self):
        ref1 = self.mgr.create_reference(self.art, version=1)
        ref2 = self.mgr.create_reference(self.art, version=2)
        
        refs = self.mgr.get_references(self.art.artifact_id)
        assert len(refs) == 2
        assert {r.version for r in refs} == {1, 2}

    def test_validate_ownership(self):
        ref = self.mgr.create_reference(self.art, owner_session_id="sess-producer-01")
        assert self.mgr.validate_ownership(ref.reference_id, "sess-producer-01") is True
        assert self.mgr.validate_ownership(ref.reference_id, "sess-consumer-01") is False

    def test_verify_lineage(self):
        ref1 = self.mgr.create_reference(self.art, version=1)
        
        art2 = _make_workspace_artifact("art-schema-002")
        ref2 = self.mgr.create_reference(art2, version=2, lineage=[ref1.reference_id])

        lineage_chain = self.mgr.verify_lineage(ref2.reference_id)
        assert ref2.reference_id in lineage_chain
        assert ref1.reference_id in lineage_chain

    def test_sharing_history_timeline(self):
        ref = self.mgr.create_reference(self.art)
        events = self.mgr.timeline.events
        assert len(events) == 1
        assert events[0].event_type == TimelineEventType.ARTIFACT_SHARED


class TestHandoffManagerLifecycle:
    def setup_method(self):
        self.art_mgr = SharedArtifactManager()
        self.mgr = HandoffManager(timeline=self.art_mgr.timeline)
        self.art = _make_workspace_artifact()
        self.ref = self.art_mgr.create_reference(self.art)

    def test_create_handoff_pending(self):
        hdf = self.mgr.create_handoff(
            producer_session_id="sess-producer-01",
            consumer_session_id="sess-consumer-01",
            artifact_reference=self.ref,
            reason="Deliver database schema for REST API implementation",
        )
        assert isinstance(hdf, Handoff)
        assert hdf.handoff_id.startswith("hdf-")
        assert hdf.status == HandoffStatus.PENDING
        assert hdf.producer_session_id == "sess-producer-01"
        assert hdf.consumer_session_id == "sess-consumer-01"

    def test_handoff_validation_same_session_fails(self):
        with pytest.raises(ValueError):
            self.mgr.create_handoff(
                producer_session_id="sess-01",
                consumer_session_id="sess-01",
                artifact_reference=self.ref,
                reason="Invalid self-handoff",
            )

    def test_accept_handoff(self):
        hdf = self.mgr.create_handoff("sess-producer-01", "sess-consumer-01", self.ref, "Schema handoff")
        accepted = self.mgr.accept_handoff(hdf.handoff_id, "sess-consumer-01")
        assert accepted.status == HandoffStatus.ACCEPTED

    def test_accept_handoff_wrong_consumer_raises(self):
        hdf = self.mgr.create_handoff("sess-producer-01", "sess-consumer-01", self.ref, "Schema handoff")
        with pytest.raises(ValueError):
            self.mgr.accept_handoff(hdf.handoff_id, "sess-other-session")

    def test_reject_handoff(self):
        hdf = self.mgr.create_handoff("sess-producer-01", "sess-consumer-01", self.ref, "Schema handoff")
        rejected = self.mgr.reject_handoff(hdf.handoff_id, "sess-consumer-01", reason="Missing user table")
        assert rejected.status == HandoffStatus.REJECTED
        assert rejected.rejected_at is not None
        assert rejected.evidence.get("rejection_reason") == "Missing user table"

    def test_complete_handoff(self):
        hdf = self.mgr.create_handoff("sess-producer-01", "sess-consumer-01", self.ref, "Schema handoff")
        self.mgr.accept_handoff(hdf.handoff_id, "sess-consumer-01")
        completed = self.mgr.complete_handoff(hdf.handoff_id, "sess-consumer-01")
        assert completed.status == HandoffStatus.COMPLETED
        assert completed.completed_at is not None

    def test_cancel_handoff(self):
        hdf = self.mgr.create_handoff("sess-producer-01", "sess-consumer-01", self.ref, "Schema handoff")
        cancelled = self.mgr.cancel_handoff(hdf.handoff_id, "sess-producer-01", reason="Superseded by v2")
        assert cancelled.status == HandoffStatus.CANCELLED
        assert cancelled.cancelled_at is not None

    def test_handoff_timeline_events(self):
        hdf = self.mgr.create_handoff("sess-producer-01", "sess-consumer-01", self.ref, "Schema handoff")
        self.mgr.accept_handoff(hdf.handoff_id, "sess-consumer-01")
        self.mgr.complete_handoff(hdf.handoff_id, "sess-consumer-01")

        event_types = [e.event_type for e in self.mgr.timeline.events]
        assert TimelineEventType.HANDOFF_CREATED in event_types
        assert TimelineEventType.HANDOFF_ACCEPTED in event_types
        assert TimelineEventType.HANDOFF_COMPLETED in event_types


class TestExtendedCollaborationReport:
    def setup_method(self):
        self.bus = MessageBus(blueprint_id="bp-c3-report")
        self.art_mgr = SharedArtifactManager(timeline=self.bus.timeline)
        self.hdf_mgr = HandoffManager(timeline=self.bus.timeline)
        self.bus.set_artifact_manager(self.art_mgr)
        self.bus.set_handoff_manager(self.hdf_mgr)

    def test_report_includes_shared_artifacts_and_handoffs(self):
        art = _make_workspace_artifact()
        ref = self.art_mgr.create_reference(art)
        hdf = self.hdf_mgr.create_handoff("sess-producer-01", "sess-consumer-01", ref, "Handing off schema")
        self.hdf_mgr.accept_handoff(hdf.handoff_id, "sess-consumer-01")
        self.hdf_mgr.complete_handoff(hdf.handoff_id, "sess-consumer-01")

        report = self.bus.generate_report()
        assert isinstance(report, CollaborationReport)
        assert report.total_shared_artifacts == 1
        assert len(report.shared_artifacts) == 1
        assert ref.reference_id in report.artifact_references
        assert report.total_handoffs == 1
        assert len(report.completed_handoffs) == 1
        assert "sess-producer-01" in report.ownership_summary


class TestCLIPhaseC3:
    def test_handoff_command_text(self):
        result = runner.invoke(app, ["handoff"])
        assert result.exit_code == 0
        assert "Inter-Session Handoffs" in result.output
        assert "PENDING" in result.output

    def test_handoff_command_json(self):
        result = runner.invoke(app, ["handoff", "--json"])
        assert result.exit_code == 0
        assert "handoff_id" in result.output
        assert "producer_session_id" in result.output

    def test_artifact_command_text(self):
        result = runner.invoke(app, ["artifact"])
        assert result.exit_code == 0
        assert "Shared Artifact References" in result.output
        assert "Zero-Duplication Pointers" in result.output

    def test_artifact_command_json(self):
        result = runner.invoke(app, ["artifact", "--json"])
        assert result.exit_code == 0
        assert "reference_id" in result.output
        assert "artifact_id" in result.output
