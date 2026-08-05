# Approvals & Peer Review Architecture (ACR-007 Phase C1)

**Status:** Architecture Specified  
**Contracts:** `ApprovalCoordinatorContract`, `ReviewCoordinatorContract`  

---

## 1. Overview

The **Approvals & Review** architecture provides formal mechanisms for:
1. **Governance & Human Approvals:** Requesting and rendering sign-off decisions for high-risk artifacts (`ApprovalRequest`, `ApprovalDecision`).
2. **Peer Review Requests:** Inter-agent peer code/spec reviews (`ReviewRequest`).

All approvals and review outcomes are recorded as immutable evidence records in the execution timeline.

---

## 2. Approval Request & Decision Flow

```python
class ApprovalRequest(BaseModel):
    approval_id: str
    requester_session_id: str
    approver_session_id: str | None
    artifact_references: list[ArtifactReference]
    reason: str
    evidence: dict[str, Any]
    status: ApprovalStatus    # PENDING, APPROVED, REJECTED, CHANGES_REQUESTED
    outcome: ApprovalDecision | None
    requested_at: str

class ApprovalDecision(BaseModel):
    decision_id: str
    approval_id: str
    status: ApprovalStatus
    actor_session_id: str
    reason: str
    evidence: dict[str, Any]
    decided_at: str
```

### Approval Lifecycle

```
[PENDING] ───► [APPROVED]
   │
   ├───► [REJECTED]
   │
   └───► [CHANGES_REQUESTED]
```

---

## 3. Peer Review Requests (`ReviewRequest`)

```python
class ReviewRequest(BaseModel):
    review_id: str
    reviewer_session_id: str
    author_session_id: str
    artifact_references: list[ArtifactReference]
    reason: str
    requested_at: str
```

Peer reviews allow Lead/Reviewer agents to perform verification on artifacts produced by implementation agents before handoffs are finalized.

---

## 4. Contracts

```python
class ApprovalCoordinatorContract(ABC):
    @abstractmethod
    def request_approval(...) -> ApprovalRequest: ...

    @abstractmethod
    def submit_decision(...) -> ApprovalDecision: ...

    @abstractmethod
    def get_approval(...) -> ApprovalRequest | None: ...


class ReviewCoordinatorContract(ABC):
    @abstractmethod
    def request_peer_review(...) -> ReviewRequest: ...

    @abstractmethod
    def get_pending_reviews(...) -> list[ReviewRequest]: ...
```
