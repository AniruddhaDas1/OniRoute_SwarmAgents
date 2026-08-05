# Agent Session Architecture (`docs/RUNTIME_SESSIONS.md`)

## Executive Summary

An **AgentSession** (`runtime.agent.models.AgentSession`) is the canonical declarative unit representing one live agent in the Agent Runtime. Each session is instantiated from an `OrganizationMember` definition in the frozen `ExecutionBlueprint`.

---

## 1. Session Schema

| Field | Type | Description |
| :--- | :--- | :--- |
| `session_id` | `str` | Unique session identifier (e.g. `sess-mem-backend-01-001`) |
| `member_id` | `str` | Source Organization member ID |
| `role_id` | `str` | Bound role ID |
| `role_title` | `str` | Human-readable role title |
| `blueprint_id` | `str` | Parent `ExecutionBlueprint` reference |
| `capability_ids` | `list[str]` | Capability IDs this session fulfills |
| `state` | `RuntimeState` | Current lifecycle state |
| `status` | `ExecutionStatus` | High-level execution status |
| `artifacts` | `list[ArtifactRecord]` | Collected artifact records |
| `events` | `list[ExecutionEvent]` | Chronological event log |
| `metrics` | `RuntimeMetrics` | Performance and telemetry data |
| `evidence` | `list[dict]` | Audit evidence records |

---

## 2. Session Instantiation Rule

One `AgentSession` is created per `OrganizationMember` in the `ExecutionBlueprint.organization`. Sessions inherit all member capability references, role definitions, and dependency relationships from the blueprint.

---

## 3. Session Termination

Sessions exit the lifecycle through one of three terminal states:
- **`COMPLETED`**: Successful execution and artifact delivery.
- **`FAILED`**: Unrecoverable execution error.
- **`CANCELLED`**: Explicit cancellation by coordinator governance.
