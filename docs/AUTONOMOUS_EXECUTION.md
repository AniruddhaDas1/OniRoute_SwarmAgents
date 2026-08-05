# Phase P3.A3 — Autonomous Execution Specification

## 1. Subsystem Overview
Phase P3.A3 (**Autonomous Execution**) is the third stage of Phase 3 (Swarm Execution Planning & Initialization) in OniRoute v1.2.

```
RuntimeExecutionSnapshot (P3.A2) -> Execution Task Queue -> Autonomous Execution (P3.A3) -> Updated RuntimeExecutionSnapshot
```

This is the **FIRST phase** authorized to:
- Execute agent sessions
- Invoke LLM model providers
- Execute MCP tools
- Produce artifact deliverables
- Drive runtime state transitions (`READY` -> `RUNNING` -> `COMPLETED`)

---

## 2. Responsibilities & Subsystem Boundaries

- **Input Contract**: Consumes **ONLY** [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125).
- **Output Contracts**:
  - Updated [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125)
  - List of [`SwarmExecutionResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/result.py#L11) records
  - Physical workspace artifacts, logs, traces, and execution history
- **Responsibilities**:
  1. Construct deterministic `ExecutionTaskQueue` from snapshot.
  2. Execute tasks wave by wave (Waves 1 to 6).
  3. Enforce budget limits ($50.00 total) and halt on exhaustion.
  4. Enforce retry, rollback, and timeout policies.
  5. Route generated artifacts through `ArtifactRouter` and `SessionStorage`.
  6. Write logs to `LogStorage` and execution traces to `TraceStorage`.
  7. Advance `ExecutionCursor` position across waves.
  8. Update `wave_status`, `session_map`, and session states (`READY` -> `COMPLETED`).
  9. Recompute SHA-256 Snapshot Hash for the updated state.

---

## 3. Mandatory Component Reuse Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125) | Consumed as input contract; updated upon completion | Consumed and updated in `AutonomousExecutionEngine.execute_swarm` |
| `Agent Runtime` | Reused `AgentExecutionEngine`, `AgentSession`, `RuntimeState`, `ExecutionStatus` | Session state transitions and execution driving |
| `Session Manager` | Reused `SessionManager`, `SessionCoordinator`, `SessionRegistry` | Session lifecycle management |
| `Invocation Engine` | Reused `InvocationEngine` & provider adapters (`OllamaAdapter`, `OpenAICompatibleAdapter`) | Provider invocations |
| `UMAL` | Reused `ModelManager` for model resolution | Model selection |
| `Governance Engine` | Reused `PolicyEngine`, `BudgetTracker`, `AuditEngine` | Budget and permission verification |
| `Artifact Router` | Reused `ArtifactRouter` | Artifact destination routing |
| `Trace Storage` | Reused `TraceStorage` | Execution trace log persistence |
| `Log Storage` | Reused `LogStorage` | Execution log persistence |
| `History Storage` | Reused `ExecutionHistoryStorage` | History record persistence |
| `Event Bus` | Reused runtime execution events | Event registration |
| `MCP Adapters` | Reused `ToolCatalog`, `ToolResolver`, `ToolSelector` | Tool execution |
| `Model Providers` | Reused registered provider adapters | Invocation dispatch |

---

## 4. CLI Reference

```bash
# Execute Swarm autonomously across Waves 1 to 6 and display execution summary
oniroute execute "Build React FastAPI web application"

# Output raw JSON snapshot and task execution results
oniroute execute "Build React FastAPI web application" --json
```
