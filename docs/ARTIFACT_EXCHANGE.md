# Phase P3.A4 — Artifact Exchange Specification

## 1. Subsystem Overview
The [`ArtifactExchange`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/artifact_exchange.py#L32) registers, versions, tracks lineage, and delivers produced artifacts without regenerating any code or files.

```
SwarmExecutionResult ──► ArtifactExchange ──► ExchangeArtifactRecord (v1.0.0) ──► Recipient Profiles
```

---

## 2. Invariant Rules

- **Zero Regeneration**: Artifacts are registered from `SwarmExecutionResult` outputs. Never regenerated.
- **Semver Versioning**: Each registered artifact is assigned a version string (`v1.0.0`).
- **Lineage Tracking**: Tracks parent artifact IDs to preserve transformation history.
- **Delivery Acknowledgements**: Tracks `DELIVERED` and `CONFIRMED` states upon transfer to downstream profiles.
- **Conflict Resolution**: Detects duplicate artifact names or concurrent modifications across parallel tasks and applies `VERSION_BRANCH` resolution.

---

## 3. ExchangeArtifactRecord Schema

| Field | Type | Description |
|---|---|---|
| `exchange_id` | `str` | Unique exchange ID (e.g. `ex-art-task-w1-dev`) |
| `artifact_id` | `str` | Target artifact ID |
| `owner_profile_id` | `str` | Owner AgentProfile ID |
| `owner_session_id` | `str` | Owner AgentSession ID |
| `receiving_profile_ids` | `List[str]` | Target receiving AgentProfile IDs |
| `name` | `str` | Artifact name |
| `version` | `str` | Semver version string (`v1.0.0`) |
| `artifact_type` | `str` | Artifact category |
| `lineage` | `List[str]` | Parent artifact IDs |
| `delivery_status` | `str` | Status (`DELIVERED`, `CONFIRMED`) |
| `conflict_status` | `str` | Conflict state (`NO_CONFLICT`, `CONFLICT_DETECTED`, `RESOLVED`) |
| `exchange_hash` | `str` | SHA-256 exchange hash |
| `registered_at` | `str` | ISO-8601 UTC timestamp |
