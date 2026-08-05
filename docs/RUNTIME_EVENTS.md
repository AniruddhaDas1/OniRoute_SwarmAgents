# Runtime Events Specification (`docs/RUNTIME_EVENTS.md`)

## Executive Summary

The Agent Runtime emits immutable **`ExecutionEvent`** records at every significant point in an `AgentSession` lifecycle. Events form an append-only audit trail.

---

## 1. Canonical Event Types

| Event Type | Trigger |
| :--- | :--- |
| `SESSION_CREATED` | A new `AgentSession` was instantiated |
| `EXECUTION_STARTED` | Session transitioned from `READY` → `RUNNING` |
| `EXECUTION_PAUSED` | Session transitioned into `WAITING` state |
| `EXECUTION_COMPLETED` | Session reached terminal `COMPLETED` state |
| `EXECUTION_FAILED` | Session reached terminal `FAILED` state |
| `ARTIFACT_PRODUCED` | An `ArtifactRecord` was registered to the session |
| `REVIEW_REQUESTED` | Session entered `REVIEW` gate |
| `REVIEW_COMPLETED` | Review gate cleared; session resumes `RUNNING` |
| `STATE_TRANSITION` | Any state change in the lifecycle DAG |

---

## 2. Event Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `event_id` | `str` | Unique event identifier |
| `event_type` | `RuntimeEventType` | Canonical event type enum |
| `session_id` | `str` | Source session |
| `member_id` | `str` | Source organization member |
| `description` | `str` | Human-readable description |
| `event_payload` | `dict` | Structured event data payload |
| `previous_state` | `RuntimeState \| None` | Pre-transition state |
| `next_state` | `RuntimeState \| None` | Post-transition state |
| `timestamp` | `str` | ISO-8601 UTC timestamp |

---

## 3. Event Immutability Constraint

Events MUST be immutable after recording. The `EventRecorderContract` implementation must treat `record_event` as an append-only operation. Events must never be mutated or deleted.
