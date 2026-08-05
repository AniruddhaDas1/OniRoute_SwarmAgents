# OniRoute Mission Orchestrator Developer Guide (`docs/MISSION_DEVELOPER_GUIDE.md`)

## Overview

This guide explains how to programmatically consume the **Mission Orchestrator** package (`runtime.mission`) in Python code.

---

## 1. Package Architecture & Core Components

```python
from runtime.mission import (
    MissionIntake,
    MissionResolver,
    MissionOrchestrator,
    MissionDirector,
    MissionRequest,
    Mission,
    ExecutionRequest,
    MissionState,
)
```

---

## 2. Programmatic Pipeline Execution

```python
from pathlib import Path
from runtime.mission import MissionDirector, MissionIntake

# Step 1: Mission Intake
intake = MissionIntake()
mission_request = intake.process_intake(
    raw_prompt="Build a SaaS billing dashboard",
    explicit_workspace=Path.cwd(),
    parameters={"priority": "high", "local_only": True},
)

# Step 2: Mission Director Supervision (Resolution + Orchestration)
director = MissionDirector()
resolved_mission = director.receive_mission(mission_request)
assert resolved_mission.status.current_state == MissionState.VALIDATED

# Step 3: Mission Orchestration
execution_request = director.orchestrate_mission(resolved_mission)
assert execution_request.execution_state == MissionState.ORCHESTRATED
assert execution_request.mission.result is None  # Read-only, zero execution
```

---

## 3. Accessing Prepared Request Payloads

```python
# Inspect prepared planning payload
planning_payload = execution_request.planning_request
print("Primary Goal:", planning_payload["primary_goal"])
print("Priority:", planning_payload["priority"])

# Inspect prepared governance payload
governance_payload = execution_request.governance_request
print("Permissions Requested:", governance_payload["permissions"])

# Inspect prepared UMAL payload
umal_payload = execution_request.umal_request
print("Local Preference:", umal_payload["constraints"]["local_only"])

# Inspect immutable evidence audit trail
evidence = execution_request.execution_evidence
print("Recorded Evidence Stages:", list(evidence.model_dump().keys()))
```

---

## 4. Extension Rules for Downstream ACRs (e.g. ACR-005 Swarm Orchestrator)

1. **Treat `runtime.mission` as Read-Only**: Downstream engines must consume `ExecutionRequest` without altering `MissionOrchestrator` or `MissionResolver`.
2. **Preserve Lifecycle States**: Respect `MissionState.ORCHESTRATED` as the entry state for Swarm assembly.
3. **Immutability Guarantee**: Always update evidence using `evidence.record_stage(...)` which returns a new immutable instance.
