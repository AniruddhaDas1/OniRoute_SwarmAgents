# Phase P2.S2 — Deterministic Skill Ranking Specification

## 1. Subsystem Overview
Phase P2.S2 (**Deterministic Skill Ranking**) is the second stage of the Skill Intelligence subsystem in OniRoute v1.2.

```
EngineeringExecutionPlan -> Skill Discovery (P2.S1) -> SkillSelectionReport -> Skill Ranking (P2.S2) -> RankedSkillReport -> Skill Bundling (P2.S3)
```

Skill Ranking processes the [`SkillSelectionReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L48) and [`EngineeringExecutionPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/plan.py#L34) to determine which discovered skills are most valuable, assigning deterministic weighted scores, priority levels, graph-based dependency orderings, and producing an immutable [`RankedSkillReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L54).

It operates **strictly without**:
- Natural language / prompt parsing
- Repository scanning or workspace AST inspection
- AI invocation or LLM calls
- Skill re-discovery or discovery logic duplication

---

## 2. Multi-Factor Scoring Model

Every discovered skill receives a normalized score ($0.0 - 100.0$) based on 7 deterministic factors:

| Scoring Factor | Weight | Description |
| :--- | :--- | :--- |
| **Execution Priority** | $15.0$ pts | Category tier (Foundation/Platform vs Core vs Supporting vs Utility) |
| **Discipline Match** | $20.0$ pts | Direct alignment with `plan.required_disciplines` |
| **Deliverable Match** | $15.0$ pts | Alignment with `plan.required_deliverables` |
| **Technology Match** | $15.0$ pts | Alignment with `plan.technology_stack` |
| **Dependency Weight** | $15.0$ pts | Prerequisites required by dependent skills or workflows |
| **Registry Trust** | $10.0$ pts | Official registry skill ($10.0$) vs Community skill ($6.0$) |
| **Skill Completeness** | $10.0$ pts | Resolution of required knowledge sources, packages, and compatible workflows |

---

## 3. Priority Levels

Skills are classified into 6 priority levels:
- `CRITICAL`: Score $\ge 85.0$ or Foundation/Platform/Architecture skill.
- `HIGH`: Score $\ge 70.0$ or strong technology stack and discipline match.
- `MEDIUM`: Score $\ge 55.0$ supporting core engineering tasks.
- `SUPPORT`: Dependents $\ge 1$ supporting higher priority skills.
- `LOW`: Score $\ge 40.0$.
- `OPTIONAL`: Score $< 40.0$.

---

## 4. CLI Reference

```bash
# Display formatted ranked skill tables and summaries
oniroute rank-skills "Build React FastAPI application"

# Output raw JSON RankedSkillReport
oniroute rank-skills "Build React FastAPI application" --json
```
