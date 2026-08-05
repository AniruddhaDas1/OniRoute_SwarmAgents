# ACR-004 Phase O1: Mission Orchestrator Specification (`docs/MISSION_ORCHESTRATOR.md`)

## Executive Summary

The **Mission Orchestrator** is the high-level supervisor and single entry point connecting natural-language user commands from the OniRoute CLI to the underlying frozen runtime engines of the OniRoute framework (v1.0.0).

Under ACR-004 Phase O1, the Mission Orchestrator is established as an **ARCHITECTURE ONLY** layer. It does **NOT** replace any existing engine, does **NOT** alter execution contracts, and does **NOT** execute AI models directly. Instead, it translates natural-language commands (e.g. `oniroute Create a premium SaaS landing page`) into canonical, immutable **Missions** and orchestrates them across the already implemented, frozen framework layers.

```text
                               +----------------------------------+
                               |            OniRoute CLI          |
                               | (Natural Language Command Input) |
                               +----------------------------------+
                                                |
                                                v
                               +----------------------------------+
                               |        Mission Orchestrator      |
                               |    (Single Gateway & Director)   |
                               +----------------------------------+
                                                |
                                                v
    +---------------------------------------------------------------------------------------+
    |                               Frozen Engine Architecture                              |
    |                                                                                       |
    |  Workspace -> Context Engine -> ICOE -> Planning Engine -> Governance -> UMAL ->      |
    |  Invocation -> Execution Runtime                                                      |
    +---------------------------------------------------------------------------------------+
```

---

## 1. Primary Responsibilities

The Mission Orchestrator owns **only** orchestration logic. Its primary responsibilities include:

1. **Intent Understanding**: Accepting raw natural-language prompt strings from the CLI and normalizing them into structured mission requirements.
2. **Canonical Mission Construction**: Building immutable `Mission` objects encapsulating request parameters, requirements, constraints, context, and evidence tracking.
3. **Execution Context Collection**: Resolving target workspace root and project metadata using the frozen `WorkspaceResolver`.
4. **Engine Delegation**: Sequential handoff to the Context Engine, ICOE (Context Optimization), Planning Engine, Governance Policy Engine, UMAL (Model Selection), Invocation Engine, and Execution Runtime.
5. **Evidence Collection**: Recording immutable stage-by-stage evidence snapshots across all orchestration steps.
6. **Status Supervision & Reporting**: Maintaining mission state machine transitions and generating final execution reports.

---

## 2. Mission Director

The **Mission Director** (`runtime.mission.contracts.MissionDirectorContract`) is the core supervisor component within the Mission Orchestrator.

### Key Rules & Boundaries
- **Supervision Only**: The Mission Director supervises pipeline progression and handles engine delegations.
- **NEVER Executes AI Directly**: The Mission Director never invokes LLMs or executes code generation scripts directly; all invocation and execution must pass through the frozen `InvocationEngine` and `WorkflowEngine`.
- **Immutable Evidence**: Every decision made by the Mission Director or delegated engines is recorded in `MissionEvidence`.

---

## 3. CLI Command Contract

The Mission Orchestrator establishes natural-language CLI intake contracts for commands such as:

```bash
# Web application generation
oniroute Create a premium SaaS landing page

# Web site creation
oniroute Create portfolio website

# Backend service generation
oniroute Build REST API

# Code refactoring
oniroute Refactor authentication

# Bug fixing & diagnostics
oniroute Fix failing tests

# Repository analysis
oniroute Review this repository
```

These commands serve as inputs to the Mission Intake layer, which converts them into canonical `MissionRequest` objects for orchestration.
