"""Deterministic Collaboration Message Bus for OniRoute SwarmAgents (ACR-007 Phase C2).

Implements MessageBusContract to provide structured, typed inter-session communication
strictly through:
  AgentSession → Conversation → Thread → MessageBus → Recipient Session → Timeline

Never permits direct session-to-session messaging bypassing conversation/thread structure.
No AI execution, no runtime scheduling, no runtime mutation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from runtime.agent.models import AgentSession

from .contracts import MessageBusContract
from .models import (
    CollaborationConversation,
    CollaborationReport,
    CollaborationSession,
    ConversationStatus,
    HandoffStatus,
    Message,
    MessageThread,
    MessageType,
    ThreadStatus,
    ThreadType,
    TimelineEventType,
)
from .router import MessageRouter
from .timeline import CollaborationTimeline


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageBus(MessageBusContract):
    """Concrete implementation of the Collaboration Message Bus.

    Manages Conversations, Threads, Message Publishing, Routing, Delivery, and Timeline logging.
    """

    def __init__(self, blueprint_id: str = "bp-default", router: MessageRouter | None = None) -> None:
        self._blueprint_id = blueprint_id
        self._router = router or MessageRouter()
        self._timeline = CollaborationTimeline()

        self._conversations: dict[str, CollaborationConversation] = {}
        """conversation_id → CollaborationConversation"""

        self._threads: dict[str, MessageThread] = {}
        """thread_id → MessageThread"""

        self._messages: dict[str, Message] = {}
        """message_id → Message"""

        self._active_sessions: dict[str, AgentSession] = {}
        """session_id → AgentSession object (registered for routing)"""

    # ------------------------------------------------------------------
    # Public Properties
    # ------------------------------------------------------------------

    @property
    def router(self) -> MessageRouter:
        return self._router

    @property
    def timeline(self) -> CollaborationTimeline:
        return self._timeline

    # ------------------------------------------------------------------
    # Session Registration
    # ------------------------------------------------------------------

    def register_session(self, session: AgentSession) -> None:
        """Register an active AgentSession for message routing."""
        self._active_sessions[session.session_id] = session

    def register_sessions(self, sessions: list[AgentSession]) -> None:
        """Register multiple active AgentSessions."""
        for s in sessions:
            self.register_session(s)

    # ------------------------------------------------------------------
    # Conversation Management
    # ------------------------------------------------------------------

    def create_conversation(
        self,
        title: str,
        mission_id: str = "",
        blueprint_id: str | None = None,
        participants: list[str] | None = None,
        evidence: dict | None = None,
        metadata: dict | None = None,
    ) -> CollaborationConversation:
        """Create a new CollaborationConversation."""
        conv_id = f"conv-{uuid.uuid4().hex[:8]}"
        conv = CollaborationConversation(
            conversation_id=conv_id,
            mission_id=mission_id,
            blueprint_id=blueprint_id or self._blueprint_id,
            title=title,
            participants=list(participants or []),
            status=ConversationStatus.ACTIVE,
            threads=[],
            evidence=evidence or {},
            metadata=metadata or {},
            created_at=_utcnow(),
        )
        self._conversations[conv_id] = conv

        self._timeline.record_event(
            event_type=TimelineEventType.CONVERSATION_CREATED,
            session_id=participants[0] if participants else "system",
            description=f"Conversation created: '{title}' ({conv_id})",
            payload={"conversation_id": conv_id, "title": title, "mission_id": mission_id},
        )
        return conv

    def get_conversation(self, conversation_id: str) -> CollaborationConversation | None:
        """Retrieve a CollaborationConversation by ID."""
        return self._conversations.get(conversation_id)

    def list_conversations(self) -> tuple[CollaborationConversation, ...]:
        """Return all conversations."""
        return tuple(self._conversations.values())

    def close_conversation(self, conversation_id: str) -> CollaborationConversation:
        """Close a conversation and all its open threads."""
        if conversation_id not in self._conversations:
            raise KeyError(f"Conversation '{conversation_id}' not found.")

        conv = self._conversations[conversation_id]
        if conv.status == ConversationStatus.CLOSED:
            return conv

        # Close all open threads in this conversation
        updated_threads: list[MessageThread] = []
        for thread in conv.threads:
            if thread.status == ThreadStatus.OPEN:
                closed_th = self.close_thread(thread.thread_id)
                updated_threads.append(closed_th)
            else:
                updated_threads.append(thread)

        closed_conv = CollaborationConversation(
            conversation_id=conv.conversation_id,
            mission_id=conv.mission_id,
            blueprint_id=conv.blueprint_id,
            title=conv.title,
            participants=list(conv.participants),
            status=ConversationStatus.CLOSED,
            threads=updated_threads,
            metadata=dict(conv.metadata),
            evidence=dict(conv.evidence),
            created_at=conv.created_at,
            closed_at=_utcnow(),
        )
        self._conversations[conversation_id] = closed_conv

        self._timeline.record_event(
            event_type=TimelineEventType.CONVERSATION_CLOSED,
            session_id="system",
            description=f"Conversation '{conv.title}' ({conversation_id}) closed.",
            payload={"conversation_id": conversation_id},
        )
        return closed_conv

    # ------------------------------------------------------------------
    # Thread Management
    # ------------------------------------------------------------------

    def create_thread(
        self,
        topic: str,
        participant_session_ids: list[str],
        conversation_id: str | None = None,
        thread_type: ThreadType = ThreadType.DISCUSSION,
        evidence: dict | None = None,
        metadata: dict | None = None,
    ) -> MessageThread:
        """Create a new MessageThread within a conversation (implements MessageBusContract)."""
        thread_id = f"th-{uuid.uuid4().hex[:8]}"

        # Auto-create conversation if none provided
        if not conversation_id or conversation_id not in self._conversations:
            conv = self.create_conversation(
                title=f"Conversation for thread: {topic}",
                participants=participant_session_ids,
            )
            conversation_id = conv.conversation_id

        thread = MessageThread(
            thread_id=thread_id,
            conversation_id=conversation_id,
            topic=topic,
            thread_type=thread_type,
            status=ThreadStatus.OPEN,
            participant_session_ids=list(participant_session_ids),
            messages=[],
            evidence=evidence or {},
            metadata=metadata or {},
            created_at=_utcnow(),
        )
        self._threads[thread_id] = thread

        # Attach thread to conversation
        conv = self._conversations[conversation_id]
        new_threads = list(conv.threads) + [thread]
        new_participants = sorted(set(conv.participants) | set(participant_session_ids))
        updated_conv = CollaborationConversation(
            conversation_id=conv.conversation_id,
            mission_id=conv.mission_id,
            blueprint_id=conv.blueprint_id,
            title=conv.title,
            participants=new_participants,
            status=conv.status,
            threads=new_threads,
            metadata=dict(conv.metadata),
            evidence=dict(conv.evidence),
            created_at=conv.created_at,
            closed_at=conv.closed_at,
        )
        self._conversations[conversation_id] = updated_conv

        self._timeline.record_event(
            event_type=TimelineEventType.THREAD_CREATED,
            session_id=participant_session_ids[0] if participant_session_ids else "system",
            description=f"Thread created: '{topic}' ({thread_id})",
            payload={"thread_id": thread_id, "conversation_id": conversation_id, "topic": topic},
        )
        return thread

    def get_thread(self, thread_id: str) -> MessageThread | None:
        """Retrieve a MessageThread by ID (implements MessageBusContract)."""
        return self._threads.get(thread_id)

    def close_thread(self, thread_id: str) -> MessageThread:
        """Close an open MessageThread."""
        if thread_id not in self._threads:
            raise KeyError(f"Thread '{thread_id}' not found.")

        thread = self._threads[thread_id]
        if thread.status == ThreadStatus.CLOSED:
            return thread

        closed_thread = MessageThread(
            thread_id=thread.thread_id,
            conversation_id=thread.conversation_id,
            topic=thread.topic,
            thread_type=thread.thread_type,
            status=ThreadStatus.CLOSED,
            participant_session_ids=list(thread.participant_session_ids),
            messages=list(thread.messages),
            evidence=dict(thread.evidence),
            metadata=dict(thread.metadata),
            created_at=thread.created_at,
            closed_at=_utcnow(),
        )
        self._threads[thread_id] = closed_thread

        # Update in parent conversation
        if thread.conversation_id in self._conversations:
            conv = self._conversations[thread.conversation_id]
            updated_threads = [
                closed_thread if t.thread_id == thread_id else t
                for t in conv.threads
            ]
            self._conversations[thread.conversation_id] = CollaborationConversation(
                conversation_id=conv.conversation_id,
                mission_id=conv.mission_id,
                blueprint_id=conv.blueprint_id,
                title=conv.title,
                participants=list(conv.participants),
                status=conv.status,
                threads=updated_threads,
                metadata=dict(conv.metadata),
                evidence=dict(conv.evidence),
                created_at=conv.created_at,
                closed_at=conv.closed_at,
            )

        self._timeline.record_event(
            event_type=TimelineEventType.THREAD_CLOSED,
            session_id="system",
            description=f"Thread '{thread.topic}' ({thread_id}) closed.",
            payload={"thread_id": thread_id, "conversation_id": thread.conversation_id},
        )
        return closed_thread

    def archive_thread(self, thread_id: str) -> MessageThread:
        """Archive a MessageThread."""
        if thread_id not in self._threads:
            raise KeyError(f"Thread '{thread_id}' not found.")

        thread = self._threads[thread_id]
        archived_thread = MessageThread(
            thread_id=thread.thread_id,
            conversation_id=thread.conversation_id,
            topic=thread.topic,
            thread_type=thread.thread_type,
            status=ThreadStatus.ARCHIVED,
            participant_session_ids=list(thread.participant_session_ids),
            messages=list(thread.messages),
            evidence=dict(thread.evidence),
            metadata=dict(thread.metadata),
            created_at=thread.created_at,
            closed_at=_utcnow(),
        )
        self._threads[thread_id] = archived_thread
        return archived_thread

    # ------------------------------------------------------------------
    # Message Publishing & Delivery
    # ------------------------------------------------------------------

    def publish_message(self, message: Message) -> Message:
        """Publish a message to the bus (implements MessageBusContract).

        Performs:
        1. Thread and conversation validation.
        2. Recipient routing via MessageRouter.
        3. Appending message to target thread.
        4. Recording PUBLISHED and DELIVERED timeline events.
        """
        # Ensure message has an ID
        msg_id = message.message_id or f"msg-{uuid.uuid4().hex[:8]}"

        # Resolve thread or create default
        thread_id = message.thread_id
        if not thread_id or thread_id not in self._threads:
            # Create thread for message
            thread = self.create_thread(
                topic=message.subject or f"{message.message_type.value.upper()} thread",
                participant_session_ids=[message.sender_session_id],
                conversation_id=message.conversation_id,
            )
            thread_id = thread.thread_id
            message = Message(
                message_id=msg_id,
                conversation_id=thread.conversation_id,
                thread_id=thread_id,
                sender_session_id=message.sender_session_id,
                sender_member_id=message.sender_member_id,
                recipient_sessions=list(message.recipient_sessions),
                recipient_session_id=message.recipient_session_id,
                message_type=message.message_type,
                subject=message.subject,
                content=message.content,
                evidence=dict(message.evidence),
                payload=dict(message.payload),
                metadata=dict(message.metadata),
                in_reply_to_id=message.in_reply_to_id,
                delivered=True,
                timestamp=message.timestamp or _utcnow(),
            )
        else:
            message = Message(
                message_id=msg_id,
                conversation_id=self._threads[thread_id].conversation_id,
                thread_id=thread_id,
                sender_session_id=message.sender_session_id,
                sender_member_id=message.sender_member_id,
                recipient_sessions=list(message.recipient_sessions),
                recipient_session_id=message.recipient_session_id,
                message_type=message.message_type,
                subject=message.subject,
                content=message.content,
                evidence=dict(message.evidence),
                payload=dict(message.payload),
                metadata=dict(message.metadata),
                in_reply_to_id=message.in_reply_to_id,
                delivered=True,
                timestamp=message.timestamp or _utcnow(),
            )

        # Perform routing
        descriptors = list(message.recipient_sessions)
        if message.recipient_session_id:
            descriptors.append(message.recipient_session_id)
        if not descriptors:
            descriptors = ["broadcast"]

        active_list = list(self._active_sessions.values()) if self._active_sessions else [message.sender_session_id]
        resolved_recipients = self._router.resolve_recipients(
            descriptors, active_list, sender_session_id=message.sender_session_id
        )

        # Append message to thread
        thread = self._threads[thread_id]
        new_messages = list(thread.messages) + [message]
        new_participants = sorted(set(thread.participant_session_ids) | set(resolved_recipients) | {message.sender_session_id})
        
        updated_thread = MessageThread(
            thread_id=thread.thread_id,
            conversation_id=thread.conversation_id,
            topic=thread.topic,
            thread_type=thread.thread_type,
            status=thread.status,
            participant_session_ids=new_participants,
            messages=new_messages,
            evidence=dict(thread.evidence),
            metadata=dict(thread.metadata),
            created_at=thread.created_at,
            closed_at=thread.closed_at,
        )
        self._threads[thread_id] = updated_thread
        self._messages[message.message_id] = message

        # Update thread in parent conversation
        if thread.conversation_id in self._conversations:
            conv = self._conversations[thread.conversation_id]
            updated_threads = [
                updated_thread if t.thread_id == thread_id else t
                for t in conv.threads
            ]
            conv_participants = sorted(set(conv.participants) | set(new_participants))
            self._conversations[thread.conversation_id] = CollaborationConversation(
                conversation_id=conv.conversation_id,
                mission_id=conv.mission_id,
                blueprint_id=conv.blueprint_id,
                title=conv.title,
                participants=conv_participants,
                status=conv.status,
                threads=updated_threads,
                metadata=dict(conv.metadata),
                evidence=dict(conv.evidence),
                created_at=conv.created_at,
                closed_at=conv.closed_at,
            )

        # Log PUBLISHED and DELIVERED events on timeline
        self._timeline.record_event(
            event_type=TimelineEventType.MESSAGE_PUBLISHED,
            session_id=message.sender_session_id,
            description=f"Message published to thread '{thread.topic}' by '{message.sender_session_id}'",
            payload={
                "message_id": message.message_id,
                "thread_id": thread_id,
                "type": message.message_type.value,
                "recipients": resolved_recipients,
            },
        )

        for r_sid in resolved_recipients:
            self._timeline.record_event(
                event_type=TimelineEventType.MESSAGE_DELIVERED,
                session_id=r_sid,
                description=f"Message {message.message_id} delivered to '{r_sid}'",
                payload={"message_id": message.message_id, "recipient_session_id": r_sid},
            )

        return message

    def get_messages(self, session_id: str) -> list[Message]:
        """Retrieve all messages sent by or delivered to a specific AgentSession (implements MessageBusContract)."""
        res: list[Message] = []
        for msg in self._messages.values():
            if msg.sender_session_id == session_id or msg.recipient_session_id == session_id:
                res.append(msg)
            elif "broadcast" in msg.recipient_sessions or "*" in msg.recipient_sessions:
                res.append(msg)
            elif any(session_id in r for r in msg.recipient_sessions):
                res.append(msg)
        return res

    # ------------------------------------------------------------------
    # Managers Integration (Phase C3)
    # ------------------------------------------------------------------

    def set_artifact_manager(self, artifact_manager: SharedArtifactManager) -> None:
        """Attach a SharedArtifactManager instance sharing the bus timeline."""
        self._artifact_manager = artifact_manager

    def set_handoff_manager(self, handoff_manager: HandoffManager) -> None:
        """Attach a HandoffManager instance sharing the bus timeline."""
        self._handoff_manager = handoff_manager

    # ------------------------------------------------------------------
    # Session Snapshot & Reporting
    # ------------------------------------------------------------------

    def get_collaboration_session(
        self,
        artifact_manager: SharedArtifactManager | None = None,
        handoff_manager: HandoffManager | None = None,
    ) -> CollaborationSession:
        """Return an immutable snapshot of the active CollaborationSession."""
        art_mgr = artifact_manager or getattr(self, "_artifact_manager", None)
        hdf_mgr = handoff_manager or getattr(self, "_handoff_manager", None)

        open_ths = [t for t in self._threads.values() if t.status == ThreadStatus.OPEN]
        closed_ths = [t for t in self._threads.values() if t.status != ThreadStatus.OPEN]
        all_participants = sorted({
            p for conv in self._conversations.values() for p in conv.participants
        })

        shared_refs = list(art_mgr.get_all_references()) if art_mgr else []
        all_handoffs = list(hdf_mgr.get_all_handoffs()) if hdf_mgr else []

        return CollaborationSession(
            collaboration_id=f"collab-{self._blueprint_id}",
            blueprint_id=self._blueprint_id,
            agent_session_ids=all_participants,
            active_conversations=list(self._conversations.values()),
            participants=all_participants,
            open_threads=open_ths,
            closed_threads=closed_ths,
            shared_artifacts=shared_refs,
            handoffs=all_handoffs,
            approvals=[],
            statistics={
                "total_conversations": len(self._conversations),
                "total_threads": len(self._threads),
                "open_threads": len(open_ths),
                "closed_threads": len(closed_ths),
                "total_messages": len(self._messages),
                "total_participants": len(all_participants),
                "total_shared_artifacts": len(shared_refs),
                "total_handoffs": len(all_handoffs),
            },
            timeline=self._timeline.to_timeline(),
            created_at=_utcnow(),
        )

    def generate_report(
        self,
        artifact_manager: SharedArtifactManager | None = None,
        handoff_manager: HandoffManager | None = None,
    ) -> CollaborationReport:
        """Generate a comprehensive CollaborationReport including shared artifacts and handoffs."""
        art_mgr = artifact_manager or getattr(self, "_artifact_manager", None)
        hdf_mgr = handoff_manager or getattr(self, "_handoff_manager", None)

        session_snap = self.get_collaboration_session(artifact_manager=art_mgr, handoff_manager=hdf_mgr)

        shared_refs = list(art_mgr.get_all_references()) if art_mgr else []
        ref_ids = [r.reference_id for r in shared_refs]

        all_handoffs = list(hdf_mgr.get_all_handoffs()) if hdf_mgr else []
        pending_h = [h for h in all_handoffs if h.status == HandoffStatus.PENDING]
        completed_h = [h for h in all_handoffs if h.status == HandoffStatus.COMPLETED]
        rejected_h = [h for h in all_handoffs if h.status == HandoffStatus.REJECTED]
        cancelled_h = [h for h in all_handoffs if h.status == HandoffStatus.CANCELLED]

        ownership_sum: dict[str, int] = {}
        lineage_sum: dict[str, list[str]] = {}
        for r in shared_refs:
            ownership_sum[r.owner_session_id] = ownership_sum.get(r.owner_session_id, 0) + 1
            if r.lineage:
                lineage_sum[r.reference_id] = r.lineage

        summary = (
            f"Collaboration Session for blueprint '{self._blueprint_id}'. "
            f"Conversations: {session_snap.statistics['total_conversations']}, "
            f"Threads: {session_snap.statistics['total_threads']}, "
            f"Messages: {session_snap.statistics['total_messages']}. "
            f"Shared Artifacts: {len(shared_refs)}, Handoffs: {len(all_handoffs)} "
            f"(completed={len(completed_h)}, pending={len(pending_h)}, rejected={len(rejected_h)}, cancelled={len(cancelled_h)})."
        )

        return CollaborationReport(
            report_id=f"rep-collab-{self._blueprint_id}-{uuid.uuid4().hex[:6]}",
            collaboration_id=session_snap.collaboration_id,
            total_messages=session_snap.statistics["total_messages"],
            total_threads=session_snap.statistics["total_threads"],
            total_conversations=session_snap.statistics["total_conversations"],
            total_shared_artifacts=len(shared_refs),
            shared_artifacts=shared_refs,
            artifact_references=ref_ids,
            total_handoffs=len(all_handoffs),
            pending_handoffs=pending_h,
            completed_handoffs=completed_h,
            rejected_handoffs=rejected_h,
            cancelled_handoffs=cancelled_h,
            total_approvals=0,
            approved_count=0,
            ownership_summary=ownership_sum,
            lineage_summary=lineage_sum,
            timeline=self._timeline.to_timeline(),
            summary=summary,
            generated_at=_utcnow(),
        )
