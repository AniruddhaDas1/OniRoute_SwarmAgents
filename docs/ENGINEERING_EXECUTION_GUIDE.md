# Autonomous Engineering Execution Guide (Phase P5.E1)

## 1. Developer Integration API

Developers and agents can programmatically execute code generation for contracts:

```python
from runtime.contracts import EngineeringContractEngine
from runtime.engineering import EngineeringWorkerEngine, EngineeringResult

# 1. Obtain EngineeringContractReport from Phase P4
contract_engine = EngineeringContractEngine()
contract_report = contract_engine.generate_contracts(allocation_report)

# 2. Execute Autonomous Engineering Worker
worker_engine = EngineeringWorkerEngine()
results = worker_engine.execute_all_contracts(contract_report)

# 3. Inspect generated results and created files
assert len(results) == len(contract_report.contracts)
for r in results:
    assert isinstance(r, EngineeringResult)
    print(f"Result ID: {r.result_id}, Files: {r.created_files}")
```

---

## 2. CLI Usage Guide

```bash
# Execute autonomous engineering worker for current workspace
oniroute engineer

# Output raw JSON list of EngineeringResults
oniroute engineer --json

# Run with explicit EngineeringContractReport JSON file
oniroute engineer --contracts /path/to/contract_report.json
```

---

## 3. Transition to Phase P5.E2 (Cross-Agent Review)

Once engineering workers generate source code, **Phase P5.E2 (Cross-Agent Review)** will review, critique, and verify the generated work before it is accepted into the main codebase branch.
