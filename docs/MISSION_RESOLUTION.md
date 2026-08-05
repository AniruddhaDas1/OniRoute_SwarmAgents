# ACR-004 Phase O3: Mission Resolution Architecture (`docs/MISSION_RESOLUTION.md`)

## Executive Summary

**Mission Resolution** (`runtime.mission.resolution.MissionResolver`) is Phase O3 of the Mission Orchestrator architecture.

Mission Resolution transforms a canonical `MissionRequest` into a fully validated, immutable `Mission` object (`VALIDATED` state).

It orchestrates existing, frozen framework engines sequentially without introducing planning, workflow generation, agent selection, skill selection, model selection, or execution logic of its own.

---

## 1. Pipeline Sequence

```text
  MissionRequest (Intake Phase O2)
       │
       ▼
  [1] Workspace Analysis (WorkspaceManager & WorkspaceContext)
       │
       ▼
  [2] Project Analysis (ProjectDetector & ProjectMetadata)
       │
       ▼
  [3] Repository Analysis (RepositoryLoader & Resolver)
       │
       ▼
  [4] Context Resolution (ContextBuilder & OptimizationEngine ICOE)
       │
       ▼
  [5] Knowledge Resolution (Knowledge Sources, Packages, Mappings)
       │
       ▼
  [6] Constraint Resolution (Operational & Policy Constraints)
       │
       ▼
  [7] Mission Validation (State machine progression & contracts)
       │
       ▼
  Validated Mission (RESOLVED / VALIDATED state)
```

---

## 2. Stage Breakdown & Framework Engine Integration

| Stage | Responsible Module / Engine | Collected Data & Evidence Recorded | Boundaries & Constraints |
|---|---|---|---|
| **Workspace Analysis** | `runtime.workspace.WorkspaceManager` | Workspace root, Engine root, Project type, Workspace metadata snapshot, Git repository presence, Read-only safety confirmation | No file modifications |
| **Project Analysis** | `runtime.workspace.project.ProjectDetector` | Primary language, Framework, Build system, Package manager, Repository layout, Manifest path & versions | No build tool execution |
| **Repository Analysis** | `runtime.loader.RepositoryLoader` & `runtime.resolver.Resolver` | Symbol count, Configuration files, Documentation files, Workspace storage existence | No planning |
| **Context Resolution** | `runtime.context.builder.ContextBuilder` & `runtime.optimization.OptimizationEngine` | Canonical context snapshot, ICOE token optimization report & measurements | Frozen ICOE optimization algorithms |
| **Knowledge Resolution** | `runtime.loader.RepositoryLoader` | Knowledge sources, Packages, Mappings, Repository/community/official metadata | **NO** Skill or Agent selection |
| **Constraint Resolution** | `runtime.mission.models.MissionConstraints` | Workspace boundaries, Technology constraints, User budget/timeouts/providers/local-only settings | Metadata determination only |
| **Mission Validation** | `runtime.mission.resolution.MissionResolver` | Immutable `Mission`, requirements, deliverables, status transitions (`RECEIVED` → `PARSED` → `RESOLVED` → `VALIDATED`), `MissionReport` | **NO** execution fields |

---

## 3. Guarantees & Boundaries

Mission Resolution strictly enforces the following architectural boundaries:
- **No Planning**: Does not generate execution plans or steps.
- **No Workflow Generation**: Does not construct workflow definitions.
- **No Agent Selection**: Does not select or bind agents.
- **No Skill Selection**: Does not select or bind skills.
- **No Swarm Execution**: Does not invoke swarm agents.
- **No Model Selection**: Does not invoke UMAL or select LLM models.
- **No AI Invocation**: Zero LLM API calls or AI execution.
- **Provider Independence**: Preserves provider-neutral interfaces.
- **Workspace Boundaries**: All storage reads pass through frozen workspace APIs; read-only engine safety confirmed.

---

## 4. CLI Handoff

- Natural-language commands submitted to `oniroute` (e.g. `oniroute Create a premium SaaS landing page`) automatically flow through Mission Intake and Mission Resolution, returning the validated `Mission` payload.
- Added `oniroute mission [PROMPT]` command to inspect resolved missions in table format or raw JSON (`--json`) without planning or execution.
