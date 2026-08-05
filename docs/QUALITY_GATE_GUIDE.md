# Quality Gate Developer & Integration Guide (Phase P5.E2)

## 1. Developer Integration API

Developers and agents can programmatically invoke cross-agent review:

```python
from runtime.engineering import EngineeringWorkerEngine
from runtime.review import QualityGateEngine, QualityReport

# 1. Obtain EngineeringResults from Phase P5.E1
worker = EngineeringWorkerEngine()
results = worker.execute_all_contracts(contract_report)

# 2. Run Quality Gate Review for Phase P5.E2
gate_engine = QualityGateEngine()
quality_reports = gate_engine.review_all_results(results)

# 3. Inspect quality reports and approval status
assert len(quality_reports) == len(results)
for q in quality_reports:
    assert isinstance(q, QualityReport)
    print(f"Report ID: {q.report_id}, Status: {q.approval_status}, Findings: {len(q.findings)}")
```

---

## 2. CLI Usage Guide

```bash
# Perform Quality Gate review on generated EngineeringResults
oniroute review

# Output raw JSON QualityReport list
oniroute review --json

# Run with explicit EngineeringResult JSON file
oniroute review --result /path/to/engineering_result.json
```

---

## 3. Transition to Phase P5.E3 (Self-Healing)

If a [`QualityReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/review/models.py#L31) has `required_fixes` or status `REJECTED`/`CONDITIONALLY_APPROVED`, **Phase P5.E3 (Self-Healing)** will consume `QualityReport` to resolve findings, regenerate affected implementations, and produce an updated `EngineeringResult`.
