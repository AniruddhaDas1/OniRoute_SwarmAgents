# Canonical Mission Orchestration Pipeline (`docs/MISSION_PIPELINE.md`)

## Executive Summary

This document specifies the canonical 10-stage execution pipeline managed by the **Mission Orchestrator**.

Each stage delegates work to an existing, frozen framework engine. The Mission Orchestrator does not replace any engine, nor does it duplicate planning, context building, governance, or invocation logic.

---

## 1. Canonical Pipeline Sequence

```text
  [1] CLI Command
       │
       ▼
  [2] Mission Intake
       │
       ▼
  [3] Workspace Discovery (existing: WorkspaceResolver)
       │
       ▼
  [4] Mission Resolution (Mission Director)
       │
       ▼
  [5] Context Engine (existing: ContextBuilder)
       │
       ▼
  [6] ICOE (existing: OptimizationEngine)
       │
       ▼
  [7] Planning Engine (existing: WorkflowEngine.plan)
       │
       ▼
  [8] Governance (existing: PolicyEngine & AuditEngine)
       │
       ▼
  [9] UMAL (existing: ModelManager)
       │
       ▼
  [10] Invocation & Execution Runtime (existing: InvocationEngine & WorkflowEngine.run)
```

---

## 2. Stage Breakdown & Engine Delegations

| Stage | Name | Responsible Module / Engine | Delegated Behavior & Evidence Recorded |
|---|---|---|---|
| **1** | `CLI Command` | CLI (`cli.main`) | Natural-language prompt submitted by user |
| **2** | `Mission Intake` | Mission Intake (Phase O2) | Parses prompt into `MissionRequest` (`RECEIVED` state) |
| **3** | `Workspace Discovery` | `runtime.workspace.discovery` | Discovers target workspace root & project type (`WorkspaceMetadata`) |
| **4** | `Mission Resolution` | `MissionDirector` | Normalizes intent, constraints, requirements into `Mission` (`RESOLVED` state) |
| **5** | `Context Engine` | `runtime.context.builder` | Assembles workflow context & dependency maps |
| **6** | `ICOE` | `runtime.optimization` | Optimizes prompt & context tokens against budget limits |
| **7** | `Planning Engine` | `runtime.execution.engine` | Builds deterministic step execution plan (`PLANNED` state) |
| **8** | `Governance` | `runtime.governance` | Evaluates permission policies, budgets, and security compliance |
| **9** | `UMAL` | `runtime.models` | Selects optimal LLM model & provider protocol |
| **10** | `Invocation & Runtime` | `runtime.invocation` / `execution` | Executes plan, records trace events, routes artifacts via `ArtifactRouter` |

---

## 3. Immutable Evidence Recording Across Pipeline

At every stage transition, the `MissionDirector` calls `MissionEvidence.record_stage(stage_name, data)` to record an immutable evidence record:

- **Workspace Stage**: Workspace root path, project type, discovery priority level, validation status.
- **Project Stage**: Manifest path, framework version, language version.
- **Requirements Stage**: Functional requirements, non-functional requirements, target deliverable types.
- **Constraints Stage**: Budget limits, timeout limits, local-only flag.
- **Context Stage**: Context snapshot ID, estimated byte size, symbol count.
- **Optimization Stage**: Token budget, compression ratio, protected symbols list.
- **Planning Stage**: Plan ID, step count, agent/skill assignments.
- **Governance Stage**: Policy outcome (`PASS`/`BLOCK`), budget snapshot, audit ID.
- **Model Selection Stage**: Selected model ID, provider name, protocol type.
- **Execution Stage**: Execution ID, runtime duration, status.
- **Artifacts Stage**: Array of created artifact records routed via `ArtifactRouter`.
