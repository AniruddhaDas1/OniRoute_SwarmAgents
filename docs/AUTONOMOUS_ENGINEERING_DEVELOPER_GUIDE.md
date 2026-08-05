# Autonomous Engineering Developer & Integration Guide (Phase P5)

## 1. End-to-End Programmatic Pipeline Usage

```python
from runtime.engineering import EngineeringWorkerEngine, AutonomousEngineeringCertificationEngine
from runtime.review import QualityGateEngine
from runtime.healing import RepairPlanner, SelfHealingEngine
from runtime.validation import VerificationEngine, AcceptanceEngine

# 1. Execute Engineering Worker (P5.E1)
worker = EngineeringWorkerEngine()
results = worker.execute_all_contracts(contract_report)

# 2. Execute Quality Gate Review (P5.E2)
gate_engine = QualityGateEngine()
quality_reports = gate_engine.review_all_results(results, contract_report)

# 3. Execute Self-Healing Repair (P5.E3)
planner = RepairPlanner()
healing_engine = SelfHealingEngine()
updated_results = []
result_map = {r.result_id: r for r in results}
for q_rep in quality_reports:
    repair_plan = planner.create_repair_plan(q_rep)
    orig_res = result_map.get(q_rep.engineering_result_id, results[0])
    upd_res = healing_engine.apply_repairs(repair_plan, orig_res, workspace_root)
    updated_results.append(upd_res)

# 4. Execute Verification & Acceptance (P5.E4)
vrf_engine = VerificationEngine()
verifications = vrf_engine.verify_all_results(updated_results, workspace_root)
acpt_engine = AcceptanceEngine()
acceptance_reports = acpt_engine.evaluate_all_acceptances(verifications)

# 5. Execute Autonomous Engineering Certification & Freeze (P5.E5)
cert_engine = AutonomousEngineeringCertificationEngine()
cert_report = cert_engine.certify_engineering_pipeline(
    acceptance_reports=acceptance_reports,
    verification_results=verifications,
    updated_results=updated_results,
    quality_reports=quality_reports,
    engineering_results=results,
    contract_report=contract_report,
)

assert cert_report.production_readiness is True
```

---

## 2. CLI Execution Commands

```bash
# Certify and freeze Autonomous Engineering Subsystem
oniroute certify-engineering

# Output raw JSON EngineeringCertificationReport
oniroute certify-engineering --json
```
