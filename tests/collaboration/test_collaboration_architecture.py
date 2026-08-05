"""Architecture Validation Tests for ACR-007 Phase C1 — Engineering Collaboration Architecture.

Validates:
- Immutability and schema integrity of collaboration models
- Enums and canonical message types
- Contracts and abstract method signatures
- Timeline logging and report structure
- Read-only integration boundaries (no execution, no AI calls, no runtime mutation)
"""

from __future__ import annotations

from typing import get_type_hints

import pytest

from runtime.collaboration import (
    ApprovalCoordinatorContract,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    ArtifactReference,
    CollaborationCoordinatorContract,
    CollaborationReport,
    CollaborationSession,
    Conversation,
    Handoff,
    HandoffManagerContract,
    HandoffStatus,
    Message,
    MessageBusContract,
    MessageThread,
    MessageType,
    ReviewCoordinatorContract,
    ReviewRequest,
    SharedArtifactManagerContract,
    Timeline,
    TimelineEvent,
    TimelineEventType,
)


class TestCollaborationEnums:
    def test_message_types(self):
        expected = {
            "question", "answer", "task", "handoff", "status",
            "review", "approval", "warning", "error", "info"
        }
        actual = {t.value for t in MessageType}
        assert actual == expected

    def test_handoff_status_values(self):
        expected = {"pending", "accepted", "rejected", "completed", "cancelled"}
        actual = {s.value for s in HandoffStatus}
        assert actual == expected

    def test_approval_status_values(self):
        expected = {"pending", "approved", "rejected", "changes_requested"}
        actual = {s.value for s in ApprovalStatus}
        assert actual == expected

    def test_timeline_event_types(self):
        expected_base = {"message", "handoff", "review", "approval", "artifact_shared", "state_changed"}
        c2_new = {"conversation_created", "thread_created", "message_published", "message_delivered", "thread_closed", "conversation_closed"}
        c3_new = {"handoff_created", "handoff_accepted", "handoff_rejected", "handoff_completed", "handoff_cancelled"}
        actual = {t.value for t in TimelineEventType}
        assert expected_base.issubset(actual)
        assert c2_new.issubset(actual)
        assert c3_new.issubset(actual)


class TestCollaborationModelsImmutability:
    def test_message_model_frozen(self):
        msg = Message(
            message_id="msg-101",
            sender_session_id="sess-agent-1",
            sender_member_id="mem-1",
            message_type=MessageType.QUESTION,
            content="What is the database schema?",
        )
        with pytest.raises(Exception):
            msg.content = "Mutated"

    def test_artifact_reference_frozen(self):
        ref = ArtifactReference(
            reference_id="ref-101",
            artifact_id="art-db-schema-001",
            owner_session_id="sess-agent-1",
            owner_member_id="mem-1",
        )
        with pytest.raises(Exception):
            ref.artifact_id = "mutated"

    def test_handoff_frozen(self):
        ref = ArtifactReference(
            reference_id="ref-101",
            artifact_id="art-db-schema-001",
            owner_session_id="sess-agent-1",
            owner_member_id="mem-1",
        )
        handoff = Handoff(
            handoff_id="hdf-101",
            producer_session_id="sess-agent-1",
            consumer_session_id="sess-agent-2",
            artifact_reference=ref,
            reason="Database schema ready for implementation",
        )
        with pytest.raises(Exception):
            handoff.status = HandoffStatus.ACCEPTED

    def test_approval_request_frozen(self):
        approval = ApprovalRequest(
            approval_id="appr-101",
            requester_session_id="sess-agent-1",
            reason="Infrastructure change approval",
        )
        with pytest.raises(Exception):
            approval.status = ApprovalStatus.APPROVED

    def test_timeline_event_frozen(self):
        evt = TimelineEvent(
            event_id="evt-101",
            event_type=TimelineEventType.MESSAGE,
            session_id="sess-agent-1",
            description="Message published",
        )
        with pytest.raises(Exception):
            evt.description = "mutated"

    def test_collaboration_session_frozen(self):
        collab = CollaborationSession(
            collaboration_id="collab-101",
            blueprint_id="bp-101",
            agent_session_ids=["sess-agent-1", "sess-agent-2"],
        )
        with pytest.raises(Exception):
            collab.blueprint_id = "mutated"

    def test_json_serialization_round_trip(self):
        msg = Message(
            message_id="msg-201",
            sender_session_id="sess-agent-1",
            sender_member_id="mem-1",
            message_type=MessageType.TASK,
            content="Execute migrations",
        )
        d = msg.model_dump(mode="json")
        assert d["message_id"] == "msg-201"
        assert d["message_type"] == "task"

        ref = ArtifactReference(
            reference_id="ref-201",
            artifact_id="art-201",
            owner_session_id="sess-1",
            owner_member_id="mem-1",
        )
        report = CollaborationReport(
            report_id="rep-201",
            collaboration_id="collab-201",
            total_messages=5,
            total_handoffs=2,
            completed_handoffs=[],
            total_approvals=1,
            approved_count=1,
            timeline=Timeline(timeline_id="tl-201", session_id="sess-1"),
            summary="Collaboration completed successfully.",
        )
        rep_d = report.model_dump(mode="json")
        assert rep_d["report_id"] == "rep-201"
        assert rep_d["total_messages"] == 5


class TestCollaborationContracts:
    def test_contracts_are_abstract(self):
        with pytest.raises(TypeError):
            MessageBusContract()

        with pytest.raises(TypeError):
            HandoffManagerContract()

        with pytest.raises(TypeError):
            SharedArtifactManagerContract()

        with pytest.raises(TypeError):
            ApprovalCoordinatorContract()

        with pytest.raises(TypeError):
            ReviewCoordinatorContract()

        with pytest.raises(TypeError):
            CollaborationCoordinatorContract()


class TestReadonlyIntegrationBoundaries:
    def test_collaboration_does_not_modify_agent_runtime(self):
        from runtime.agent.models import AgentSession, RuntimeState
        session = AgentSession(
            session_id="sess-arch-001",
            member_id="mem-1",
            role_id="role-1",
            role_title="Backend Dev",
            blueprint_id="bp-101",
            state=RuntimeState.RUNNING,
        )
        # Create a message referencing the session
        msg = Message(
            message_id="msg-arch-001",
            sender_session_id=session.session_id,
            sender_member_id=session.member_id,
            message_type=MessageType.INFO,
            content="Session status update",
        )
        # Verify agent session state is untouched
        assert session.state == RuntimeState.RUNNING
        assert len(session.events) == 0
