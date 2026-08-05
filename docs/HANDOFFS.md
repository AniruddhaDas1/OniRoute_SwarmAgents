# Inter-Session Handoff Architecture (ACR-007 Phase C1)

**Status:** Architecture Specified  
**Contract:** `HandoffManagerContract`  

---

## 1. Overview

An **Inter-Session Handoff** represents the formal transfer of a completed deliverable or artifact from a **Producer** agent session to a **Consumer** agent session.

Handoffs enable asynchronous multi-agent workflows (e.g. Architect → Backend Developer → QA Engineer) while maintaining strict artifact lineage and evidence trails.

---

## 2. Shared Artifact References (Zero-Duplication Principle)

Artifacts produced during session execution reside in the workspace artifact storage (`ArtifactRecord`).

The Collaboration layer **never duplicates** artifact content. Instead, it uses lightweight, immutable `ArtifactReference` pointers:

```python
class ArtifactReference(BaseModel):
    reference_id: str         # Pointer ID
    artifact_id: str          # Target ArtifactRecord ID in workspace
    owner_session_id: str     # Producing AgentSession ID
    owner_member_id: str      # Producing Member ID
    lineage: list[str]        # Ancestor reference IDs
    metadata: dict[str, Any]  # Metadata overrides/annotations
    shared_at: str            # ISO-8601 UTC timestamp
```

---

## 3. Handoff Model (`Handoff`)

```python
class Handoff(BaseModel):
    handoff_id: str
    producer_session_id: str
    consumer_session_id: str
    artifact_reference: ArtifactReference
    reason: str
    evidence: dict[str, Any]
    status: HandoffStatus      # PENDING, ACCEPTED, REJECTED, COMPLETED
    timestamp: str
    completed_at: str | None
```

---

## 4. Handoff Lifecycle FSM

```
   [PENDING]
      │
      ├───► [ACCEPTED] ───► [COMPLETED]
      │
      └───► [REJECTED]
```

- **PENDING:** Producer initiates handoff; consumer has not yet acknowledged.
- **ACCEPTED:** Consumer accepts deliverable and begins downstream work.
- **REJECTED:** Consumer rejects deliverable (e.g. missing fields, failed validation).
- **COMPLETED:** Consumer finishes downstream work derived from handoff.

---

## 5. Handoff Manager Interface Contract (`HandoffManagerContract`)

```python
class HandoffManagerContract(ABC):
    @abstractmethod
    def initiate_handoff(
        self,
        producer_session_id: str,
        consumer_session_id: str,
        artifact_reference: ArtifactReference,
        reason: str,
        evidence: dict | None = None,
    ) -> Handoff: ...

    @abstractmethod
    def update_handoff_status(self, handoff_id: str, status: HandoffStatus) -> Handoff: ...

    @abstractmethod
    def get_handoffs(self, session_id: str) -> list[Handoff]: ...
```
