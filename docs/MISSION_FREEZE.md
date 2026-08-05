# ACR-004 Mission Orchestrator Freeze Specification (`docs/MISSION_FREEZE.md`)

## Executive Summary

Effective upon completion of **ACR-004 Phase O5**, the **Mission Orchestrator** package (`runtime.mission`) is formally **FROZEN**.

No future Architecture Change Request (ACR) may alter the contracts, state machine transitions, model schemas, or execution boundaries of the Mission Orchestrator, with the sole exception of critical bug fixes.

---

## 1. Frozen Components Scope

The following modules and interfaces are strictly frozen under version 1.0.0:

1. **Mission Intake** (`runtime.mission.intake.MissionIntake`, `MissionNormalizer`)
2. **Mission Resolution** (`runtime.mission.resolution.MissionResolver`)
3. **Mission Orchestration** (`runtime.mission.orchestration.MissionOrchestrator`)
4. **Mission Models** (`runtime.mission.models`: `MissionRequest`, `Mission`, `MissionContext`, `MissionConstraints`, `MissionRequirements`, `MissionDeliverables`, `MissionStatus`, `MissionReport`, `ExecutionRequest`)
5. **Mission States** (`runtime.mission.states.MissionState`, `ALLOWED_STATE_TRANSITIONS`, `can_transition`)
6. **Mission Director** (`runtime.mission.director.MissionDirector`)
7. **Mission Contracts** (`runtime.mission.contracts`: `MissionDirectorContract`, `MissionIntakeContract`, `MissionResolverContract`, `MissionOrchestratorContract`, `MissionPipelineContract`)
8. **Mission Evidence** (`runtime.mission.evidence.MissionEvidence`)
9. **Mission Exceptions** (`runtime.mission.exceptions`)

---

## 2. Freeze Rules & Governance

- **Rule F-1 (Contract Immutability)**: Abstract contract methods in `contracts.py` must not be renamed, reordered, or removed.
- **Rule F-2 (State Machine Enforcement)**: Allowed lifecycle transitions in `states.py` (`RECEIVED` → `PARSED` → `RESOLVED` → `VALIDATED` → `ORCHESTRATED`) are locked.
- **Rule F-3 (No Runtime Side-Effects)**: Mission Intake, Resolution, and Orchestration must remain strictly read-only and non-evaluative.
- **Rule F-4 (Provider Independence)**: Neutral model, governance, and planning payloads must be preserved.
- **Rule F-5 (Downstream Consumption)**: ACR-005 (Swarm Orchestrator) and future ACRs must consume the frozen `ExecutionRequest` without mutating `runtime.mission`.
