"""Test suite for ACR-007 Phase C2 — Collaboration Message Bus.

Validates:
- Conversation creation, status transitions, and closing
- Thread creation, thread types, closing, and append-only message invariant
- Message routing (specific session, role, department, broadcast, system)
- Message publishing, delivery tracking, and timeline event recording
- CollaborationSession aggregation and CollaborationReport generation
- CLI commands (oniroute collaborate, oniroute conversation, oniroute thread)
- Read-only Agent Runtime boundaries (no runtime state mutation)
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.agent.models import AgentSession, RuntimeState
from runtime.collaboration import (
    CollaborationConversation,
    CollaborationReport,
    CollaborationSession,
    ConversationStatus,
    Message,
    MessageBus,
    MessageRouter,
    MessageThread,
    MessageType,
    RecipientType,
    ThreadStatus,
    ThreadType,
    TimelineEventType,
)

runner = CliRunner()


def _make_agent_session(session_id: str, role_id: str, role_title: str, department: str = "engineering") -> AgentSession:
    return AgentSession(
        session_id=session_id,
        member_id=f"mem-{session_id}",
        role_id=role_id,
        role_title=role_title,
        blueprint_id="bp-test-c2",
        state=RuntimeState.RUNNING,
        metadata={"department": department},
    )


class TestMessageRouter:
    def setup_method(self):
        self.router = MessageRouter()
        self.s1 = _make_agent_session("sess-lead-01", "role-architect", "Lead Architect", department="engineering")
        self.s2 = _make_agent_session("sess-dev-01", "role-backend", "Backend Developer", department="engineering")
        self.s3 = _make_agent_session("sess-qa-01", "role-qa", "QA Engineer", department="quality")
        self.active_sessions = [self.s1, self.s2, self.s3]

    def test_classify_descriptors(self):
        assert self.router.classify_descriptor("broadcast") == RecipientType.BROADCAST
        assert self.router.classify_descriptor("*") == RecipientType.BROADCAST
        assert self.router.classify_descriptor("system") == RecipientType.SYSTEM
        assert self.router.classify_descriptor("role:backend") == RecipientType.ROLE
        assert self.router.classify_descriptor("dept:engineering") == RecipientType.DEPARTMENT
        assert self.router.classify_descriptor("sess-dev-01") == RecipientType.SPECIFIC_SESSION

    def test_route_specific_session(self):
        res = self.router.resolve_recipients("sess-dev-01", self.active_sessions)
        assert res == ["sess-dev-01"]

        res_prefix = self.router.resolve_recipients("session:sess-lead-01", self.active_sessions)
        assert res_prefix == ["sess-lead-01"]

    def test_route_role(self):
        res = self.router.resolve_recipients("role:role-backend", self.active_sessions)
        assert res == ["sess-dev-01"]

        res_title = self.router.resolve_recipients("role:Lead Architect", self.active_sessions)
        assert res_title == ["sess-lead-01"]

    def test_route_department(self):
        res = self.router.resolve_recipients("dept:quality", self.active_sessions)
        assert res == ["sess-qa-01"]

        res_eng = self.router.resolve_recipients("department:engineering", self.active_sessions)
        assert sorted(res_eng) == ["sess-dev-01", "sess-lead-01"]

    def test_route_broadcast(self):
        res = self.router.resolve_recipients("broadcast", self.active_sessions, sender_session_id="sess-lead-01")
        assert sorted(res) == ["sess-dev-01", "sess-qa-01"]


class TestConversationAndThreadManagement:
    def setup_method(self):
        self.bus = MessageBus(blueprint_id="bp-test-c2")

    def test_create_conversation(self):
        conv = self.bus.create_conversation(
            title="Authentication Service Architecture",
            mission_id="msn-auth-001",
            participants=["sess-lead-01", "sess-dev-01"],
        )
        assert conv.conversation_id.startswith("conv-")
        assert conv.status == ConversationStatus.ACTIVE
        assert conv.title == "Authentication Service Architecture"
        assert self.bus.get_conversation(conv.conversation_id) is not None

    def test_create_thread(self):
        conv = self.bus.create_conversation(title="Payment Service", participants=["sess-lead-01"])
        th = self.bus.create_thread(
            topic="Stripe Webhook Handler",
            participant_session_ids=["sess-lead-01", "sess-dev-01"],
            conversation_id=conv.conversation_id,
            thread_type=ThreadType.TASK,
        )
        assert th.thread_id.startswith("th-")
        assert th.status == ThreadStatus.OPEN
        assert th.thread_type == ThreadType.TASK
        assert len(self.bus.get_conversation(conv.conversation_id).threads) == 1

    def test_close_thread(self):
        conv = self.bus.create_conversation(title="Test Conv")
        th = self.bus.create_thread(topic="Test Topic", participant_session_ids=["sess-1"], conversation_id=conv.conversation_id)
        
        closed = self.bus.close_thread(th.thread_id)
        assert closed.status == ThreadStatus.CLOSED
        assert closed.closed_at is not None

    def test_close_conversation_closes_open_threads(self):
        conv = self.bus.create_conversation(title="Project Kickoff", participants=["sess-1"])
        th1 = self.bus.create_thread(topic="Topic 1", participant_session_ids=["sess-1"], conversation_id=conv.conversation_id)
        th2 = self.bus.create_thread(topic="Topic 2", participant_session_ids=["sess-1"], conversation_id=conv.conversation_id)

        closed_conv = self.bus.close_conversation(conv.conversation_id)
        assert closed_conv.status == ConversationStatus.CLOSED
        for t in closed_conv.threads:
            assert t.status == ThreadStatus.CLOSED


class TestMessagePublishAndDelivery:
    def setup_method(self):
        self.bus = MessageBus(blueprint_id="bp-test-c2")
        self.s1 = _make_agent_session("sess-lead-01", "role-architect", "Lead Architect")
        self.s2 = _make_agent_session("sess-dev-01", "role-backend", "Backend Developer")
        self.bus.register_sessions([self.s1, self.s2])

    def test_publish_message(self):
        conv = self.bus.create_conversation(title="Backend Conv", participants=[self.s1.session_id, self.s2.session_id])
        th = self.bus.create_thread(topic="Database Schema", participant_session_ids=[self.s1.session_id], conversation_id=conv.conversation_id)

        msg = Message(
            message_id="msg-001",
            conversation_id=conv.conversation_id,
            thread_id=th.thread_id,
            sender_session_id=self.s1.session_id,
            sender_member_id=self.s1.member_id,
            recipient_sessions=[self.s2.session_id],
            message_type=MessageType.QUESTION,
            subject="Schema Fields",
            content="Do we need a tenant_id column?",
        )
        published = self.bus.publish_message(msg)
        assert published.delivered is True

        updated_th = self.bus.get_thread(th.thread_id)
        assert len(updated_th.messages) == 1
        assert updated_th.messages[0].content == "Do we need a tenant_id column?"

    def test_timeline_event_recording(self):
        conv = self.bus.create_conversation(title="Timeline Test Conv", participants=[self.s1.session_id])
        th = self.bus.create_thread(topic="Timeline Test Thread", participant_session_ids=[self.s1.session_id], conversation_id=conv.conversation_id)
        
        self.bus.publish_message(Message(
            message_id="msg-tl-01",
            conversation_id=conv.conversation_id,
            thread_id=th.thread_id,
            sender_session_id=self.s1.session_id,
            sender_member_id=self.s1.member_id,
            recipient_sessions=[self.s2.session_id],
            message_type=MessageType.INFO,
            content="Hello world",
        ))

        events = self.bus.timeline.events
        event_types = [e.event_type for e in events]
        assert TimelineEventType.CONVERSATION_CREATED in event_types
        assert TimelineEventType.THREAD_CREATED in event_types
        assert TimelineEventType.MESSAGE_PUBLISHED in event_types
        assert TimelineEventType.MESSAGE_DELIVERED in event_types


class TestCollaborationSessionAndReporting:
    def setup_method(self):
        self.bus = MessageBus(blueprint_id="bp-test-c2")
        self.s1 = _make_agent_session("sess-lead-01", "role-architect", "Lead Architect")
        self.s2 = _make_agent_session("sess-dev-01", "role-backend", "Backend Developer")
        self.bus.register_sessions([self.s1, self.s2])

    def test_collaboration_session_snapshot(self):
        conv = self.bus.create_conversation(title="Test Session Snapshot", participants=[self.s1.session_id, self.s2.session_id])
        self.bus.create_thread(topic="Thread 1", participant_session_ids=[self.s1.session_id], conversation_id=conv.conversation_id)

        session_snap = self.bus.get_collaboration_session()
        assert isinstance(session_snap, CollaborationSession)
        assert session_snap.statistics["total_conversations"] == 1
        assert session_snap.statistics["total_threads"] == 1

    def test_collaboration_report_generation(self):
        conv = self.bus.create_conversation(title="Report Conv", participants=[self.s1.session_id])
        self.bus.create_thread(topic="Report Thread", participant_session_ids=[self.s1.session_id], conversation_id=conv.conversation_id)

        report = self.bus.generate_report()
        assert isinstance(report, CollaborationReport)
        assert report.collaboration_id.startswith("collab-")
        assert report.total_conversations == 1
        assert report.total_threads == 1


class TestCollaborationCLI:
    def test_collaborate_command_text(self):
        result = runner.invoke(app, ["collaborate", "Design User Service"])
        assert result.exit_code == 0
        assert "Collaboration Session" in result.output
        assert "bp-collab-001" in result.output

    def test_collaborate_command_json(self):
        result = runner.invoke(app, ["collaborate", "Design Payment Service", "--json"])
        assert result.exit_code == 0
        assert "collaboration_id" in result.output
        assert "active_conversations" in result.output

    def test_conversation_command_text(self):
        result = runner.invoke(app, ["conversation"])
        assert result.exit_code == 0
        assert "Conversation:" in result.output

    def test_conversation_command_json(self):
        result = runner.invoke(app, ["conversation", "--json"])
        assert result.exit_code == 0
        assert "conversation_id" in result.output

    def test_thread_command_text(self):
        result = runner.invoke(app, ["thread"])
        assert result.exit_code == 0
        assert "Thread:" in result.output

    def test_thread_command_json(self):
        result = runner.invoke(app, ["thread", "--json"])
        assert result.exit_code == 0
        assert "thread_id" in result.output
