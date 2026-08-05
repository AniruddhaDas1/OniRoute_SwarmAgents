# Implementation Allocation Developer & Integration Guide (Phase P4.G3)

## 1. Developer Integration API

Developers and agents can programmatically invoke the [`ImplementationAllocationEngine`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/allocation/engine.py#L25) to allocate implementation targets:

```python
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.blueprint import ProjectBlueprintEngine
from runtime.allocation import ImplementationAllocationEngine, ImplementationAllocationReport

# 1. Obtain ProjectBlueprintReport from Phase P4.G2
blueprint_engine = ProjectBlueprintEngine()
blueprint_report = blueprint_engine.generate_blueprint(scaffold_report)

# 2. Generate ImplementationAllocationReport for Phase P4.G3
allocation_engine = ImplementationAllocationEngine()
allocation_report = allocation_engine.allocate_implementation(blueprint_report)

# 3. Inspect target allocations and execution order
assert isinstance(allocation_report, ImplementationAllocationReport)
print(f"Allocation ID: {allocation_report.allocation_id}")
print(f"Targets Allocated: {len(allocation_report.allocated_targets)}")
print(f"Execution Order Length: {len(allocation_report.execution_order)}")
```

---

## 2. CLI Usage Guide

To run implementation allocation from the command line:

```bash
# Run implementation allocation on current workspace
oniroute allocate

# Output formatted JSON report
oniroute allocate --json

# Run with explicit blueprint report path
oniroute allocate --blueprint path/to/blueprint_report.json
```

---

## 3. Strict Prohibitions

1. **No Source Code Generation**: Allocation engines assign target ownership ONLY. Code generation contracts are created in P4.G4.
2. **No Engine Root Writes**: Engine root remains read-only.
3. **No Orphan Files**: Every expected file, module, and directory must be assigned to an Agent Profile.
