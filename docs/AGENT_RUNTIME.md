# Agent Runtime Architecture (`docs/AGENT_RUNTIME.md`)

## Executive Summary

The **Agent Runtime** is the execution layer of OniRoute v1.0.0, implemented under Architecture Change Request 006 (**ACR-006**). It is the single layer authorized to create live agent sessions, track execution lifecycle, collect artifacts, and generate runtime reports.

The Agent Runtime consumes a sealed `ExecutionBlueprint` from the frozen Organization Builder (ACR-005) and is entirely responsible for execution. It must not modify the Mission, Workspace, or Organization architecture.

---

## 1. Core Responsibilities

| Responsibility | Description |
| :--- | :--- |
| **Session Creation** | Instantiate `AgentSession` records from Organization member definitions in the Blueprint |
| **Lifecycle Management** | Track and enforce deterministic state transitions across session lifecycle |
| **Event Recording** | Capture immutable `ExecutionEvent` records throughout session execution |
| **Artifact Collection** | Collect, register, and track `ArtifactRecord` lineage across sessions |
| **Execution Reporting** | Compile comprehensive `RuntimeReport` upon coordinator completion |

---

## 2. Canonical Pipeline

```text
ExecutionBlueprint (sealed, from ACR-005)
    │
    ▼
RuntimeInitializer ──► RuntimeContext
    │
    ▼
SessionManager ──► AgentSession[] (one per Organization Member)
    │
    ▼
ExecutionCoordinator
  ├── Dispatch sessions
  ├── Track lifecycle (INITIALIZED → READY → RUNNING → COMPLETED/FAILED)
  ├── Aggregate ExecutionEvents
  └── Collect ArtifactRecords
    │
    ▼
ArtifactCollector ──► ArtifactRecord[]
    │
    ▼
ExecutionReporter ──► RuntimeReport
    │
    ▼
Collaboration Layer (future: ACR-007)
```

---

## 3. Boundaries

The Agent Runtime is the **ONLY** layer authorized to execute work. All prior pipeline stages are frozen:

| Layer | Status | Runtime Access |
| :--- | :--- | :--- |
| Workspace Architecture | FROZEN | Read-only via WorkspaceRuntime |
| Mission Orchestrator | FROZEN | Consumed upstream only |
| Organization Builder | FROZEN | `ExecutionBlueprint` read-only |
| Agent Runtime | **ACTIVE** | Full execution authority |
