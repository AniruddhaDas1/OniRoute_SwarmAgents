# Phase P2.S4 — Agent Profile Builder Specification

## 1. Subsystem Overview
Phase P2.S4 (**Agent Profile Builder**) is the fourth stage of the Skill Intelligence subsystem in OniRoute v1.2.

```
EngineeringExecutionPlan -> Skill Discovery (P2.S1) -> SkillSelectionReport -> Skill Ranking (P2.S2) -> RankedSkillReport -> Skill Bundling (P2.S3) -> ExecutionSkillBundleReport -> Agent Profile Builder (P2.S4) -> AgentProfileReport -> Runtime
```

The Agent Profile Builder processes the [`ExecutionSkillBundleReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L146) and [`EngineeringExecutionPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/plan.py#L34) to synthesize execution-ready, immutable [`AgentProfile`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L164) contracts.

It operates **strictly without**:
- Modifying Runtime or executing code
- AI invocation or LLM calls
- Natural language / prompt parsing
- Splitting execution bundles across multiple profiles

---

## 2. Profile Mapping Rules

- **Mapping Strategies**: Supports $1\text{ Bundle} \to 1\text{ Profile}$ (default) or $N\text{ Bundles} \to 1\text{ Profile}$.
- **Strict Bundle Ownership**: Bundles are atomic units of discipline skills. A bundle is **never split** across multiple profiles.
- **Validation**:
  - `every_bundle_assigned`: True
  - `no_orphan_bundles`: True
  - `no_duplicate_bundle_ownership`: True
  - `dependency_integrity`: True (Verified DAG)

---

## 3. CLI Reference

```bash
# Display synthesized agent profiles, roles, bundle mappings, and deliverables
oniroute profiles "Build React FastAPI application"

# Output raw JSON AgentProfileReport
oniroute profiles "Build React FastAPI application" --json
```
