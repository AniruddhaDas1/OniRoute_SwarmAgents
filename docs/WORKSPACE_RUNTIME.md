# Workspace Runtime Integration Specification (`docs/WORKSPACE_RUNTIME.md`)

## Executive Summary

This document specifies the integration of the **Workspace Architecture** into the **OniRoute Execution Engine** (`WorkflowEngine`, `GovernanceEngine`, `OptimizationEngine`).

Phase W4 and Phase W5 certify that every runtime process operates under an immutable `ExecutionContext` containing both `engine_root` and `workspace_root`. All execution persistence — history, traces, sessions, reports, logs, and generated artifacts — is strictly routed into the User Workspace, while the Engine Root remains untouched.

---

## 1. Runtime Integration Lifecycle

```text
1. Initialization:
   CLI / API invocation
       │
       ▼
   WorkspaceManager.create_context(cwd, explicit_workspace)
       │
       ▼
   WorkspaceResolver.resolve_workspace() ──► ProjectDetector & WorkspaceValidator
       │
       ▼
   ExecutionContext Created (Engine Root Read-Only Confirmed)

2. Execution Pipeline:
   WorkflowEngine(registry, workspace_metadata=ctx.workspace_metadata)
       │
       ├─► Plan Execution ──────────► WorkspaceStorage.ensure_dir("plans")
       ├─► Execute Steps ──────────► ArtifactRouter.route_artifact() ──► .oniroute/generated/
       ├─► Trace Events ───────────► TraceStorage.append_trace()    ──► .oniroute/traces/
       ├─► Session Snapshots ──────► SessionStorage.persist()        ──► .oniroute/sessions/
       └─► Governance & Audit ─────► ReportStorage.persist()         ──► .oniroute/reports/

3. Shutdown & Persistence:
   Execution History Written ──► ExecutionHistoryStorage.persist() ──► .oniroute/history/
   Locks Released & State Flushed
```

---

## 2. Component Integration Details

### 2.1 Execution History Persistence (`ExecutionHistoryStorage`)
- **Module**: `runtime.workspace.history_storage`
- **Behavior**: When a workflow execution completes or fails, `WorkflowEngine` formats the execution summary (execution ID, workflow ID, status, step summaries, timestamps) and calls `ExecutionHistoryStorage.persist(execution_id, record)`.
- **Target File**: `.oniroute/history/<execution_id>.json`
- **Safety**: Passed through `assert_no_engine_write()`.

### 2.2 Trace Persistence (`TraceStorage`)
- **Module**: `runtime.workspace.trace_storage`
- **Behavior**: As steps execute, runtime events (`step_started`, `step_completed`, `tool_invoked`, `error_emitted`) are streamed into `TraceStorage.append_trace(execution_id, events)`.
- **Target File**: `.oniroute/traces/<execution_id>.jsonl`
- **Format**: JSON Lines format (1 line per event).

### 2.3 Session Persistence (`SessionStorage`)
- **Module**: `runtime.workspace.session_storage`
- **Behavior**: Multi-step workflows and interactive CLI sessions record their active state, conversation context, and execution variables using `SessionStorage.persist_session(session_metadata)`.
- **Target File**: `.oniroute/sessions/<session_id>.yaml`

### 2.4 Report Persistence (`ReportStorage`)
- **Module**: `runtime.workspace.report_storage`
- **Behavior**: Optimization runs and governance policy audits record structured metrics and traces via `ReportStorage.save_report(report_type, execution_id, data)`.
- **Target File**: `.oniroute/reports/<report_type>/<execution_id>.json`

### 2.5 Artifact Routing (`ArtifactRouter`)
- **Module**: `runtime.workspace.artifact_router`
- **Behavior**: All code generation, documentation, presentation, or report creation tools invoke `ArtifactRouter.route_artifact(context, category, filename)` to resolve an absolute destination path.
- **Boundary Verification**: Asserts $\text{Path}_{\text{destination}} \subseteq \text{Workspace Root} \land \text{Path}_{\text{destination}} \nsubseteq \text{Engine Root}$.

---

## 3. Multiple Executions & Restart Behavior

1. **State Isolation**: Each execution receives a unique `execution_id`. History files, trace files, and report logs use `execution_id` as their primary filename key, preventing overwrite collisions across concurrent or sequential runs.
2. **Restart Behavior**: When `oniroute` is invoked repeatedly in the same directory, `WorkspaceResolver` detects the existing `.oniroute/` marker, reloads `workspace.yaml`, and appends new execution history/traces without destroying previous state.
3. **Workspace Consistency**: All metadata operations are atomic file writes. Incomplete writes do not corrupt existing execution records.
4. **Engine Isolation**: Throughout multiple executions, zero writes touch the Engine Root.

---

## 4. Verification Code Example

```python
from pathlib import Path
from runtime.loader import RepositoryLoader
from runtime.execution.engine import WorkflowEngine
from runtime.workspace import WorkspaceManager

# 1. Resolve workspace context
manager = WorkspaceManager()
ctx = manager.create_context(cwd=Path.cwd())
assert ctx.is_engine_read_only()

# 2. Instantiate workflow engine with workspace metadata
registry = RepositoryLoader(ctx.engine_root).load()
engine = WorkflowEngine(registry, workspace_metadata=ctx.workspace_metadata)

# 3. Run workflow
result = engine.run("sample_workflow")

# 4. Confirm persistence inside workspace
assert (ctx.workspace_root / ".oniroute" / "history" / f"{result.execution_id}.json").exists()
assert (ctx.workspace_root / ".oniroute" / "traces" / f"{result.execution_id}.jsonl").exists()
```
