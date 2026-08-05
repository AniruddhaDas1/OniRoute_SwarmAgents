# Mission Recovery Reference — Phase P6.D3

## Overview

Mission Recovery enables OniRoute to recover from crashes, reboots, and unexpected
interruptions without losing execution state. All recovery state is read from
existing Session Storage and Trace Storage.

## Recovery Flow

```
Process Crash / Reboot / Network Failure
         │
         ▼
┌──────────────────────────────┐
│   MissionControlEngine       │
│   recover_session(session_id)│
└────────┬─────────────────────┘
         │
         ├─── Read SessionStorage manifest
         │    → Recover mission_id
         │
         ├─── Read TraceStorage events
         │    → Determine last known state
         │
         └─── Set recovered mission state
              → RUNNING / FAILED / COMPLETED
```

## Recovery Scenarios

### Scenario 1: Clean Crash During Execution

```
Last trace event: AGENT_STARTED
Recovered state: RUNNING
Action: Mission resumes from last checkpoint
```

### Scenario 2: Crash After Failure

```
Last trace event: MISSION_FAILED
Recovered state: FAILED
Action: User can issue "oniroute retry" to re-execute
```

### Scenario 3: Crash After Completion

```
Last trace event: MISSION_COMPLETED
Recovered state: COMPLETED
Action: No recovery needed, session already complete
```

## CLI Usage

```bash
# Recover the latest session
oniroute resume

# Check session state after reboot
oniroute status

# Retry a failed session
oniroute retry --mission msn-abc-123
```

## Concurrent Mission Recovery

When multiple missions were active during a crash, the recovery system:

1. Scans all session directories under `.oniroute/sessions/`
2. Reads each session's manifest and traces
3. Reconstructs the `ConcurrentMissionRegistry`
4. Reports all recovered missions via `oniroute status`

## Storage Dependencies

| Storage | Recovery Use |
|---|---|
| `SessionStorage` | Read session manifests for mission_id |
| `TraceStorage` | Read last event to determine state |
| `ExecutionHistoryStorage` | Read historical execution records |

## Constraints

- Recovery NEVER modifies Runtime execution logic
- Recovery NEVER replays LLM invocations
- Recovery reads ONLY from existing storage
- Recovery state is deterministic from stored traces
