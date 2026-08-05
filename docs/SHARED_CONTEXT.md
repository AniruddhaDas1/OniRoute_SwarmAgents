# Phase P3.A4 — Shared Context Specification

## 1. Subsystem Overview
The [`SharedContextManager`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/shared_context.py#L25) maintains versioned, immutable snapshots of the shared swarm context.

```
Genesis Context (v1) ──► Task Outcomes Merged ──► SharedContextSnapshot (v2)
```

---

## 2. SharedContextSnapshot Schema

```json
{
  "snapshot_id": "ctx-snap-v2-f453ef76",
  "version_index": 2,
  "previous_snapshot_id": "ctx-snap-w1-init-10fd3457",
  "context_data": {
    "execution_uuid": "exec-uuid-97a7a7",
    "mission_id": "msn-710572",
    "total_tasks_completed": 11,
    "last_updated_wave": 6
  },
  "conflict_log": [],
  "context_hash": "c710d91378786a279e96a7e575e5c936657cb27ae28d815cc310bd4f2294c1a8",
  "timestamp": "2026-08-05T21:30:00+00:00"
}
```

---

## 3. Supported Operations

- **Read**: Access shared key-values from the latest immutable snapshot.
- **Merge**: Compute non-destructive updates from completed task outcomes into a new versioned snapshot (`v+1`).
- **Conflict Detection**: Identify key-value collisions across concurrent wave tasks and append details to `conflict_log`.
- **Version History**: Retain parent snapshot lineage (`previous_snapshot_id`) for auditability.
