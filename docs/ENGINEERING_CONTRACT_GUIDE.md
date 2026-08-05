# Engineering Contracts Developer & Integration Guide (Phase P4.G4)

## 1. Developer Integration API

Developers and agents can programmatically generate engineering contracts from implementation allocations:

```python
from runtime.allocation import ImplementationAllocationEngine
from runtime.contracts import EngineeringContractEngine, EngineeringContractReport

# 1. Obtain ImplementationAllocationReport from Phase P4.G3
allocation_engine = ImplementationAllocationEngine()
allocation_report = allocation_engine.allocate_implementation(blueprint_report)

# 2. Generate EngineeringContractReport for Phase P4.G4
contract_engine = EngineeringContractEngine()
contract_report = contract_engine.generate_contracts(allocation_report)

# 3. Inspect generated contracts and execution waves
assert isinstance(contract_report, EngineeringContractReport)
print(f"Report ID: {contract_report.report_id}")
print(f"Contracts Generated: {len(contract_report.contracts)}")
print(f"Waves Scheduled: {len(contract_report.execution_waves)}")
```

---

## 2. CLI Usage Guide

To generate and inspect engineering contracts from the command line:

```bash
# Run contracts generation on current workspace
oniroute contracts

# Output formatted JSON report
oniroute contracts --json

# Run with explicit allocation report path
oniroute contracts --allocation path/to/allocation_report.json
```

---

## 3. Autonomous Engineering (P5) Execution Interface

In **Phase P5 (Autonomous Engineering)**, autonomous coding agents execute **ONLY** from an immutable [`EngineeringContractReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/contracts/models.py#L35).

Each agent receives its assigned `EngineeringContract` specifying:
- Exact target path and expected outputs
- Explicit interface & architecture constraints
- Security, performance, testing, and acceptance criteria
- Assigned wave execution order (1 through 6)
