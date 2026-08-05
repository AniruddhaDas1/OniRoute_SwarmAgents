# Phase P4 — Project Assembly Architecture & Freeze Specification

## 1. Subsystem Overview

**Project Assembly (Phase P4)** is the foundation for autonomous codebase scaffolding, architectural blueprinting, implementation target allocation, and engineering contract generation in OniRoute v1.2.

```
RuntimeExecutionSnapshot
        │
        ▼
Workspace Scaffold (P4.G1) ──► WorkspaceScaffoldReport
        │
        ▼
Project Blueprint (P4.G2) ──► ProjectBlueprintReport
        │
        ▼
Implementation Allocation (P4.G3) ──► ImplementationAllocationReport
        │
        ▼
Engineering Contracts (P4.G4) ──► EngineeringContractReport
        │
        ▼
Project Assembly Freeze (P4.G5) ──► ProjectAssemblyCertificationReport
```

---

## 2. Core Governance Rules

1. **Zero LLM Invocations**: Phase P4 operates deterministically without calling LLM providers.
2. **Zero Code Generation**: Phase P4 generates contracts and scaffold manifests ONLY. Source code generation is deferred to Phase P5.
3. **Immutable Data Contracts**: All report outputs (`WorkspaceScaffoldReport`, `ProjectBlueprintReport`, `ImplementationAllocationReport`, `EngineeringContractReport`, `ProjectAssemblyCertificationReport`) enforce Pydantic immutability (`model_config = ConfigDict(frozen=True)`).
4. **Engine Root Read-Only Safety**: Engine root is protected against edits during assembly via `assert_no_engine_write`.
5. **Strict Pipeline Boundaries**: Every pipeline stage consumes ONLY its explicit upstream report contract.

---

## 3. Subsystem Phases

- **P4.G1 Workspace Scaffold**: Creates workspace directory trees, `.oniroute/` runtime folders, and environment manifests.
- **P4.G2 Project Blueprint**: Defines module allocations, directory ownership, and expected files across 11 engineering disciplines.
- **P4.G3 Implementation Allocation**: Maps every implementation target to an Agent Profile ID, discipline, and priority.
- **P4.G4 Engineering Contracts**: Generates execution-ready engineering contract specifications incorporating 10 rule suites.
- **P4.G5 Assembly Certification & Freeze**: Certifies and freezes the complete P4 pipeline.
