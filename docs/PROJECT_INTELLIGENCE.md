# OniRoute Project Intelligence Subsystem (v1.2)

## 1. Overview
The **Project Intelligence Subsystem** is the foundational Phase 1 engine of OniRoute v1.2. It converts arbitrary user natural language requests and local workspace environments into a single, canonical, declarative **Engineering Execution Plan** before any mission execution, organization assembly, or agent orchestration begins.

The subsystem is **100% deterministic**, **provider-independent**, **rule-based**, and consumes **0 LLM tokens**.

---

## 2. Architecture & Design Principles

```
                              [ User Request ]
                                     │
                                     ▼
                       ┌───────────────────────────┐
                       │   Intent Analysis Engine  │
                       │          (P1.I1)          │
                       └─────────────┬─────────────┘
                                     │ IntentReport
                                     ▼
                       ┌───────────────────────────┐
                       │   Workspace Intelligence  │
                       │          (P1.I2)          │
                       └─────────────┬─────────────┘
                                     │ WorkspaceContext
                                     ▼
                       ┌───────────────────────────┐
                       │  Repository Intelligence  │
                       │          (P1.I3)          │
                       └─────────────┬─────────────┘
                                     │ RepositoryContext
                                     ▼
                       ┌───────────────────────────┐
                       │ Engineering Execution Plan│
                       │          (P1.I4)          │
                       └─────────────┬─────────────┘
                                     │ EngineeringExecutionPlan
                                     ▼
                       ┌───────────────────────────┐
                       │       Mission Intake      │
                       └───────────────────────────┘
```

### Core Principles
1. **Strict Context Chaining**: Each phase consumes the immutable output of the previous phase.
2. **Zero Code Generation & Execution**: Understands *what exists* and *what is requested* without executing compilers, runtime scripts, or parsing ASTs.
3. **Engine Safety Boundary**: Enforces read-only safety on the OniRoute Engine Root (`PROTECTED_ENGINE_TARGETS`).
4. **Immutability**: All context data structures are implemented using Pydantic `frozen=True` models.
5. **Deterministic Pipeline**: Identical inputs yield byte-for-byte identical context objects across all execution environments.

---

## 3. Context Model Specifications

| Context Model | Module | Primary Purpose | Key Fields |
|---|---|---|---|
| `IntentReport` | `runtime/intent/models.py` | Intent analysis output | `primary_intent`, `project_category`, `detected_technologies`, `confidence_score` |
| `WorkspaceContext` | `runtime/workspace/intelligence.py` | Workspace intelligence output | `workspace_root`, `workspace_state`, `project_type`, `build_tool`, `package_manager` |
| `RepositoryContext` | `runtime/workspace/repository.py` | Structural repository output | `directory_topology`, `detected_roots`, `entry_points`, `test_presence`, `repository_size` |
| `EngineeringExecutionPlan` | `runtime/workspace/plan.py` | Consolidated execution blueprint | `plan_id`, `repository_strategy`, `required_disciplines`, `required_deliverables`, `high_level_milestones` |

---

## 4. Subsystem Governance & Constraints
- **Architecture Integrity**: Reuses existing Core v1.1 Mission, Workspace, Runtime, and Organization layers.
- **Provider Independence**: No vendor-specific SDKs embedded inside context engines.
- **Subsystem Freeze**: Certified and frozen in Phase P1.I5. No functional changes permitted post-freeze except bug fixes.
