# Self-Healing Developer & Integration Guide (Phase P5.E3)

## 1. Developer Integration API

Developers and agents can programmatically execute self-healing code repairs:

```python
from runtime.healing import RepairPlanner, SelfHealingEngine, UpdatedEngineeringResult

# 1. Generate RepairPlan from QualityReport
planner = RepairPlanner()
repair_plan = planner.create_repair_plan(quality_report)

# 2. Execute SelfHealingEngine for targeted remediation
healing_engine = SelfHealingEngine()
updated_result = healing_engine.apply_repairs(repair_plan, original_result, workspace_root)

# 3. Inspect updated result
assert isinstance(updated_result, UpdatedEngineeringResult)
print(f"Updated Result ID: {updated_result.updated_result_id}")
print(f"Applied Repairs: {len(updated_result.applied_repairs)}")
print(f"Resolved Findings: {len(updated_result.resolved_findings)}")
```

---

## 2. CLI Usage Guide

```bash
# Execute Self-Healing repairs for current workspace
oniroute heal

# Output raw JSON list of UpdatedEngineeringResults
oniroute heal --json

# Run with explicit QualityReport and EngineeringResult JSON files
oniroute heal --report /path/to/quality_report.json --result /path/to/engineering_result.json
```

---

## 3. Transition to Phase P5.E4 (Validation & Acceptance)

Once Self-Healing generates an [`UpdatedEngineeringResult`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/healing/models.py#L38), **Phase P5.E4 (Validation & Acceptance)** will perform final acceptance checks, test suite validation, and production certification.
