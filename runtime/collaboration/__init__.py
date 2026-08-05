"""OniRoute SwarmAgents — Engineering Collaboration Package (ACR-007 Phase C1 Architecture, Phase C2 Message Bus, Phase C3 Shared Artifacts & Handoffs, Phase C4 Review & Approval Coordination).

Coordinates communication, conversations, threads, messages, handoffs, shared artifacts,
peer reviews, governance approvals, timelines, and progress reporting between live AgentSessions.

Consumes the frozen Agent Runtime without modifying Mission, Organization, Workspace, or Runtime.
"""

from .approval_coordinator import ApprovalCoordinator
from .artifact_manager import SharedArtifactManager
from .contracts import (
    ApprovalCoordinatorContract,
    CollaborationCoordinatorContract,
    HandoffManagerContract,
    MessageBusContract,
    ReviewCoordinatorContract,
    SharedArtifactManagerContract,
)
from .handoff_manager import HandoffManager
from .message_bus import MessageBus
from .models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    ArtifactReference,
    CollaborationApproval,
    CollaborationConversation,
    CollaborationReport,
    CollaborationReview,
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
    ReviewStatus,
    ThreadStatus,
    ThreadType,
    Timeline,
    TimelineEvent,
    TimelineEventType,
)

from .review_coordinator import ReviewCoordinator
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
    "ReviewStatus",
    "ApprovalStatus",
    "TimelineEventType",
    "Message",
    "MessageThread",
    "Conversation",
    "CollaborationConversation",
    "ArtifactReference",
    "Handoff",
    "CollaborationReview",
    "ReviewRequest",
    "ApprovalDecision",
    "CollaborationApproval",
    "ApprovalRequest",
    "TimelineEvent",
    "Timeline",
    "CollaborationSession",
    "CollaborationReport",
    # Managers & Coordinators
    "MessageRouter",
    "CollaborationTimeline",
    "MessageBus",
    "SharedArtifactManager",
    "HandoffManager",
    "ReviewCoordinator",
    "ApprovalCoordinator",
    # Contracts
    "MessageBusContract",
    "HandoffManagerContract",
    "SharedArtifactManagerContract",
    "ApprovalCoordinatorContract",
    "ReviewCoordinatorContract",
    "CollaborationCoordinatorContract",
]
