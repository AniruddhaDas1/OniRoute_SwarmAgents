# Phase P3.A2 — Swarm Initialization Specification

## 1. Subsystem Overview
Phase P3.A2 (**Swarm Initialization**) is the second stage of Phase 3 (Swarm Execution Planning & Initialization) in OniRoute v1.2.

```
MissionDeploymentPlan (P3.A1) -> Swarm Initialization (P3.A2) -> RuntimeExecutionSnapshot -> Autonomous Execution (P3.A3)
```

The Swarm Initialization engine processes an immutable [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) to instantiate runtime sessions, allocate execution context, connect workspace storage, and produce an immutable [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125).

It operates **strictly without**:
- Executing code or running workflows
- Invoking LLMs or AI providers
- Generating artifacts or modifying source files

---

## 2. Responsibilities & Subsystem Boundaries

- **Input Contract**: Consumes **ONLY** [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180).
- **Output Contract**: Produces **ONLY** [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125).
- **Responsibilities**:
  1. Generate unique Execution UUID (`exec-uuid-xxxxxx`) and Snapshot ID (`snap-xxxxxx`).
  2. Instantiate one [`AgentSession`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/agent/models.py#L184) in state `READY` per scheduled Agent Profile.
  3. Map profile-to-session bindings and wave execution statuses.
  4. Initialize `ExecutionCursor` position at Wave 1 (`current_step_index = 0`, `state = READY`).
  5. Initialize unspent `BudgetStatus` ($50.00 total, $0.00 spent).
  6. Establish restorable `CheckpointStatus` (`chk-w1-init-xxxxxx`).
  7. Register `EventBusReferences` for runtime event channels.
  8. Connect `StorageReferences` for `.oniroute/` directories (`sessions/`, `traces/`, `logs/`, `history/`, `reports/`, `artifacts/`).
  9. Assert workspace read-only safety boundaries via `WorkspaceReferences`.
  10. Compute validation evidence metrics and SHA-256 Snapshot Hash.

---

## 3. Mandatory Component Reuse Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) | Read-only input contract for waves, profiles, budget, and policies | Consumed in `SwarmInitializationEngine.initialize_swarm` |
| `Agent Runtime models` | Reused `AgentSession`, `RuntimeState`, `ExecutionStatus`, `RuntimeMetrics`, `ExecutionEvent` | Integrated into session instantiation in state `READY` |
| `Agent Session models` | `AgentSession` instantiated per `AgentProfile` | Initialized in state `READY` without execution |
| `Runtime contracts` | Reused `SessionCoordinator`, `SessionManager`, `SessionRegistry` | Preserved unchanged |
| `Workspace Runtime` | Reused `WorkspaceManager` and `WorkspaceContext` | Preserved unchanged |
| `Artifact Router` | Reused `ArtifactRouter` for destination pathways | Connected without file creation |
| `Trace Storage` | Reused `TraceStorage` for execution trace directory paths | Connected without writing |
| `Log Storage` | Reused `LogStorage` for execution log directory paths | Connected without writing |
| `Session Storage` | Reused `SessionStorage` for session directory creation | Connected to workspace storage |
| `History Storage` | Reused `HistoryStorage` for history tracking paths | Connected without writing |
| `Governance contracts` | Reused `BudgetTracker` and budget allocation models | Integrated into `BudgetStatus` |

---

## 4. CLI Reference

```bash
# Initialize Swarm and display execution UUID, READY sessions, waves, budget, and storage
oniroute initialize "Build React FastAPI application"

# Output raw JSON RuntimeExecutionSnapshot representation
oniroute initialize "Build React FastAPI application" --json
```
