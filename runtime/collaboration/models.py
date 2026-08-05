"""Immutable Data Models for Engineering Collaboration Architecture (ACR-007 Phase C1).

Defines all declarative, immutable Pydantic models for inter-session communication,
handoffs, shared artifacts, approvals, reviews, timelines, and collaboration reports.

Architecture-only specifications. No AI execution, no runtime scheduling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Message Vocabulary & Enums
# ---------------------------------------------------------------------------

class MessageType(str, Enum):
    """Canonical message categories supported by the Collaboration Message Bus."""

    QUESTION = "question"
    ANSWER = "answer"
    TASK = "task"
    HANDOFF = "handoff"
    STATUS = "status"
    REVIEW = "review"
    APPROVAL = "approval"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class HandoffStatus(str, Enum):
    """Status lifecycle for an inter-session handoff."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"


class ApprovalStatus(str, Enum):
    """Status outcomes for an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class TimelineEventType(str, Enum):
    """Categories of timeline events captured during collaboration."""

    MESSAGE = "message"
    HANDOFF = "handoff"
    REVIEW = "review"
    APPROVAL = "approval"
    ARTIFACT_SHARED = "artifact_shared"
    STATE_CHANGED = "state_changed"


# ---------------------------------------------------------------------------
# Core Message Models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    """Immutable message record sent between agent sessions."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(..., description="Unique message identifier.")
    sender_session_id: str = Field(..., description="AgentSession ID of the sender.")
    sender_member_id: str = Field(..., description="Organization Member ID of the sender.")
    recipient_session_id: str | None = Field(
        default=None, description="Target AgentSession ID (None for broadcast messages)."
    )
    message_type: MessageType = Field(..., description="Canonical message type.")
    subject: str = Field(default="", description="Subject or brief title of the message.")
    content: str = Field(..., description="Body content of the message.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Structured message payload.")
    thread_id: str | None = Field(default=None, description="Parent MessageThread ID if part of a thread.")
    in_reply_to_id: str | None = Field(default=None, description="Parent Message ID being replied to.")
    timestamp: str = Field(default_factory=_utcnow, description="ISO-8601 UTC timestamp.")


class MessageThread(BaseModel):
    """Immutable thread grouping related messages."""

    model_config = ConfigDict(frozen=True)

    thread_id: str = Field(..., description="Unique thread identifier.")
    topic: str = Field(..., description="Thread topic or objective.")
    participant_session_ids: list[str] = Field(
        default_factory=list, description="AgentSession IDs participating in this thread."
    )
    messages: list[Message] = Field(default_factory=list, description="Chronological message list.")
    created_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC thread creation timestamp.")


class Conversation(BaseModel):
    """Immutable conversation container between sessions."""

    model_config = ConfigDict(frozen=True)

    conversation_id: str = Field(..., description="Unique conversation identifier.")
    title: str = Field(..., description="Conversation title.")
    threads: list[MessageThread] = Field(default_factory=list, description="List of message threads.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible metadata.")
    created_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC creation timestamp.")


# ---------------------------------------------------------------------------
# Shared Artifact Reference
# ---------------------------------------------------------------------------

class ArtifactReference(BaseModel):
    """Immutable pointer to a shared artifact. Does not duplicate artifact content."""

    model_config = ConfigDict(frozen=True)

    reference_id: str = Field(..., description="Unique reference identifier.")
    artifact_id: str = Field(..., description="ID of the underlying ArtifactRecord in workspace.")
    owner_session_id: str = Field(..., description="AgentSession ID that produced the artifact.")
    owner_member_id: str = Field(..., description="Member ID that produced the artifact.")
    lineage: list[str] = Field(default_factory=list, description="Parent artifact reference IDs.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible reference metadata.")
    shared_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC timestamp when shared.")


# ---------------------------------------------------------------------------
# Handoff Models
# ---------------------------------------------------------------------------

class Handoff(BaseModel):
    """Immutable record of an artifact/task handoff between producer and consumer agents."""

    model_config = ConfigDict(frozen=True)

    handoff_id: str = Field(..., description="Unique handoff identifier.")
    producer_session_id: str = Field(..., description="AgentSession ID initiating the handoff.")
    consumer_session_id: str = Field(..., description="Target AgentSession ID receiving the handoff.")
    artifact_reference: ArtifactReference = Field(..., description="Pointer to the shared artifact.")
    reason: str = Field(..., description="Rationale for the handoff.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Contextual verification evidence.")
    status: HandoffStatus = Field(default=HandoffStatus.PENDING, description="Current handoff status.")
    timestamp: str = Field(default_factory=_utcnow, description="ISO-8601 UTC handoff timestamp.")
    completed_at: str | None = Field(default=None, description="ISO-8601 UTC completion timestamp.")


