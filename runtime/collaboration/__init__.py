"""OniRoute SwarmAgents — Engineering Collaboration Package (ACR-007 Phase C1 Architecture).

Coordinates communication, handoffs, shared artifacts, approvals, reviews,
timelines, and progress reporting between live AgentSessions.

Consumes the frozen Agent Runtime without modifying Mission, Organization, Workspace, or Runtime.
Architecture & declarative models only.
"""

from .contracts import (
    ApprovalCoordinatorContract,
    CollaborationCoordinatorContract,
    HandoffManagerContract,
    MessageBusContract,
    ReviewCoordinatorContract,
    SharedArtifactManagerContract,
)
from .models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    ArtifactReference,
    CollaborationReport,
    CollaborationSession,
    Conversation,
    Handoff,
    HandoffStatus,
    Message,
    MessageThread,
    MessageType,
    ReviewRequest,
    Timeline,
    TimelineEvent,
    TimelineEventType,
)

__all__ = [
    # Models & Enums
    "MessageType",
    "HandoffStatus",
    "ApprovalStatus",
    "TimelineEventType",
    "Message",
    "MessageThread",
    "Conversation",
    "ArtifactReference",
    "Handoff",
    "ApprovalDecision",
    "ApprovalRequest",
    "ReviewRequest",
    "TimelineEvent",
    "Timeline",
    "CollaborationSession",
    "CollaborationReport",
    # Contracts
    "MessageBusContract",
    "HandoffManagerContract",
    "SharedArtifactManagerContract",
    "ApprovalCoordinatorContract",
    "ReviewCoordinatorContract",
    "CollaborationCoordinatorContract",
]
