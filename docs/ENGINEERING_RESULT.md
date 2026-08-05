# Engineering Result Schema Specification (Phase P5.E1)

## 1. Schema Specification

The [`EngineeringResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/engineering/models.py#L9) is an immutable Pydantic data model (`model_config = ConfigDict(frozen=True)`).

```json
{
  "result_id": "engres-123456",
  "contract_id": "ctr-0001",
  "profile_id": "prf-be-eng",
  "modified_files": [],
  "created_files": ["src/main.py"],
  "artifacts": ["src/main.py"],
  "execution_time_ms": 12.45,
  "provider": "oniroute-local-engine",
  "model": "gemini-2.5-pro",
  "token_usage": {
    "prompt_tokens": 120,
    "completion_tokens": 80,
    "total_tokens": 200
  },
  "cost_usd": 0.0004,
  "trace_references": ["trc-ctr-0001"],
  "evidence": {
    "contract_id": "ctr-0001",
    "boundary_safety_verified": true,
    "read_only_engine_verified": true,
    "bytes_written": 450
  },
  "timestamp": "2026-08-06T01:08:00Z",
  "result_hash": "c8d9e0f1..."
}
```

---

## 2. Field Definitions

| Field Name | Type | Description |
|---|---|---|
| `result_id` | `str` | Unique result identifier (`engres-xxxxxx`) |
| `contract_id` | `str` | Associated engineering contract ID |
| `profile_id` | `str` | Assigned Agent Profile ID |
| `modified_files` | `List[str]` | List of modified target file paths |
| `created_files` | `List[str]` | List of created target file paths |
| `artifacts` | `List[str]` | List of generated implementation artifact paths |
| `execution_time_ms` | `float` | Code generation execution latency in ms |
| `provider` | `str` | Model provider name |
| `model` | `str` | LLM model name |
| `token_usage` | `Dict[str, int]` | Token consumption metrics |
| `cost_usd` | `float` | Execution cost in USD |
| `trace_references` | `List[str]` | Trace IDs recorded |
| `evidence` | `Dict[str, Any]` | Validation evidence and safety check log |
| `timestamp` | `str` | ISO-8601 UTC completion timestamp |
| `result_hash` | `str` | SHA-256 hash of result payload |
