# Mission Control Architecture — Phase P6.D3

## Overview

Mission Control provides safe user interaction with running, paused, and completed
missions without modifying Runtime execution behavior. All operations consume
existing Runtime APIs (Session Storage, Trace Storage, History Storage,
ExecutionEventStream).

## Architecture

```
User CLI / API / VS Code Extension
         │
         ▼
┌──────────────────────────┐
│   MissionControlEngine   │
│                          │
│  • issue_command()       │
│  • inspect_mission()     │
│  • list_missions()       │
│  • recover_session()     │
│  • get_mission_logs()    │
│  • get_concurrent_registry() │
└────────┬─────────────────┘
         │ Consumes (read/write)
         ▼
┌──────────────────────────┐
│  Existing Runtime APIs   │
│                          │
│  • SessionStorage        │
│  • TraceStorage          │
│  • ExecutionHistoryStorage │
│  • ExecutionEventStream  │
└──────────────────────────┘
```

## Supported Actions

| Action | Description | Pre-condition |
|---|---|---|
| `PAUSE` | Suspends mission execution | Mission is RUNNING |
| `RESUME` | Resumes a paused mission | Mission is PAUSED |
| `CANCEL` | Terminates mission permanently | Mission is not COMPLETED/CANCELLED |
| `RETRY` | Re-queues a failed mission | Mission is FAILED or CANCELLED |
| `APPROVE_REVIEW` | Approves a waiting review | Review is pending |
| `REJECT_REVIEW` | Rejects a review with reason | Review is pending |
| `INSPECT` | Returns full mission inspection | Any state |

## Data Contracts

| Contract | Description |
|---|---|
| `MissionControlCommand` | Immutable command issued by user |
| `MissionControlResult` | Immutable result of command execution |
| `MissionInspection` | Full mission state snapshot |
| `MissionHistoryEntry` | Historical mission record for search |
| `ConcurrentMissionRegistry` | Active/paused/completed mission counts |

## Constraints

- **No Runtime changes**: Mission Control never modifies Runtime execution logic.
- **No planning changes**: No mission planning or assembly logic exists here.
- **No engineering changes**: No code generation or file modification.
- **Storage-only**: All state is persisted via existing storage APIs.
- **Trace-auditable**: Every command and result is persisted to TraceStorage.

## Module Layout

```
runtime/control/
├── __init__.py          # Package exports
├── models.py            # Immutable data contracts
└── engine.py            # MissionControlEngine
```
