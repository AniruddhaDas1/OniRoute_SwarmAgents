# Phase P3.A2 — Runtime Execution Snapshot Specification

## 1. Schema Definition
The [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125) is an immutable Pydantic data contract produced by the [`SwarmInitializationEngine`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/engine.py#L42).

```json
{
  "snapshot_id": "snap-a1b2c3",
  "mission_id": "msn-123456",
  "deployment_plan_id": "dep-123456",
  "execution_uuid": "exec-uuid-789xyz",
  "wave_status": { ... },
  "session_map": { ... },
  "sessions": [ ... ],
  "execution_cursor": { ... },
  "execution_context": { ... },
  "budget_status": { ... },
  "retry_status": { ... },
  "checkpoint_status": { ... },
  "event_bus_references": { ... },
  "storage_references": { ... },
  "workspace_references": { ... },
  "evidence": { ... },
  "timestamp": "2026-08-05T21:10:27+00:00",
  "snapshot_hash": "67af3d875edc2dce0751592e585f684729ec38c931efcd041c37e83ebdce7685"
}
```

---

## 2. Component Specifications

### 2.1 Identifiers & UUIDs
- **`snapshot_id`**: String identifier prefixed with `snap-` (e.g. `snap-a1b2c3`).
- **`mission_id`**: Associated mission identifier.
- **`deployment_plan_id`**: Associated deployment plan identifier (`dep-xxxxxx`).
- **`execution_uuid`**: Canonical execution instance UUID (`exec-uuid-xxxxxx`).

### 2.2 Workload & Session State
- **`sessions`**: List of initialized [`AgentSession`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/agent/models.py#L184) instances in state `READY`.
- **`session_map`**: Dictionary mapping `profile_id -> SessionStateRecord`.
- **`wave_status`**: Dictionary mapping `wave_number (1-6) -> WaveExecutionStatus`.
- **`execution_cursor`**: [`ExecutionCursor`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L12) tracking active wave, session, step index, and execution state (`READY`).

### 2.3 Resource Tracking & State Control
- **`budget_status`**: [`BudgetStatus`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L50) tracking total USD budget ($50.00), spent USD ($0.00), and per-wave / per-profile allocations.
- **`retry_status`**: [`RetryStatus`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L65) tracking retry counters (all initialized to 0) and max retry limits.
- **`checkpoint_status`**: [`CheckpointStatus`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L77) capturing restorable initialization checkpoint ID (`chk-w1-init-xxxxxx`).

### 2.4 Subsystem Connections
- **`event_bus_references`**: Channel mapping for `execution_events`, `state_transitions`, `artifact_events`, `governance_events`, `trace_events`, and `log_events`.
- **`storage_references`**: Connected directory paths for `.oniroute/` subdirectories (`sessions/`, `traces/`, `logs/`, `history/`, `reports/`, `artifacts/`).
- **`workspace_references`**: Resolved workspace ID, root path, engine root path, read-only safety assertion, and project framework type.

### 2.5 Integrity Verification
- **`evidence`**: Contains validation metrics (`all_profiles_initialized`, `all_sessions_mapped`, `no_orphan_sessions`, `wave_integrity`, `budget_initialized`, `checkpoint_initialized`, `storage_connected`, `deterministic_snapshot`).
- **`snapshot_hash`**: SHA-256 hash computed over canonical JSON payload.
