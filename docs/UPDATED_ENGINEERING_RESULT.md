# Updated Engineering Result Schema Specification (Phase P5.E3)

## 1. Schema Specification

The [`UpdatedEngineeringResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/healing/models.py#L38) is an immutable Pydantic data model (`model_config = ConfigDict(frozen=True)`).

```json
{
  "updated_result_id": "updres-123456",
  "original_result_id": "engres-987654",
  "repair_plan_id": "rprplan-112233",
  "applied_repairs": ["act-0001"],
  "modified_files": ["src/main.py"],
  "created_files": [],
  "resolved_findings": ["fnd-arch-0001"],
  "remaining_findings": [],
  "artifacts": ["src/main.py"],
  "execution_time_ms": 8.45,
  "token_usage": {
    "prompt_tokens": 60,
    "completion_tokens": 40,
    "total_tokens": 100
  },
  "cost_usd": 0.0002,
  "trace_references": ["trc-rprplan-112233"],
  "evidence": {
    "original_result_id": "engres-987654",
    "repair_plan_id": "rprplan-112233",
    "applied_action_count": 1,
    "resolved_finding_count": 1,
    "boundary_safety_verified": true,
    "read_only_engine_verified": true
  },
  "timestamp": "2026-08-06T01:15:00Z",
  "updated_result_hash": "d4e5f6a1..."
}
```

---

## 2. Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `updated_result_id` | `str` | Unique updated result ID (`updres-xxxxxx`) |
| `original_result_id` | `str` | Original EngineeringResult ID |
| `repair_plan_id` | `str` | Associated RepairPlan ID |
| `applied_repairs` | `List[str]` | List of applied RepairAction IDs |
| `modified_files` | `List[str]` | List of modified target file relative paths |
| `created_files` | `List[str]` | List of created file relative paths |
| `resolved_findings` | `List[str]` | List of resolved QualityFinding IDs |
| `remaining_findings` | `List[str]` | List of unresolved QualityFinding IDs |
| `artifacts` | `List[str]` | Consolidated list of target artifact paths |
| `execution_time_ms` | `float` | Repair execution duration in ms |
| `token_usage` | `Dict[str, int]` | Incremental token consumption |
| `cost_usd` | `float` | Incremental cost in USD |
| `trace_references` | `List[str]` | Trace IDs recorded |
| `evidence` | `Dict[str, Any]` | Validation evidence and safety check log |
| `timestamp` | `str` | ISO-8601 UTC completion timestamp |
| `updated_result_hash` | `str` | SHA-256 hash of updated result payload |
