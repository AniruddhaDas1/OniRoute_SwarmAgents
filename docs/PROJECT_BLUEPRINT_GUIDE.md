# Project Blueprint Developer & Integration Guide (Phase P4.G2)

## 1. Developer Integration API

Developers and agents can programmatically invoke the [`ProjectBlueprintEngine`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/blueprint/engine.py#L18) to construct project blueprints from scaffold reports:

```python
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.blueprint import ProjectBlueprintEngine, ProjectBlueprintReport

# 1. Obtain WorkspaceScaffoldReport from Phase P4.G1
scaffold_engine = WorkspaceScaffoldEngine()
scaffold_report = scaffold_engine.scaffold_workspace(snapshot)

# 2. Generate ProjectBlueprintReport for Phase P4.G2
blueprint_engine = ProjectBlueprintEngine()
blueprint_report = blueprint_engine.generate_blueprint(scaffold_report)

# 3. Inspect module allocations and discipline ownership
assert isinstance(blueprint_report, ProjectBlueprintReport)
print(f"Blueprint ID: {blueprint_report.blueprint_id}")
print(f"Modules Allocated: {len(blueprint_report.project_modules)}")
print(f"Coverage Score: {blueprint_report.evidence['coverage_score']}")
```

---

## 2. CLI Usage Guide

To inspect project blueprints from the command line:

```bash
# Run blueprint generation on current workspace
oniroute blueprint-project

# Output formatted JSON report
oniroute blueprint-project --json

# Run with explicit scaffold report path
oniroute blueprint-project --scaffold path/to/scaffold.json
```

---

## 3. Strict Prohibitions

1. **No Source Code Generation**: Blueprint engines define directory and module contracts ONLY. Code generation begins in Phase P4.G4.
2. **No Engine Root Writes**: Never attempt to write into the read-only engine directory.
3. **No Orphan Modules**: Every module must be assigned to one of the 11 supported engineering disciplines (`Frontend`, `Backend`, `Database`, `Infrastructure`, `Security`, `Testing`, `Documentation`, `Automation`, `Analytics`, `AI`, `Shared`).
