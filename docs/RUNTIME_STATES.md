# Runtime State Machine Specification (`docs/RUNTIME_STATES.md`)

## Executive Summary

The **Agent Runtime State Machine** defines the canonical lifecycle of an `AgentSession`. It is a deterministic Directed Acyclic Graph (DAG) of state transitions enforced by the `can_runtime_transition` guard function in `runtime.agent.models`.

---

## 1. State Machine Diagram

```text
              INITIALIZED
                   │
                   ▼
                READY ─────────────────────────► CANCELLED
                   │
                   ▼
              ┌─ RUNNING ──────────────────────► FAILED
              │    │
              │    ├──► WAITING ──► RUNNING (retry)
              │    │         └────────────────► CANCELLED / FAILED
              │    └──► REVIEW ──► RUNNING (approved)
              │              └──────────────► FAILED
              └──────────────────────────────► COMPLETED
```

---

## 2. State Definitions

| State | Description |
| :--- | :--- |
| `INITIALIZED` | Session record created, not yet ready for execution |
| `READY` | Session has been validated and is prepared to start |
| `RUNNING` | Active execution in progress |
| `WAITING` | Blocking on a dependency or resource |
| `REVIEW` | Artifact or output submitted for review gate |
| `COMPLETED` | Successful execution; terminal state |
| `FAILED` | Unrecoverable error; terminal state |
| `CANCELLED` | Explicitly halted by governance or coordinator; terminal state |

---

## 3. Transition Guard

```python
from runtime.agent import can_runtime_transition, RuntimeState

# Allowed
can_runtime_transition(RuntimeState.READY, RuntimeState.RUNNING)     # True
can_runtime_transition(RuntimeState.RUNNING, RuntimeState.COMPLETED) # True

# Blocked — no backward transitions
can_runtime_transition(RuntimeState.COMPLETED, RuntimeState.RUNNING) # False
```
