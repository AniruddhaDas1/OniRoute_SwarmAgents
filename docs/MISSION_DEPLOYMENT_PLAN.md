# Phase P3.A1 — Mission Deployment Plan Specification

## 1. Schema Definition
The [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) is an immutable Pydantic data contract produced by the [`MissionDeploymentPlanner`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/planner.py#L52).

```json
{
  "plan_id": "dep-a1b2c3",
  "mission_id": "msn-123456",
  "execution_plan_id": "plan-123456",
  "agent_profiles": [ ... ],
  "execution_waves": [ ... ],
  "parallel_execution_groups": { ... },
  "parallel_groups": [ ... ],
  "sequential_dependencies": { ... },
  "review_gates": [ ... ],
  "approval_gates": [ ... ],
  "human_approval_checkpoints": [ ... ],
  "artifact_routes": [ ... ],
  "retry_rules": { ... },
  "failure_handling": { ... },
  "rollback_strategy": { ... },
  "execution_constraints": [ ... ],
  "budget_allocation": { ... },
  "timeout_rules": { ... },
  "evidence": { ... },
  "timestamp": "2026-08-05T20:40:55+00:00",
  "deployment_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

---

## 2. Model Fields & Components

### 2.1 Primary Identifiers & References
- **`plan_id`**: String identifier prefixed with `dep-` (e.g. `dep-a1b2c3`).
- **`mission_id`**: Associated mission identifier from [`EngineeringExecutionPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/plan.py#L34).
- **`execution_plan_id`**: Associated plan identifier.
- **`agent_profiles`**: List of immutable [`AgentProfile`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L164) contracts.

### 2.2 Workload Distribution
- **`execution_waves`**: List of 6 [`ExecutionWave`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L32) objects.
- **`parallel_execution_groups`**: Mapping of wave keys (e.g. `wave_1`) to lists of parallel profile IDs.
- **`parallel_groups`**: List of [`ParallelGroup`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L48) records.
- **`sequential_dependencies`**: Profile dependency mapping (`profile_id -> list of prerequisite_profile_ids`).

### 2.3 Quality, Governance & Security Gates
- **`review_gates`**: List of [`ReviewGate`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L69) items (e.g. `rg-w2-core-review`, `rg-w3-integration-review`, `rg-w4-quality-gate`, `rg-w5-governance-review`).
- **`approval_gates`**: List of [`ApprovalGate`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L83) items (e.g. `ag-w3-architecture-approval`, `ag-w6-release-approval`).
- **`human_approval_checkpoints`**: List of [`HumanApprovalCheckpoint`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L97) items requiring explicit human sign-off.

### 2.4 Data Flow & Routing
- **`artifact_routes`**: List of [`ArtifactRoute`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L110) records mapping producer deliverables to downstream consumer profiles across waves.

### 2.5 Execution Policies & Budget
- **`retry_rules`**: Immutable [`RetryPolicy`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L123) (max retries, backoff factor, per-profile overrides).
- **`failure_handling`**: Immutable [`FailureHandlingPolicy`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L136) (action, threshold, isolation, rollback flag).
- **`rollback_strategy`**: Immutable [`RollbackPolicy`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L147) (strategy, checkpoints, target wave).
- **`timeout_rules`**: Immutable [`TimeoutPolicy`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L157) (mission, wave, profile timeouts).
- **`budget_allocation`**: Immutable [`ExecutionBudgetAllocation`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L168) (total USD budget, wave split, profile split).

### 2.6 Validation Evidence & Hash
- **`evidence`**: Validation assertions dictionary (`no_cyclic_execution`, `every_profile_scheduled`, `no_orphan_profiles`, `valid_review_path`, `valid_approval_path`, `valid_artifact_routing`, `deterministic_execution_order`).
- **`timestamp`**: ISO-8601 UTC timestamp.
- **`deployment_hash`**: SHA-256 Deployment Hash computed over canonical JSON payload.
