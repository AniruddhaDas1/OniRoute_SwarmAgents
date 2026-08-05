# Skill Intelligence Pipeline Specification

## 1. Sequential Pipeline Flow

The Skill Intelligence pipeline processes requirements sequentially down to agent profile execution contracts:

```
EngineeringExecutionPlan
         │
         ▼
[Stage 1: Skill Discovery Engine]  (runtime/skills/discovery.py)
         │
         ▼ SkillSelectionReport
[Stage 2: Skill Ranking Engine]    (runtime/skills/ranking.py)
         │
         ▼ RankedSkillReport
[Stage 3: Skill Bundling Engine]   (runtime/skills/bundling.py)
         │
         ▼ ExecutionSkillBundleReport
[Stage 4: Agent Profile Builder]  (runtime/skills/builder.py)
         │
         ▼ AgentProfileReport
Autonomous Swarm Runtime (Phase P3)
```

---

## 2. Immutable Data Contracts

All models are frozen Pydantic schemas defined in [`runtime/skills/models.py`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py):

1. **`SkillSelectionReport`**: Captures discovered skill records, coverage metrics, required knowledge, packages, and MCP tools.
2. **`RankedSkillReport`**: Captures 1-indexed rank order, assigned priority levels (`CRITICAL`, `HIGH`, `MEDIUM`, `SUPPORT`, `LOW`, `OPTIONAL`), score breakdowns, and skill DAG dependency chains.
3. **`ExecutionSkillBundleReport`**: Captures discipline bundles (`Frontend`, `Backend`, `DevOps`, etc.), deliverables, and inter-bundle DAG execution order.
4. **`AgentProfileReport`**: Captures synthesized `AgentProfile` definitions (`Frontend Engineer`, `Backend Specialist`, etc.), assigned bundle references, and inter-profile execution ordering.
