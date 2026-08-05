# Phase P5.E3 — Self-Healing Specification

## 1. Subsystem Overview

**Self-Healing (Phase P5.E3)** is the automated code repair and remediation subsystem of OniRoute v1.2.

```
QualityReport (P5.E2) ──► RepairPlanner ──► RepairPlan ──► SelfHealingEngine (P5.E3) ──► UpdatedEngineeringResult ──► Validation & Acceptance (P5.E4)
```

The Self-Healing Subsystem converts approved quality review findings into a deterministic [`RepairPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/healing/models.py#L25) and applies targeted code repairs to produce an [`UpdatedEngineeringResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/healing/models.py#L38).

It operates **strictly without**:
- Introducing unrelated code changes
- Modifying engine root files
- Altering project assembly or planning artifacts

---

## 2. Safety Rules & Boundaries

1. **Target File Scope**: Repairs are strictly limited to target files listed in `repair_plan.target_files`.
2. **Engine Root Read-Only Safety**: Any repair attempt on engine root files raises a [`SelfHealingBoundaryViolation`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/healing/exceptions.py#L17).
3. **Immutable Output Contract**: Produces a frozen Pydantic [`UpdatedEngineeringResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/healing/models.py#L38).
