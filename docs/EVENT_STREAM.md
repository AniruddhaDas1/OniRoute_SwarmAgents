# Execution Event Stream Specification (Phase P6.D2)

## 1. Supported Event Types

The [`ExecutionEventStream`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/experience/stream.py#L17) publishes 12 immutable event types:

| Event Type | Description |
|---|---|
| `MISSION_STARTED` | Emitted when natural language mission begins execution |
| `AGENT_STARTED` | Emitted when an agent profile starts a wave task |
| `AGENT_FINISHED` | Emitted when an agent profile completes a wave task |
| `REVIEW_STARTED` | Emitted when Quality Gate cross-agent audit begins |
| `REVIEW_FINISHED` | Emitted when Quality Gate completes audit |
| `HEALING_STARTED` | Emitted when Self-Healing repair planner begins |
| `HEALING_FINISHED` | Emitted when Self-Healing applies code repairs |
| `VERIFICATION_STARTED` | Emitted when deterministic build & coverage checks begin |
| `ACCEPTANCE_COMPLETED` | Emitted when release acceptance criteria pass |
| `MISSION_COMPLETED` | Emitted when end-to-end pipeline completes and is certified |
| `MISSION_FAILED` | Emitted on unhandled runtime or execution errors |
| `CANCELLED` | Emitted on operator Ctrl+C graceful cancellation |

---

## 2. Event Schema

```json
{
  "event_id": "evt-123456",
  "event_type": "AGENT_STARTED",
  "mission_id": "msn-987654",
  "session_id": "sess-active-001",
  "stage_name": "ENGINEERING",
  "agent_id": "prf-frontend-dev",
  "agent_role": "Frontend Engineer",
  "task_description": "Creating React components for property listings",
  "progress_percentage": 45.0,
  "files_created": ["components/PropertyCard.tsx"],
  "files_modified": [],
  "quality_score": 9.8,
  "production_ready": false,
  "timestamp": "2026-08-06T00:00:00Z"
}
```
