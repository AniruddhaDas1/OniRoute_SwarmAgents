# Engineering Collaboration Freeze Declaration (ACR-007 Phase C5)

**Status:** SEALED & FROZEN  
**Release Tag:** `v0.7.0-collaboration`  
**Effective Date:** 2026-08-05  

---

## 1. Freeze Statement

The **Engineering Collaboration** subsystem (`runtime/collaboration/`) of OniRoute SwarmAgents is hereby **formally frozen**.

No future Architecture Change Request (ACR) or feature branch may alter the core models, contracts, routing rules, handoff lifecycle state machines, review/approval state machines, or public API surfaces of this layer.

Only critical security fixes or backward-compatible bug fixes are permitted.

---

## 2. Frozen Scope

The freeze applies to all modules, models, contracts, and APIs within `runtime/collaboration/`:

### 1. Modules Frozen
- `runtime/collaboration/models.py`
- `runtime/collaboration/contracts.py`
- `runtime/collaboration/router.py`
- `runtime/collaboration/timeline.py`
- `runtime/collaboration/message_bus.py`
- `runtime/collaboration/artifact_manager.py`
- `runtime/collaboration/handoff_manager.py`
- `runtime/collaboration/review_coordinator.py`
- `runtime/collaboration/approval_coordinator.py`
- `runtime/collaboration/__init__.py`

### 2. Models Frozen (`models.py`)
`Message`, `MessageThread`, `CollaborationConversation` (`Conversation`), `ArtifactReference`, `Handoff`, `CollaborationReview` (`ReviewRequest`), `CollaborationApproval` (`ApprovalRequest`), `ApprovalDecision`, `TimelineEvent`, `Timeline`, `CollaborationSession`, `CollaborationReport`.

### 3. Enums Frozen (`models.py`)
`MessageType`, `ConversationStatus`, `ThreadType`, `ThreadStatus`, `RecipientType`, `HandoffStatus`, `ReviewStatus`, `ApprovalStatus`, `TimelineEventType`.

### 4. Contracts Frozen (`contracts.py`)
`MessageBusContract`, `HandoffManagerContract`, `SharedArtifactManagerContract`, `ApprovalCoordinatorContract`, `ReviewCoordinatorContract`, `CollaborationCoordinatorContract`.

---

## 3. Modification Policy

Any proposed modification to `runtime/collaboration/` must satisfy:

1. **Non-Breaking Invariant:** Must preserve 100% backward compatibility for all Pydantic schemas, contract methods, CLI options, and JSON outputs.
2. **Zero Mutation Rule:** Must never introduce side-effect mutations to `runtime/agent/` (`AgentSession`), `workspace/`, `mission/`, or `organization/`.
3. **Provider Independence:** Must never introduce external I/O, cloud service bindings, or LLM AI calls into the core collaboration modules.
4. **Test Verification:** Must pass all 71 collaboration tests and 356 total repository tests without regressions.
