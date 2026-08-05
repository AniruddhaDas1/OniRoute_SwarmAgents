"""OniRoute SwarmAgents — Engineering Collaboration Package (ACR-007 Phase C1 Architecture & Phase C2 Message Bus).

Coordinates communication, conversations, threads, messages, handoffs, shared artifacts,
approvals, reviews, timelines, and progress reporting between live AgentSessions.

Consumes the frozen Agent Runtime without modifying Mission, Organization, Workspace, or Runtime.
"""

from .contracts import (
    ApprovalCoordinatorContract,
    CollaborationCoordinatorContract,
    HandoffManagerContract,
    MessageBusContract,
    ReviewCoordinatorContract,
    SharedArtifactManagerContract,
)
from .message_bus import MessageBus
from .models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    ArtifactReference,
    CollaborationConversation,
    CollaborationReport,
    CollaborationSession,
    Conversation,
    ConversationStatus,
    Handoff,
    HandoffStatus,
    Message,
    MessageThread,
    MessageType,
    RecipientType,
    ReviewRequest,
    ThreadStatus,
    ThreadType,
    Timeline,
    TimelineEvent,
    TimelineEventType,
)
from .router import MessageRouter
from .timeline import CollaborationTimeline

__all__ = [
    # Models & Enums
    "MessageType",
    "ConversationStatus",
    "ThreadType",
    "ThreadStatus",
    "RecipientType",
    "HandoffStatus",
    "ApprovalStatus",
    "TimelineEventType",
    "Message",
    "MessageThread",
    "Conversation",
    "CollaborationConversation",
    "ArtifactReference",
    "Handoff",
    "ApprovalDecision",
    "ApprovalRequest",
    "ReviewRequest",
    "TimelineEvent",
    "Timeline",
    "CollaborationSession",
    "CollaborationReport",
    # Engines & Routing
    "MessageRouter",
    "CollaborationTimeline",
    "MessageBus",
    # Contracts
    "MessageBusContract",
    "HandoffManagerContract",
    "SharedArtifactManagerContract",
    "ApprovalCoordinatorContract",
    "ReviewCoordinatorContract",
    "CollaborationCoordinatorContract",
]
