# Phase P3.A3 — Execution Task Queue Specification

## 1. Subsystem Overview
The [`ExecutionTaskQueue`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/queue.py#L33) is a deterministic task queue constructed directly from a [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125).

```
RuntimeExecutionSnapshot ──► ExecutionTaskQueue ──► AutonomousExecutionEngine
```

---

## 2. Invariant Execution Rules

- **Zero Recalculation**: The queue strictly consumes pre-planned wave mappings and session dependencies from the snapshot. **Execution order is never recalculated.**
- **Topological Wave Sequence**: Tasks are executed in strict wave order:
  `Wave 1 -> Wave 2 -> Wave 3 -> Wave 4 -> Wave 5 -> Wave 6`
- **Parallel Grouping**: Within a wave, tasks without inter-dependencies are grouped into parallel execution sets.

---

## 3. ExecutionTask Schema

Each [`ExecutionTask`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/queue.py#L15) model contains:

| Attribute | Type | Description |
|---|---|---|
| `task_id` | `str` | Unique task ID (e.g. `task-w1-devops-sess-devops-001`) |
| `wave_number` | `int` | Assigned wave number (1 to 6) |
| `profile_id` | `str` | Associated AgentProfile ID |
| `session_id` | `str` | Associated AgentSession ID |
| `agent_role` | `str` | Human-readable agent role title |
| `primary_discipline` | `str` | Primary engineering discipline |
| `bundle_reference` | `str` | Assigned skill bundle ID |
| `dependencies` | `List[str]` | Prerequisite task IDs |
| `status` | `ExecutionStatus` | Task status (`PENDING`, `IN_PROGRESS`, `DONE`, `ERROR`, `SKIPPED`) |
| `retry_counter` | `int` | Current retry attempt count |
| `max_retries` | `int` | Maximum allowed retries |
| `timeout_seconds` | `int` | Task timeout limit in seconds |
| `priority` | `int` | Execution priority (1 highest) |
| `execution_hash` | `str` | SHA-256 hash computed over task parameters |