# ---------------------------------------------------------------------------
# Approval Models
# ---------------------------------------------------------------------------

class ApprovalDecision(BaseModel):
    """Immutable record of a decision rendered on an ApprovalRequest."""

    model_config = ConfigDict(frozen=True)

    decision_id: str = Field(..., description="Unique decision identifier.")
    approval_id: str = Field(..., description="Associated ApprovalRequest ID.")
    status: ApprovalStatus = Field(..., description="Approval decision outcome.")
    actor_session_id: str = Field(..., description="AgentSession ID rendering the decision.")
    reason: str = Field(..., description="Rationale for the decision.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Evidence supporting decision.")
    decided_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC decision timestamp.")


class ApprovalRequest(BaseModel):
    """Immutable request for human or governance approval."""

    model_config = ConfigDict(frozen=True)

    approval_id: str = Field(..., description="Unique approval request identifier.")
    requester_session_id: str = Field(..., description="AgentSession ID requesting approval.")
    approver_session_id: str | None = Field(
        default=None, description="Target AgentSession or human approver ID."
    )
    artifact_references: list[ArtifactReference] = Field(
        default_factory=list, description="Artifacts under approval review."
    )
    reason: str = Field(..., description="Rationale for requiring approval.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Contextual evidence.")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Approval status.")
    outcome: ApprovalDecision | None = Field(default=None, description="Decided outcome, if completed.")
    requested_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC request timestamp.")


# ---------------------------------------------------------------------------
# Review Models
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    """Immutable request for inter-agent peer review."""

    model_config = ConfigDict(frozen=True)

    review_id: str = Field(..., description="Unique review request identifier.")
    reviewer_session_id: str = Field(..., description="AgentSession ID requested to conduct review.")
    author_session_id: str = Field(..., description="AgentSession ID that authored the work.")
    artifact_references: list[ArtifactReference] = Field(
        default_factory=list, description="Artifacts submitted for peer review."
    )
    reason: str = Field(..., description="Reason for peer review request.")
    requested_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC request timestamp.")


# ---------------------------------------------------------------------------
# Timeline Models
# ---------------------------------------------------------------------------

class TimelineEvent(BaseModel):
    """Immutable chronological timeline event entry."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(..., description="Unique timeline event identifier.")
    event_type: TimelineEventType = Field(..., description="Category of timeline event.")
    session_id: str = Field(..., description="Associated AgentSession ID.")
    description: str = Field(..., description="Human-readable event description.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Structured event payload.")
    timestamp: str = Field(default_factory=_utcnow, description="ISO-8601 UTC event timestamp.")


class Timeline(BaseModel):
    """Immutable execution timeline log capturing all collaboration events."""

    model_config = ConfigDict(frozen=True)

    timeline_id: str = Field(..., description="Unique timeline identifier.")
    session_id: str = Field(..., description="Target session or collaboration context ID.")
    events: list[TimelineEvent] = Field(default_factory=list, description="Chronological timeline events.")
    created_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC creation timestamp.")


# ---------------------------------------------------------------------------
# Collaboration Session & Reporting
# ---------------------------------------------------------------------------

class CollaborationSession(BaseModel):
    """Immutable collaboration session binding active agent sessions."""

    model_config = ConfigDict(frozen=True)

    collaboration_id: str = Field(..., description="Unique collaboration session identifier.")
    blueprint_id: str = Field(..., description="ExecutionBlueprint ID reference.")
    agent_session_ids: list[str] = Field(
        default_factory=list, description="Bound AgentSession IDs participating in collaboration."
    )
    active_conversations: list[Conversation] = Field(
        default_factory=list, description="Conversations within this collaboration session."
    )
    handoffs: list[Handoff] = Field(default_factory=list, description="Handoffs recorded.")
    approvals: list[ApprovalRequest] = Field(default_factory=list, description="Approvals recorded.")
    created_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC creation timestamp.")


class CollaborationReport(BaseModel):
    """Immutable report summarizing collaboration session outcomes."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique report identifier.")
    collaboration_id: str = Field(..., description="Target CollaborationSession ID.")
    total_messages: int = Field(default=0, description="Total messages sent across all threads.")
    total_handoffs: int = Field(default=0, description="Total handoffs initiated.")
    completed_handoffs: int = Field(default=0, description="Total handoffs successfully accepted.")
    total_approvals: int = Field(default=0, description="Total approval requests processed.")
    approved_count: int = Field(default=0, description="Total approvals granted.")
    timeline: Timeline = Field(..., description="Full collaboration timeline log.")
    summary: str = Field(default="", description="Human-readable collaboration summary.")
    generated_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC report timestamp.")
