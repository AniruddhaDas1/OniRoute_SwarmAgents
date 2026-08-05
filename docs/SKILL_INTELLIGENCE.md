# Skill Intelligence Subsystem Architecture Specification (Phase P2)

## 1. Executive Overview
The **Skill Intelligence Subsystem** (Phase P2) is a 4-stage processing pipeline within OniRoute v1.2 that converts declarative [`EngineeringExecutionPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/plan.py#L34) outputs into execution-ready [`AgentProfileReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L187) contracts for autonomous agent swarm execution.

```
EngineeringExecutionPlan -> Skill Discovery (P2.S1) -> SkillSelectionReport -> Skill Ranking (P2.S2) -> RankedSkillReport -> Skill Bundling (P2.S3) -> ExecutionSkillBundleReport -> Agent Profile Builder (P2.S4) -> AgentProfileReport -> Runtime
```

---

## 2. Core Architectural Guarantees

1. **Deterministic Handoff**: Every stage consumes **ONLY** the immutable payload produced by the preceding stage.
2. **Zero Runtime Side Effects**: The subsystem performs no code execution, runtime mutations, or network calls.
3. **Zero AI Invocation**: Discovery, ranking, bundling, and profile synthesis are 100% deterministic algorithms.
4. **Zero Prompt Parsing**: Subsystem engines operate strictly on structured Pydantic models.
5. **Zero Repository Scanning**: Repository scanning occurs exclusively during Phase P1.

---

## 3. Subsystem Stages

| Stage | Module | Input Contract | Output Contract | Primary Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| **P2.S1: Skill Discovery** | [`runtime/skills/discovery.py`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/discovery.py) | `EngineeringExecutionPlan` | `SkillSelectionReport` | Registry lookup across 12 skill categories. |
| **P2.S2: Skill Ranking** | [`runtime/skills/ranking.py`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/ranking.py) | `SkillSelectionReport` | `RankedSkillReport` | 7-factor weighted scoring & priority assignment. |
| **P2.S3: Skill Bundling** | [`runtime/skills/bundling.py`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/bundling.py) | `RankedSkillReport` | `ExecutionSkillBundleReport` | Discipline grouping & inter-bundle DAG ordering. |
| **P2.S4: Agent Profile Builder** | [`runtime/skills/builder.py`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/builder.py) | `ExecutionSkillBundleReport` | `AgentProfileReport` | Agent role profile synthesis & profile DAG ordering. |

---

## 4. CLI Subcommands

- `oniroute discover-skills` / `oniroute skills`
- `oniroute rank-skills`
- `oniroute bundles`
- `oniroute profiles`
