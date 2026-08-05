# Phase P3.A4 — Swarm Coordination Specification

## 1. Subsystem Overview
Phase P3.A4 (**Swarm Coordination**) is the fourth stage of Phase 3 (Swarm Execution Planning, Initialization, Execution & Coordination) in OniRoute v1.2.

```
RuntimeExecutionSnapshot -> Autonomous Execution (P3.A3) -> Swarm Coordination (P3.A4) -> Updated RuntimeExecutionSnapshot
```

This phase coordinates executing agents without changing execution logic, planning, or runtime scheduling:
- Inter-agent messaging and notifications
- Versioned shared context synchronization
- Deterministic artifact exchange and version lineage
- Inter-wave task handoffs and delivery acknowledgements
- Review & human approval gate consensus protocols

---

## 2. Responsibilities & Subsystem Boundaries

- **Input Contract**: Consumes **ONLY** [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125) and `List[SwarmExecutionResult]`.
- **Output Contract**: Produces **ONLY** updated [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125).
- **Responsibilities**:
  1. Dispatch inter-session notification messages via `MessageBus`.
  2. Register produced artifacts into [`ArtifactExchange`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/artifact_exchange.py#L32) with version semver (`v1.0.0`) and lineage.
  3. Deliver artifacts to receiving profiles and record confirmation status (`CONFIRMED`).
  4. Detect artifact naming and concurrent modification conflicts (`VERSION_BRANCH`).
  5. Synchronize versioned [`SharedContextSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/shared_context.py#L14) records.
  6. Generate inter-wave [`SwarmHandoffRecord`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/handoffs.py#L14) transfers.
  7. Evaluate review & approval gate consensus via [`SwarmConsensusEngine`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/consensus.py#L30).
  8. Update `coordination_evidence` in snapshot evidence metadata and recompute SHA-256 Snapshot Hash.

---

## 3. Mandatory Component Reuse Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L125) | Consumed as input; updated with coordination evidence | Consumed and updated in `SwarmCoordinationEngine.coordinate_swarm` |
| `ExecutionTaskQueue` | Reused for task dependency references | Preserved unchanged |
| `SwarmExecutionResult` | Consumed as input for produced artifacts & task outcomes | Read-only input |
| `Agent Runtime` | Reused agent session models | Preserved unchanged |
| `Event Bus` | Reused `MessageBus` for inter-session messages | Messaging integration |
| `Artifact Router` | Reused `ArtifactRouter` for file paths | Artifact path references |
| `Trace Storage` | Reused `TraceStorage` | Trace log references |
| `Log Storage` | Reused `LogStorage` | Execution log references |
| `History Storage` | Reused `ExecutionHistoryStorage` | History tracking |
| `Existing Governance` | Reused `PolicyEngine` and `BudgetTracker` | Verification |
| `Existing Review & Approval Gates` | Reused `ReviewCoordinator` and `ApprovalCoordinator` | Consensus evaluation |

---

## 4. CLI Reference

```bash
# Coordinate executing agents, artifact exchanges, handoffs, and consensus decisions
oniroute coordinate "Build React FastAPI web application"

# Output raw JSON representation of coordination summary and updated snapshot
oniroute coordinate "Build React FastAPI web application" --json
```
