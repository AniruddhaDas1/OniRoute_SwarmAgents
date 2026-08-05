# Phase P3.A1 — Mission Deployment Planner Specification

## 1. Subsystem Overview
Phase P3.A1 (**Mission Deployment Planner**) is the first stage of Phase 3 (Swarm Execution Planning) in OniRoute v1.2.

```
EngineeringExecutionPlan -> AgentProfileReport -> Mission Deployment Planner (P3.A1) -> MissionDeploymentPlan -> Swarm Initialization (P3.A2)
```

The Mission Deployment Planner processes an immutable [`EngineeringExecutionPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/plan.py#L34) and an immutable [`AgentProfileReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L187) to synthesize a deployment-ready [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) contract.

It operates **strictly without**:
- Executing code or modifying Runtime state
- Creating runtime sessions or swarm agent instances
- Invoking AI or LLM models
- Modifying underlying Agent Profiles, Skills, or Organization Blueprints

---

## 2. Responsibilities & Pipeline Boundaries

- **Input Contract**: Consumes **ONLY** [`EngineeringExecutionPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/plan.py#L34) and [`AgentProfileReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Projects/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L187).
- **Output Contract**: Produces **ONLY** [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180).
- **Responsibilities**:
  1. Calculate 6-Wave execution membership using AgentProfile dependencies and discipline classifications.
  2. Structure parallel execution groups for non-dependent workloads within waves.
  3. Map sequential inter-profile dependencies.
  4. Generate automated review gates (e.g. unit tests, security scans, governance checks).
  5. Generate formal approval gates and human-in-the-loop checkpoints.
  6. Define inter-profile artifact routing pathways.
  7. Construct execution retry, failure handling, rollback, and timeout policies.
  8. Allocate execution budget deterministically across waves and agent profiles.
  9. Generate evidence metrics and compute the SHA-256 Deployment Hash.

---

## 3. Mandatory Component Reuse Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| `EngineeringExecutionPlan` | Read-only input context for constraints, risks, and milestones | Integrated in `MissionDeploymentPlanner.create_deployment_plan` |
| `AgentProfileReport` | Read-only input context for profiles, roles, and dependencies | Consumed and scheduled into waves |
| `Execution Blueprint (v1.1)` | Structural alignment for agent roles & capabilities | Zero changes required |
| `Mission models` | Referenced mission identifier & requirements context | Preserved unchanged |
| `Runtime contracts` | Read-only imports from `runtime` | Preserved unchanged |
| `Dependency graph` | Consumed DAG structure for topological wave resolution | Preserved and validated |
| `Workflow metadata` | Consumed workflow definitions from `RepositoryRegistry` | Preserved unchanged |
| `Governance models` | Consumed policy definitions and budget rules | Preserved unchanged |

---

## 4. CLI Usage

```bash
# Display formatted deployment plan tables (Waves, Parallel Groups, Gates, Routes, Budget)
oniroute deployment "Build React FastAPI application"

# Output raw JSON MissionDeploymentPlan representation
oniroute deployment "Build React FastAPI application" --json
```
