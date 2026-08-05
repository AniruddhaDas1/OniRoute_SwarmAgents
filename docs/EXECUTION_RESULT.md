# Phase P3.A3 — Execution Result Specification

## 1. Subsystem Overview
The [`SwarmExecutionResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/result.py#L11) model represents an immutable audit record produced upon completion of an autonomous swarm task during Phase P3.A3.

```json
{
  "task_id": "task-w1-devops-sess-dev",
  "session_id": "sess-devops-123456",
  "profile_id": "ap-devops-001",
  "wave_number": 1,
  "execution_status": "done",
  "produced_artifacts": [
    {
      "artifact_id": "art-task-w1-dev",
      "artifact_type": "config",
      "name": "DevOps Deliverable for DevOps Lead",
      "references": [".oniroute/artifacts/art-task-w1-dev.json"]
    }
  ],
  "consumed_tokens": 460,
  "execution_time_seconds": 0.005,
  "provider_used": "ollama",
  "model_used": "llama3",
  "cost_usd": 0.0069,
  "trace_references": [".oniroute/traces/sess-devops-123456.json"],
  "log_references": [".oniroute/logs/sess-devops-123456.log"],
  "evidence": {"tokens": 460, "cost": 0.0069},
  "timestamp": "2026-08-05T21:20:00+00:00"
}
```

---

## 2. Schema Fields

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | Associated ExecutionTask ID |
| `session_id` | `str` | Associated AgentSession ID |
| `profile_id` | `str` | Associated AgentProfile ID |
| `wave_number` | `int` | Wave number (1 to 6) |
| `execution_status` | `ExecutionStatus` | Final task status (`DONE`, `ERROR`, `SKIPPED`, `ABORTED`) |
| `produced_artifacts` | `List[ArtifactRecord]` | Artifact records produced during task execution |
| `consumed_tokens` | `int` | Total tokens consumed (prompt + completion) |
| `execution_time_seconds` | `float` | Execution elapsed time in seconds |
| `provider_used` | `str` | Provider used (e.g. `ollama`, `openai-compatible`) |
| `model_used` | `str` | Model name (e.g. `llama3`, `claude-3-5-sonnet`) |
| `cost_usd` | `float` | Execution cost in USD |
| `trace_references` | `List[str]` | Paths to execution trace files in `.oniroute/traces/` |
| `log_references` | `List[str]` | Paths to log files in `.oniroute/logs/` |
| `evidence` | `Dict[str, Any]` | Audit evidence metrics |
| `timestamp` | `str` | ISO-8601 UTC timestamp |
