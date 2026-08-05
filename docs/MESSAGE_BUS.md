# Collaboration Message Bus Architecture (ACR-007 Phase C1)

**Status:** Architecture Specified  
**Contract:** `MessageBusContract`  

---

## 1. Overview

The **Collaboration Message Bus** provides structured inter-session communication between live `AgentSession` instances. It ensures agent communication is strictly typed, thread-grouped, and fully auditable without mutating runtime session state.

---

## 2. Canonical Message Types (`MessageType`)

| Type | Description | Usage Pattern |
|---|---|---|
| `QUESTION` | Request for clarification or details | Agent A asks Agent B for database schema fields |
| `ANSWER` | Response to a `QUESTION` | Agent B provides schema specification |
| `TASK` | Inter-agent task assignment | Lead agent assigns sub-component implementation |
| `HANDOFF` | Formal artifact transfer notification | Producer notifies consumer that deliverable is ready |
| `STATUS` | Progress update or checkpoint report | Periodic execution status broadcast |
| `REVIEW` | Request for peer code or spec review | Author requests peer review from reviewer agent |
| `APPROVAL` | Approval request or notification | Request for sign-off on sensitive changes |
| `WARNING` | Non-fatal issue alert | Advisory regarding deprecated API or resource constraint |
| `ERROR` | Inter-session error notification | Notification of dependent task failure |
| `INFO` | General informational broadcast | Status update broadcast across collaboration session |

---

## 3. Data Schemas

### Message (`Message`)
- `message_id`: Unique message identifier string.
- `sender_session_id`: Source `AgentSession` ID.
- `sender_member_id`: Source Organization Member ID.
- `recipient_session_id`: Optional target `AgentSession` ID (`None` for broadcast).
- `message_type`: `MessageType` enum.
- `subject`: Subject line or title.
- `content`: Body text.
- `payload`: Extensible metadata payload dict.
- `thread_id`: Optional parent `MessageThread` ID.
- `in_reply_to_id`: Optional parent `Message` ID.
- `timestamp`: ISO-8601 UTC timestamp.

### MessageThread (`MessageThread`)
- `thread_id`: Unique thread ID.
- `topic`: Topic or task description.
- `participant_session_ids`: List of involved `AgentSession` IDs.
- `messages`: Chronological list of `Message` instances.
- `created_at`: ISO-8601 UTC timestamp.

---

## 4. Message Bus Interface Contract (`MessageBusContract`)

```python
class MessageBusContract(ABC):
    @abstractmethod
    def publish_message(self, message: Message) -> Message: ...

    @abstractmethod
    def create_thread(self, topic: str, participant_session_ids: list[str]) -> MessageThread: ...

    @abstractmethod
    def get_messages(self, session_id: str) -> list[Message]: ...

    @abstractmethod
    def get_thread(self, thread_id: str) -> MessageThread | None: ...
```
