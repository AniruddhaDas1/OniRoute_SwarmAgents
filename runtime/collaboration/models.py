"""Immutable Data Models for Engineering Collaboration (ACR-007 Phase C1, C2, C3 & C4).

Defines all declarative, immutable Pydantic models for inter-session communication,
conversations, threads, messages, shared artifact references, handoffs, reviews, approvals,
timelines, and reports.

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


class ConversationStatus(str, Enum):
    """Lifecycle status for a CollaborationConversation."""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ThreadType(str, Enum):
    """Canonical types of communication threads."""

    QUESTION = "question"
    TASK = "task"
    REVIEW = "review"
    APPROVAL = "approval"
    DISCUSSION = "discussion"
    BUG = "bug"
    DECISION = "decision"
    STATUS = "status"


class ThreadStatus(str, Enum):
    """Lifecycle status for a MessageThread."""

    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class RecipientType(str, Enum):
    """Routing types supported by the MessageRouter."""

    SPECIFIC_SESSION = "specific_session"
    ROLE = "role"
    DEPARTMENT = "department"
    BROADCAST = "broadcast"
    SYSTEM = "system"


class HandoffStatus(str, Enum):
    """Status lifecycle for an inter-session handoff."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReviewStatus(str, Enum):
    """Lifecycle states for a CollaborationReview."""

    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    CHANGES_REQUESTED = "changes_requested"
    RESUBMITTED = "resubmitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalStatus(str, Enum):
    """Status outcomes for an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class TimelineEventType(str, Enum):
    """Categories of timeline events captured during collaboration."""

    CONVERSATION_CREATED = "conversation_created"
    THREAD_CREATED = "thread_created"
    MESSAGE_PUBLISHED = "message_published"
    MESSAGE_DELIVERED = "message_delivered"
    THREAD_CLOSED = "thread_closed"
    CONVERSATION_CLOSED = "conversation_closed"
    ARTIFACT_SHARED = "artifact_shared"
    HANDOFF_CREATED = "handoff_created"
    HANDOFF_ACCEPTED = "handoff_accepted"
    HANDOFF_REJECTED = "handoff_rejected"
    HANDOFF_COMPLETED = "handoff_completed"
    HANDOFF_CANCELLED = "handoff_cancelled"
    REVIEW_CREATED = "review_created"
    REVIEW_STARTED = "review_started"
    CHANGES_REQUESTED = "changes_requested"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    APPROVAL_CREATED = "approval_created"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    MESSAGE = "message"
    HANDOFF = "handoff"
    REVIEW = "review"
    APPROVAL = "approval"
    STATE_CHANGED = "state_changed"


# ---------------------------------------------------------------------------
# Core Message Models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    """Immutable message record sent between agent sessions via conversation threads."""

    model_config = ConfigDict(frozen=True)

    message_id: str = Field(..., description="Unique message identifier.")
    conversation_id: str = Field(default="", description="Parent conversation identifier.")
    thread_id: str = Field(default="", description="Parent MessageThread identifier.")
    sender_session_id: str = Field(..., description="AgentSession ID of the sender.")
    sender_member_id: str = Field(..., description="Organization Member ID of the sender.")
    recipient_sessions: list[str] = Field(
        default_factory=list, description="Target recipient descriptors or session IDs."
    )
    recipient_session_id: str | None = Field(
        default=None, description="Primary recipient AgentSession ID (None for broadcast)."
    )
    message_type: MessageType = Field(..., description="Canonical message type.")
    subject: str = Field(default="", description="Subject or brief title of the message.")
    content: str = Field(..., description="Body content of the message.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Evidence supporting message.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Structured message payload.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible metadata.")
    in_reply_to_id: str | None = Field(default=None, description="Parent Message ID being replied to.")
    delivered: bool = Field(default=False, description="True if message has been delivered to recipients.")
    timestamp: str = Field(default_factory=_utcnow, description="ISO-8601 UTC timestamp.")


class MessageThread(BaseModel):
    """Append-only thread grouping related messages around a topic/type."""

    model_config = ConfigDict(frozen=True)

    thread_id: str = Field(..., description="Unique thread identifier.")
    conversation_id: str = Field(default="", description="Parent conversation identifier.")
    topic: str = Field(..., description="Thread topic or objective.")
    thread_type: ThreadType = Field(default=ThreadType.DISCUSSION, description="Canonical thread type.")
    status: ThreadStatus = Field(default=ThreadStatus.OPEN, description="Current thread status.")
    participant_session_ids: list[str] = Field(
        default_factory=list, description="AgentSession IDs participating in this thread."
    )
    messages: list[Message] = Field(default_factory=list, description="Chronological message list.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Thread evidence records.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible thread metadata.")
    created_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC thread creation timestamp.")
    closed_at: str | None = Field(default=None, description="ISO-8601 UTC timestamp when closed.")


class CollaborationConversation(BaseModel):
    """Immutable conversation container tying threads to a mission/blueprint context."""

    model_config = ConfigDict(frozen=True)

    conversation_id: str = Field(..., description="Unique conversation identifier.")
    mission_id: str = Field(default="", description="Associated Mission ID.")
    blueprint_id: str = Field(default="", description="Associated ExecutionBlueprint ID.")
    title: str = Field(..., description="Conversation title or description.")
    participants: list[str] = Field(
        default_factory=list, description="AgentSession IDs participating in conversation."
    )
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE, description="Conversation status.")
    threads: list[MessageThread] = Field(default_factory=list, description="List of message threads.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible metadata.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Contextual evidence.")
    created_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC creation timestamp.")
    closed_at: str | None = Field(default=None, description="ISO-8601 UTC timestamp when closed.")


# Alias for backward compatibility
Conversation = CollaborationConversation


# ---------------------------------------------------------------------------
# Shared Artifact Reference (Zero Duplication)
# ---------------------------------------------------------------------------

class ArtifactReference(BaseModel):
    """Immutable pointer referencing a workspace ArtifactRecord. Never duplicates artifact content."""

    model_config = ConfigDict(frozen=True)

    reference_id: str = Field(..., description="Unique reference identifier.")
    artifact_id: str = Field(..., description="ID of the underlying ArtifactRecord in workspace.")
    owner_session_id: str = Field(..., description="AgentSession ID that owns the artifact.")
    owner_member_id: str = Field(..., description="Member ID that owns the artifact.")
    artifact_type: str = Field(default="custom", description="Artifact category string.")
    workspace_path: str = Field(default="", description="Workspace relative path or URI.")
    lineage: list[str] = Field(default_factory=list, description="Parent artifact reference IDs.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible reference metadata.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Contextual verification evidence.")
    checksum: str = Field(default="", description="Content checksum string (e.g. SHA-256).")
    version: int = Field(default=1, ge=1, description="Artifact version integer.")
    shared_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC timestamp when shared.")


# ---------------------------------------------------------------------------
# Handoff Models
# ---------------------------------------------------------------------------

class Handoff(BaseModel):
    """Immutable record of an artifact/task handoff between producer and consumer agent sessions."""

    model_config = ConfigDict(frozen=True)

    handoff_id: str = Field(..., description="Unique handoff identifier.")
    producer_session_id: str = Field(..., description="AgentSession ID initiating the handoff.")
    consumer_session_id: str = Field(..., description="Target AgentSession ID receiving the handoff.")
    artifact_reference: ArtifactReference = Field(..., description="Pointer to the shared artifact.")
    reason: str = Field(..., description="Rationale for the handoff.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Contextual verification evidence.")
    status: HandoffStatus = Field(default=HandoffStatus.PENDING, description="Current handoff status.")
    timestamp: str = Field(default_factory=_utcnow, description="ISO-8601 UTC handoff creation timestamp.")
    completed_at: str | None = Field(default=None, description="ISO-8601 UTC completion timestamp.")
    rejected_at: str | None = Field(default=None, description="ISO-8601 UTC rejection timestamp.")
    cancelled_at: str | None = Field(default=None, description="ISO-8601 UTC cancellation timestamp.")


# ---------------------------------------------------------------------------
# Review Models (Phase C4)
# ---------------------------------------------------------------------------

class CollaborationReview(BaseModel):
    """Immutable record of an inter-agent peer review workflow."""

    model_config = ConfigDict(frozen=True)

    review_id: str = Field(..., description="Unique review request identifier.")
    conversation_id: str = Field(default="", description="Parent Conversation ID.")
    thread_id: str = Field(default="", description="Parent MessageThread ID.")
    author_session_id: str = Field(..., description="AgentSession ID that authored the work.")
    reviewer_session_id: str = Field(..., description="AgentSession ID assigned to review.")
    artifact_references: list[ArtifactReference] = Field(
        default_factory=list, description="Artifacts submitted for peer review."
    )
    status: ReviewStatus = Field(default=ReviewStatus.REQUESTED, description="Current review status.")
    reason: str = Field(default="", description="Reason for peer review request.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Review context evidence.")
    comments: list[dict[str, Any]] = Field(default_factory=list, description="Review comments/feedback.")
    decision: str | None = Field(default=None, description="Final review decision string (e.g. 'approved', 'rejected').")
    requested_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC request timestamp.")
    started_at: str | None = Field(default=None, description="ISO-8601 UTC timestamp when review started.")
    completed_at: str | None = Field(default=None, description="ISO-8601 UTC timestamp when review completed.")


# Alias for backward compatibility
ReviewRequest = CollaborationReview


# ---------------------------------------------------------------------------
# Approval Models (Phase C4)
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


class CollaborationApproval(BaseModel):
    """Immutable request for human or governance approval governed by RuntimeReviewPolicy."""

    model_config = ConfigDict(frozen=True)

    approval_id: str = Field(..., description="Unique approval request identifier.")
    conversation_id: str = Field(default="", description="Parent Conversation ID.")
    thread_id: str = Field(default="", description="Parent MessageThread ID.")
    requester_session_id: str = Field(..., description="AgentSession ID requesting approval.")
    approver_session_id: str | None = Field(
        default=None, description="Target AgentSession or human approver ID."
    )
    artifact_references: list[ArtifactReference] = Field(
        default_factory=list, description="Artifacts under approval review."
    )
    reason: str = Field(..., description="Rationale for requiring approval.")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Contextual evidence.")
    policy_name: str = Field(default="default", description="Active RuntimeReviewPolicy name.")
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING, description="Approval status.")
    outcome: ApprovalDecision | None = Field(default=None, description="Decided outcome, if completed.")
    requested_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC request timestamp.")
    decided_at: str | None = Field(default=None, description="ISO-8601 UTC completion timestamp.")


# Alias for backward compatibility
ApprovalRequest = CollaborationApproval


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
    """Immutable collaboration session tracking conversations, handoffs, shared artifacts, reviews, approvals, and timeline."""

    model_config = ConfigDict(frozen=True)

    collaboration_id: str = Field(..., description="Unique collaboration session identifier.")
    blueprint_id: str = Field(..., description="ExecutionBlueprint ID reference.")
    agent_session_ids: list[str] = Field(
        default_factory=list, description="Bound AgentSession IDs participating in collaboration."
    )
    active_conversations: list[CollaborationConversation] = Field(
        default_factory=list, description="Conversations within this collaboration session."
    )
    participants: list[str] = Field(
        default_factory=list, description="All participating AgentSession IDs."
    )
    open_threads: list[MessageThread] = Field(
        default_factory=list, description="Currently open message threads."
    )
    closed_threads: list[MessageThread] = Field(
        default_factory=list, description="Closed or archived message threads."
    )
    shared_artifacts: list[ArtifactReference] = Field(
        default_factory=list, description="Shared artifact references in this session."
    )
    handoffs: list[Handoff] = Field(
        default_factory=list, description="Handoffs recorded in this session."
    )
    reviews: list[CollaborationReview] = Field(
        default_factory=list, description="Peer reviews recorded in this session."
    )
    approvals: list[CollaborationApproval] = Field(
        default_factory=list, description="Approvals recorded in this session."
    )
    statistics: dict[str, int] = Field(
        default_factory=dict, description="Collaboration statistics."
    )
    timeline: Timeline = Field(
        default_factory=lambda: Timeline(timeline_id="tl-empty", session_id="collab-session"),
        description="Collaboration execution timeline log.",
    )
    created_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC creation timestamp.")


class CollaborationReport(BaseModel):
    """Immutable report summarizing collaboration session outcomes including reviews, approvals, policy decisions, and durations."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique report identifier.")
    collaboration_id: str = Field(..., description="Target CollaborationSession ID.")
    total_messages: int = Field(default=0, description="Total messages sent across all threads.")
    total_threads: int = Field(default=0, description="Total threads created.")
    total_conversations: int = Field(default=0, description="Total conversations created.")
    total_shared_artifacts: int = Field(default=0, description="Total shared artifact references created.")
    shared_artifacts: list[ArtifactReference] = Field(
        default_factory=list, description="List of shared ArtifactReference objects."
    )
    artifact_references: list[str] = Field(
        default_factory=list, description="List of shared reference IDs."
    )
    total_handoffs: int = Field(default=0, description="Total handoffs initiated.")
    pending_handoffs: list[Handoff] = Field(
        default_factory=list, description="Pending handoffs."
    )
    completed_handoffs: list[Handoff] = Field(
        default_factory=list, description="Successfully completed handoffs."
    )
    rejected_handoffs: list[Handoff] = Field(
        default_factory=list, description="Rejected handoffs."
    )
    cancelled_handoffs: list[Handoff] = Field(
        default_factory=list, description="Cancelled handoffs."
    )
    total_reviews: int = Field(default=0, description="Total peer review requests processed.")
    approved_reviews: list[CollaborationReview] = Field(
        default_factory=list, description="Approved peer reviews."
    )
    rejected_reviews: list[CollaborationReview] = Field(
        default_factory=list, description="Rejected peer reviews."
    )
    pending_reviews: list[CollaborationReview] = Field(
        default_factory=list, description="Outstanding / in-progress peer reviews."
    )
    changes_requested_reviews: list[CollaborationReview] = Field(
        default_factory=list, description="Peer reviews with changes requested."
    )
    outstanding_reviews: int = Field(default=0, description="Count of open/pending reviews.")

    total_approvals: int = Field(default=0, description="Total approval requests processed.")
    approved_approvals: list[CollaborationApproval] = Field(
        default_factory=list, description="Approved approval requests."
    )
    rejected_approvals: list[CollaborationApproval] = Field(
        default_factory=list, description="Rejected approval requests."
    )
    pending_approvals: list[CollaborationApproval] = Field(
        default_factory=list, description="Outstanding approval requests."
    )
    approved_count: int = Field(default=0, description="Total approvals granted.")
    outstanding_approvals: int = Field(default=0, description="Count of pending approvals.")

    policy_decisions: dict[str, str] = Field(
        default_factory=dict, description="Approval ID to active policy decision outcome mapping."
    )
    review_duration_summary: dict[str, float] = Field(
        default_factory=dict, description="Review ID to completion duration in seconds mapping."
    )
    approval_duration_summary: dict[str, float] = Field(
        default_factory=dict, description="Approval ID to completion duration in seconds mapping."
    )
    ownership_summary: dict[str, int] = Field(
        default_factory=dict, description="Count of shared artifacts per owner session."
    )
    lineage_summary: dict[str, list[str]] = Field(
        default_factory=dict, description="Reference ID to parent lineage mapping."
    )
    timeline: Timeline = Field(..., description="Full collaboration timeline log.")
    summary: str = Field(default="", description="Human-readable collaboration summary.")
    generated_at: str = Field(default_factory=_utcnow, description="ISO-8601 UTC report timestamp.")
