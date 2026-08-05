# Phase P4.G4 — Engineering Contracts Specification

## 1. Subsystem Overview

Phase P4.G4 (**Engineering Contracts**) is the fourth stage of Phase 4 (Workspace Scaffolding & Code Generation Foundation) in OniRoute v1.2.

```
ImplementationAllocationReport (P4.G3) ──► Engineering Contract Engine (P4.G4) ──► EngineeringContractReport ──► Project Assembly Freeze (P4.G5)
```

The Engineering Contract Engine processes an immutable [`ImplementationAllocationReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/allocation/models.py#L31) to deterministically generate execution-ready [`EngineeringContract`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/contracts/models.py#L9) specs for every allocated target file, directory, and module.

It operates **strictly without**:
- Invoking LLMs or AI providers
- Writing source code implementations
- Executing build pipelines
- Modifying engine root files (Engine Root is permanently read-only)

---

## 2. Mandatory Existing Component Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| [`ImplementationAllocationReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/allocation/models.py#L31) | Sole input contract for target paths, agent ownership, and dependencies | Consumed in `EngineeringContractEngine.generate_contracts` |
| [`ProjectBlueprintReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/blueprint/models.py#L31) | Reused via allocation references for module specs | Preserved unchanged |
| [`WorkspaceScaffoldReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/scaffold/models.py#L9) | Reused via blueprint references for directory layout | Preserved unchanged |
| [`AgentProfileReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L187) | Reused profile definitions for agent assignment | Mapped to assigned profile IDs |
| [`EngineeringExecutionPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/plan.py#L34) | Reused plan strategy for architecture constraints | Preserved unchanged |
| [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) | Reused deployment wave mapping strategy | Mapped to contract execution waves (1-6) |
| [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L135) | Reused snapshot references | Preserved unchanged |

---

## 3. Engineering Contract Specification

Each [`EngineeringContract`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/contracts/models.py#L9) defines:

1. **Target Identification**: Target path, target type, contract ID.
2. **Agent Assignment**: Assigned Agent Profile ID and Role Title.
3. **Discipline & Priority**: Engineering discipline and implementation priority (`P0_CRITICAL` through `P3_LOW`).
4. **Execution Wave**: Wave assignment (Waves 1 to 6).
5. **Dependencies & Artifacts**: Input contract dependencies and expected output artifact paths.
6. **Rule & Constraint Suites**:
   - Interface Constraints (export symbols, protocols)
   - Architecture Constraints (provider independence, read-only engine safety, modularity)
   - Coding Standards (PEP8 / ESLint / Prettier formatting rules)
   - Naming Rules (PascalCase, snake_case, UPPER_SNAKE_CASE)
   - Security Requirements (input validation, path safety, no secrets)
   - Performance Expectations (latency, memory bounds)
   - Testing Requirements (automated unit tests)
   - Documentation Requirements (docstrings, type hints, READMEs)
   - Acceptance Criteria (verification metrics)
   - Review Requirements (peer review and approval gates)

---

## 4. CLI Reference

```bash
# Generate engineering contracts for current workspace
oniroute contracts

# Output raw JSON EngineeringContractReport
oniroute contracts --json

# Run with explicit ImplementationAllocationReport JSON file
oniroute contracts --allocation /path/to/allocation_report.json
```

---

## 5. Verification & Integrity

The contract engine validates 100% allocation coverage, zero orphan contracts, zero duplicate contracts, constraint completeness across all 10 rule suites, acceptance criteria completeness, and returns a frozen Pydantic [`EngineeringContractReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/contracts/models.py#L35).
