# Agent Runtime Architecture Reference (`docs/RUNTIME_ARCHITECTURE.md`)

## Executive Summary

This document provides the complete architectural reference for the OniRoute **Agent Runtime** (`runtime.agent`) introduced in ACR-006.

---

## 1. Package Structure

```text
runtime/agent/
├── __init__.py          # Package exports
├── models.py            # Immutable runtime models (AgentSession, events, artifacts, reports)
└── contracts.py         # ABC interface contracts for all runtime components
```

---

## 2. Canonical Data Flow

```text
[ExecutionBlueprint]  ──────────────────────────────────────────────┐
        │                                                            │
        ▼                                                            │
RuntimeInitializer ──► RuntimeContext                               │
        │                                                            │
        ▼                                                            │
SessionManager ──► [AgentSession × N] (N = |Organization.members|) │
        │                                                            │
        ▼                                                            │
ExecutionCoordinator                                                 │
  ├── session.state: INITIALIZED → READY → RUNNING                  │
  ├── ArtifactCollector ──► ArtifactRecord[]                        │
  ├── EventRecorder ──► ExecutionEvent[]                            │
  └── session.state: RUNNING → COMPLETED / FAILED                   │
        │                                                            │
        ▼                                                            │
ExecutionReporter ──► RuntimeReport                                  │
        │                                                            │
        ▼                                                            │
Collaboration Layer (future ACR-007)  ◄──────────────────────────────┘
```

---

## 3. Engine Integration Map

The Agent Runtime integrates with existing frozen engines as consumers only:

| Engine | Consumption Mode |
| :--- | :--- |
| `ExecutionBlueprint` (ACR-005) | Read-only contract input |
| Workspace Runtime | Read-only workspace discovery |
| Invocation Layer | Trigger agent skill invocations |
| UMAL | User model permission enforcement |
| Governance Engine | Policy and constraint evaluation |
| Artifact Router | Output artifact routing |
| History Engine | Execution trace persistence |

---

## 4. Contracts Summary

| Contract | Methods |
| :--- | :--- |
| `RuntimeInitializerContract` | `initialize_runtime(blueprint) → RuntimeContext` |
| `SessionManagerContract` | `create_session`, `transition_state`, `terminate_session` |
| `ExecutionCoordinatorContract` | `instantiate_sessions`, `collect_results`, `generate_report` |
| `ArtifactCollectorContract` | `register_artifact`, `get_artifacts` |
| `EventRecorderContract` | `record_event`, `get_events` |
| `ExecutionReporterContract` | `compile_report` |

---

## 5. Strict Architecture Boundaries

The Agent Runtime must:

- **NEVER** modify `runtime.mission`, `runtime.organization`, or `runtime.workspace`.
- **NEVER** call LLM APIs or AI inference services directly.
- **NEVER** schedule or dispatch background tasks or cron jobs.
- **ALWAYS** consume the `ExecutionBlueprint` as a read-only sealed contract.
- **ALWAYS** emit `ExecutionEvent` records for every state transition.
