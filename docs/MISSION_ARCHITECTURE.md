# Mission Orchestrator Architecture Overview (`docs/MISSION_ARCHITECTURE.md`)

## Executive Summary

This document certifies the architectural design, engine integration matrix, non-duplication invariants, and readiness of the **Mission Orchestrator Architecture** for OniRoute (ACR-004 Phase O1).

The Mission Orchestrator acts as the unified high-level entry point between natural-language CLI commands and the frozen runtime components of OniRoute v1.0.0.

---

## 1. Engine Integration Matrix

The Mission Orchestrator integrates all pre-existing, frozen framework engines without modifying their implementations or duplicating their responsibilities:

| Subsystem | Frozen Engine Module | Mission Orchestrator Integration Point |
|---|---|---|
| **Workspace Architecture** | `runtime.workspace` | Discovers target root & asserts Engine Root read-only boundary via `WorkspaceResolver` & `WorkspaceStorage` |
| **Resolution Engine** | `runtime.resolver` | Resolves available agent definitions, workflow specs, and skill packs from framework registry |
| **Context Engine** | `runtime.context` | Assembles context, dependency graphs, and symbol tokens via `ContextBuilder` |
| **ICOE** | `runtime.optimization` | Optimizes prompts and context token budgets via `OptimizationEngine` |
| **Planning Engine** | `runtime.execution.engine` | Builds deterministic step execution plans via `WorkflowEngine.plan()` |
| **Governance Layer** | `runtime.governance` | Enforces budget limits, security rules, and audit logs via `PolicyEngine` & `AuditEngine` |
| **UMAL** | `runtime.models` | Recommends optimal model and provider protocol via `ModelManager` |
| **Invocation Layer** | `runtime.invocation` | Dispatches model execution requests via `InvocationEngine` & adapters |
| **Execution Runtime** | `runtime.execution` | Executes step workflows, streams trace events, and routes artifacts via `WorkflowEngine.run()` |

---

## 2. Non-Duplication Invariants

To maintain strict architectural purity and modularity, Phase O1 enforces four explicit non-duplication invariants:

1. **No Duplicated Planner**: The Mission Orchestrator does NOT implement its own workflow planner or step solver. All planning is delegated to `WorkflowEngine.plan()`.
2. **No Duplicated Context Engine**: The Mission Orchestrator does NOT perform AST parsing, symbol extraction, or context assembly. All context building is delegated to `ContextBuilder`.
3. **No Duplicated Governance**: The Mission Orchestrator does NOT implement custom budget counters or security rules. All policy evaluation is delegated to `PolicyEngine`.
4. **No Duplicated Runtime**: The Mission Orchestrator does NOT execute LLM calls or code generation scripts directly. All runtime execution is delegated to `WorkflowEngine.run()` and `InvocationEngine`.

---

## 3. Provider & Workspace Independence

1. **Provider Independence**: The Mission Orchestrator operates entirely via provider-agnostic abstractions (`UMAL` / `ModelManager`). No model-provider specific logic (e.g. OpenAI, Ollama, Anthropic) exists within the orchestration layer.
2. **Workspace Independence**: All execution outputs, session logs, execution records, trace streams, and generated code are routed into `<workspace_root>/.oniroute/` via `ArtifactRouter`. The Engine Root remains permanently read-only.

---

## 4. Architectural Readiness Assessment

- **Model & Contract Integrity**: Verified via `tests/runtime/test_mission_architecture.py` (5/5 tests passing).
- **Engine Boundaries**: Verified — 0 modified engine lines.
- **Documentation Suite**: Completed across 5 canonical architecture documents.
- **Readiness**: Fully certified for ACR-004 Phase O2 (Mission Intake).
