"""Interface Contracts for Engineering Collaboration Architecture (ACR-007 Phase C1).

Defines ABC contracts for all canonical components in the Collaboration layer.
Architecture-only specifications. No AI execution, no runtime scheduling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

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
    ReviewRequest,
    Timeline,
)


class MessageBusContract(ABC):
    """Contract for managing inter-session message routing and thread management."""

    @abstractmethod
    def publish_message(self, message: Message) -> Message:
        """Publish a message to the bus and route to recipient or thread."""
        raise NotImplementedError

    @abstractmethod
    def create_thread(self, topic: str, participant_session_ids: list[str]) -> MessageThread:
        """Create a new MessageThread for grouped communication."""
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, session_id: str) -> list[Message]:
        """Retrieve all messages sent to or from a specific AgentSession."""
        raise NotImplementedError

    @abstractmethod
    def get_thread(self, thread_id: str) -> MessageThread | None:
        """Retrieve a MessageThread by ID."""
        raise NotImplementedError


class HandoffManagerContract(ABC):
    """Contract for coordinating artifact and task handoffs between sessions."""

    @abstractmethod
    def initiate_handoff(
        self,
        producer_session_id: str,
        consumer_session_id: str,
        artifact_reference: ArtifactReference,
        reason: str,
        evidence: dict | None = None,
    ) -> Handoff:
        """Initiate a handoff from producer session to consumer session."""
        raise NotImplementedError

    @abstractmethod
    def update_handoff_status(self, handoff_id: str, status: HandoffStatus) -> Handoff:
        """Update the status of a handoff (e.g. ACCEPTED, REJECTED, COMPLETED)."""
        raise NotImplementedError

    @abstractmethod
    def get_handoffs(self, session_id: str) -> list[Handoff]:
        """Retrieve all handoffs involving a specific AgentSession."""
        raise NotImplementedError


class SharedArtifactManagerContract(ABC):
    """Contract for tracking shared artifact references across sessions without duplication."""

    @abstractmethod
    def share_artifact(
        self,
        artifact_id: str,
        owner_session_id: str,
        owner_member_id: str,
        metadata: dict | None = None,
    ) -> ArtifactReference:
        """Create a shared ArtifactReference pointing to an existing workspace artifact."""
        raise NotImplementedError

    @abstractmethod
    def get_references(self, artifact_id: str) -> list[ArtifactReference]:
        """Retrieve all references pointing to a given artifact ID."""
        raise NotImplementedError

    @abstractmethod
    def verify_lineage(self, reference_id: str) -> list[str]:
        """Verify and return the lineage chain for a shared artifact reference."""
        raise NotImplementedError


class ApprovalCoordinatorContract(ABC):
    """Contract for handling human and governance approval workflows."""

    @abstractmethod
    def request_approval(
        self,
        requester_session_id: str,
        reason: str,
        artifact_references: list[ArtifactReference] | None = None,
        approver_session_id: str | None = None,
        evidence: dict | None = None,
    ) -> ApprovalRequest:
        """Create a new ApprovalRequest."""
        raise NotImplementedError

    @abstractmethod
    def submit_decision(
        self,
        approval_id: str,
        status: ApprovalStatus,
        actor_session_id: str,
        reason: str,
        evidence: dict | None = None,
    ) -> ApprovalDecision:
        """Submit a decision for a pending ApprovalRequest."""
        raise NotImplementedError

    @abstractmethod
    def get_approval(self, approval_id: str) -> ApprovalRequest | None:
        """Retrieve an ApprovalRequest by ID."""
        raise NotImplementedError


class ReviewCoordinatorContract(ABC):
    """Contract for coordinating peer reviews between live agent sessions."""

    @abstractmethod
    def request_peer_review(
        self,
        author_session_id: str,
        reviewer_session_id: str,
        artifact_references: list[ArtifactReference],
        reason: str,
    ) -> ReviewRequest:
        """Create a peer review request."""
        raise NotImplementedError

    @abstractmethod
    def get_pending_reviews(self, reviewer_session_id: str) -> list[ReviewRequest]:
        """Retrieve pending review requests assigned to a reviewer session."""
        raise NotImplementedError


class CollaborationCoordinatorContract(ABC):
    """Top-level contract coordinating collaboration sessions and reporting."""

    @abstractmethod
    def initialize_collaboration(
        self, blueprint_id: str, agent_session_ids: list[str]
    ) -> CollaborationSession:
        """Initialize a new CollaborationSession for a set of AgentSessions."""
        raise NotImplementedError

    @abstractmethod
    def get_timeline(self, collaboration_id: str) -> Timeline:
        """Retrieve the execution timeline log for a collaboration session."""
        raise NotImplementedError

    @abstractmethod
    def generate_report(self, collaboration_id: str) -> CollaborationReport:
        """Generate a comprehensive CollaborationReport."""
        raise NotImplementedError
