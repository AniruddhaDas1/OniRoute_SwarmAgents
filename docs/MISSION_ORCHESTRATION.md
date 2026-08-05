# ACR-004 Phase O4: Mission Orchestration Architecture (`docs/MISSION_ORCHESTRATION.md`)

## Executive Summary

**Mission Orchestration** (`runtime.mission.orchestration.MissionOrchestrator`) is Phase O4 of the Mission Orchestrator architecture.

Mission Orchestration converts a `VALIDATED` Mission into a canonical, immutable `ExecutionRequest` object (`ORCHESTRATED` state).

It coordinates existing frozen framework components (`Planning Engine`, `Governance Layer`, `Workspace Runtime`, `UMAL`, `Invocation Layer`) by preparing their respective request payloads without executing them.

---

## 1. Pipeline Sequence

```text
  VALIDATED Mission (Resolution Phase O3)
       │
       ▼
  [1] Planning Preparation (PlanningRequest payload)
       │
       ▼
  [2] Governance Preparation (GovernanceRequest payload)
       │
       ▼
  [3] Workspace Preparation (Workspace Runtime directory map)
       │
       ▼
  [4] UMAL Preparation (ModelRequest payload)
       │
       ▼
  [5] Invocation Preparation (InvocationRequest payload)
       │
       ▼
  [6] ExecutionRequest Assembly (Immutable ExecutionRequest payload)
       │
       ▼
  ORCHESTRATED ExecutionRequest (ORCHESTRATED state)
```

---

## 2. Prepared Requests Breakdown

| Component | Responsible Engine / Model | Prepared Output Payload | Boundaries & Safeguards |
|---|---|---|---|
| **Planning Preparation** | `runtime.execution.engine` | `planning_request`: primary goal, intent, constraints, context snapshot, workspace root, priority, risk level | **NO** execution plans generated |
| **Governance Preparation** | `runtime.governance` | `governance_request`: permissions, policies, budgets, approvals, security context, risk metadata | **NO** policy evaluation performed |
| **Workspace Preparation** | `runtime.workspace` | `workspace_metadata` & execution directory paths for 16 canonical `.oniroute/` subdirectories | **NO** filesystem writes |
| **UMAL Preparation** | `runtime.models` | `umal_request`: capabilities required, provider constraints, local preference, provider independence flag | **NO** model selection performed |
| **Invocation Preparation** | `runtime.invocation` | `invocation_request`: streaming flag, tracing flag, event bus / trace callbacks | **NO** invocation executed |
| **ExecutionRequest** | `runtime.mission.models.ExecutionRequest` | Immutable `ExecutionRequest` encapsulating all prepared requests, metadata, and evidence | `execution_state: ORCHESTRATED`, `result: None` |

---

## 3. Strict Boundary Guarantees

Mission Orchestration strictly enforces:
- **No Execution**: Does not run workflows, steps, or processes.
- **No Plan Generation**: Does not generate step-by-step execution plans.
- **No Workflow Generation**: Does not construct new workflow specifications.
- **No Agent Selection**: Does not select or assign agents.
- **No Skill Selection**: Does not select or assign skills.
- **No Model Selection**: Does not pick LLM models or call UMAL select.
- **No AI Invocation**: Zero LLM API calls or model invocations.
- **Filesystem Read-Only Safety**: Prepares directory paths without making filesystem writes.
- **Provider Independence**: Preserves provider-neutral execution requests.

---

## 4. CLI Diagnostics & Commands

- Added `oniroute mission orchestrate [COMMAND]` to prepare and display the canonical `ExecutionRequest` and evidence in human-readable table or raw JSON format (`--json`) without executing.
- Natural-language commands submitted to `oniroute` (e.g. `oniroute Create a premium SaaS landing page`) automatically flow through Mission Intake → Mission Resolution → Mission Orchestration, producing the canonical `ExecutionRequest`.
