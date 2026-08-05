# Mission Lifecycle States & Transition Matrix (`docs/MISSION_STATES.md`)

## Executive Summary

This document specifies the 9 canonical lifecycle states and transition validation rules for a **Mission** (`runtime.mission.states`).

---

## 1. Lifecycle State Machine Diagram

```text
       [RECEIVED]
           │
           v
        [PARSED]
           │
           v
       [RESOLVED]
           │
           v
       [VALIDATED]
           │
           v
        [PLANNED]
           │
           v
       [EXECUTING] ──────────────┬────────────────┐
           │                     │                │
           v                     v                v
      [COMPLETED]            [FAILED]        [CANCELLED]
    (Terminal State)     (Terminal State)  (Terminal State)
```

---

## 2. State Descriptions

| State | Name | Description | Active Operations |
|---|---|---|---|
| **1** | `RECEIVED` | Raw command received from CLI | Mission Intake parses parameters |
| **2** | `PARSED` | Command parsed into intent & requirements | Mission Resolution prepares context |
| **3** | `RESOLVED` | Workspace & project context resolved | Workspace discovery & project detection |
| **4** | `VALIDATED` | Constraints & policies validated | Governance policy evaluation |
| **5** | `PLANNED` | Step execution plan generated | Planning engine plan construction |
| **6** | `EXECUTING` | Handed off to Execution Runtime | Step invocation, telemetry, trace appends |
| **7** | `COMPLETED` | Execution completed successfully | Artifact routing, evidence flush, report generation |
| **8** | `FAILED` | Pipeline or execution failed | Error diagnostic logging, report generation |
| **9** | `CANCELLED` | User or policy cancelled mission | Partial evidence flush, lock release |

---

## 3. Allowed Transition Matrix

| Current State | Valid Target States |
|---|---|
| `RECEIVED` | `PARSED`, `FAILED`, `CANCELLED` |
| `PARSED` | `RESOLVED`, `FAILED`, `CANCELLED` |
| `RESOLVED` | `VALIDATED`, `FAILED`, `CANCELLED` |
| `VALIDATED` | `PLANNED`, `FAILED`, `CANCELLED` |
| `PLANNED` | `EXECUTING`, `FAILED`, `CANCELLED` |
| `EXECUTING` | `COMPLETED`, `FAILED`, `CANCELLED` |
| `COMPLETED` | *(None — Terminal State)* |
| `FAILED` | *(None — Terminal State)* |
| `CANCELLED` | *(None — Terminal State)* |

Validation logic is enforced programmatically via `runtime.mission.states.can_transition(current, target)`.
