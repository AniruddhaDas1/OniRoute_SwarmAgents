# Engineering Collaboration Developer Guide (ACR-007)

Technical manual for developers extending or integrating with `runtime/collaboration/`.

---

## 1. Subsystem Architecture

The Collaboration layer acts as an orchestration bus between live `AgentSession` instances:

```
                  +--------------------------+
                  |      AgentSession        |
                  +------------+-------------+
                               |
                               v
               +---------------+---------------+
               |   CollaborationConversation   |
               +---------------+---------------+
                               |
                               v
                   +-----------+-----------+
                   |     MessageThread     |
                   +-----------+-----------+
                               |
                               v
                       +-------+-------+
                       |  MessageBus   |
                       +-------+-------+
                               |
           +-------------------+-------------------+
           |                   |                   |
           v                   v                   v
+----------+----------+ +------+------+ +----------+----------+
|SharedArtifactManager| |HandoffManager| |Review/Approval Coord.|
+----------+----------+ +------+------+ +----------+----------+
           |                   |                   |
           +-------------------+-------------------+
                               |
                               v
                    +----------+----------+
                    | CollaborationTimeline|
                    +----------+----------+
                               |
                               v
                    +----------+----------+
                    | CollaborationReport |
                    +---------------------+
```

---

## 2. Programmatic Usage

### 1. Message Bus & Router
```python
from runtime.collaboration import MessageBus, Message, MessageType

bus = MessageBus(blueprint_id="bp-payment-gateway")
conv = bus.create_conversation(title="Payment Service Design", participants=["sess-arch", "sess-dev"])
th = bus.create_thread(topic="Schema Design", participant_session_ids=["sess-arch", "sess-dev"], conversation_id=conv.conversation_id)

bus.publish_message(Message(
    message_id="msg-001",
    conversation_id=conv.conversation_id,
    thread_id=th.thread_id,
    sender_session_id="sess-arch",
    sender_member_id="mem-arch",
    recipient_sessions=["sess-dev"],
    message_type=MessageType.TASK,
    content="Implement DB schema",
))
```

### 2. Zero-Duplication Shared Artifact Reference
```python
from runtime.collaboration import SharedArtifactManager
from runtime.agent.models import ArtifactRecord, ArtifactType

art_mgr = SharedArtifactManager()
art = ArtifactRecord(
    artifact_id="art-db-schema-001",
    artifact_type=ArtifactType.SCHEMA,
    owner_session_id="sess-arch",
    owner_member_id="mem-arch",
    capability_id="cap-schema",
    name="Database Schema v1",
    references=["artifacts/schema.sql"],
)

ref = art_mgr.create_reference(art, version=1, checksum="sha256-a1b2c3d4")
```

### 3. Inter-Session Handoff Lifecycle
```python
from runtime.collaboration import HandoffManager

hdf_mgr = HandoffManager(timeline=art_mgr.timeline)

# 1. Producer initiates handoff (PENDING)
h = hdf_mgr.create_handoff("sess-arch", "sess-dev", ref, reason="Schema ready")

# 2. Consumer accepts handoff (ACCEPTED)
hdf_mgr.accept_handoff(h.handoff_id, "sess-dev")

# 3. Consumer completes handoff (COMPLETED)
hdf_mgr.complete_handoff(h.handoff_id, "sess-dev")
```

### 4. Peer Reviews & Governance Approvals
```python
from runtime.collaboration import ReviewCoordinator, ApprovalCoordinator
from runtime.agent.recovery.policy import SECURITY_POLICY

rev_coord = ReviewCoordinator(timeline=art_mgr.timeline)
appr_coord = ApprovalCoordinator(timeline=art_mgr.timeline, default_policy=SECURITY_POLICY)

# Peer Review
r = rev_coord.create_review("sess-dev", "sess-qa", [ref], reason="API spec review")
rev_coord.start_review(r.review_id, "sess-qa")
rev_coord.approve_review(r.review_id, "sess-qa", comments="LGTM")

# Governance Approval
a = appr_coord.request_approval("sess-dev", "Security policy update", [ref], policy=SECURITY_POLICY)
appr_coord.approve(a.approval_id, "sess-sec-lead")
```

---

## 3. Extension Rules & Guidelines

- **Stateless & Deterministic:** All managers must be deterministic and execute in-memory without external I/O.
- **Contract Enforcement:** All implementations must inherit from the contracts defined in `runtime/collaboration/contracts.py`.
- **Read-Only Runtime Constraint:** Never mutate `AgentSession` runtime states or workspace file contents.
