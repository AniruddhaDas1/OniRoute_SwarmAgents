# Immutable Mission Models & Schemas (`docs/MISSION_MODELS.md`)

## Executive Summary

This document specifies the declarative data models and schemas for the **Mission Orchestrator** (`runtime.mission.models` and `runtime.mission.evidence`).

All Mission models are immutable Pydantic schemas. They contain **zero execution code** and serve purely as declarative contracts for data exchange across the orchestration pipeline.

---

## 1. Model Summary & References

| Model Name | Module | Primary Purpose |
|---|---|---|
| `Mission` | `runtime.mission.models` | Root canonical mission entity encapsulating all mission state |
| `MissionRequest` | `runtime.mission.models` | Raw natural-language command intake payload from CLI |
| `MissionRequirements` | `runtime.mission.models` | Parsed intent, functional requirements, & non-functional goals |
| `MissionConstraints` | `runtime.mission.models` | Operational constraints, budget limits, & security boundaries |
| `MissionDeliverables` | `runtime.mission.models` | Specified target deliverables & artifact categories |
| `MissionContext` | `runtime.mission.models` | Workspace & project context reference |
| `MissionEvidence` | `runtime.mission.evidence` | Immutable stage-by-stage audit evidence trail |
| `MissionStatus` | `runtime.mission.models` | Lifecycle state machine tracker & transition history |
| `MissionResult` | `runtime.mission.models` | Outcome payload generated upon mission termination |
| `MissionReport` | `runtime.mission.models` | Final consolidated human & machine-readable report |

---

## 2. Model Schemas

### 2.1 `MissionRequest`
```python
class MissionRequest(BaseModel):
    request_id: str
    raw_prompt: str
    explicit_workspace: Path | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    requested_at: str
```

### 2.2 `MissionRequirements`
```python
class MissionRequirements(BaseModel):
    intent_category: str  # "create", "refactor", "fix", "review"
    primary_goal: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    target_artifacts: list[str]
```

### 2.3 `MissionConstraints`
```python
class MissionConstraints(BaseModel):
    max_budget_usd: float | None = None
    timeout_seconds: int = 300
    allowed_providers: list[str] = Field(default_factory=list)
    local_only: bool = False
    require_human_approval: bool = False
```

### 2.4 `MissionDeliverables`
```python
class MissionDeliverables(BaseModel):
    expected_categories: list[str]
    target_paths: list[Path]
    output_summary: str = ""
```

### 2.5 `MissionContext`
```python
class MissionContext(BaseModel):
    workspace_id: str
    workspace_root: Path
    engine_root: Path
    project_type: str
    read_only_engine_confirmed: bool = True
```

### 2.6 `MissionEvidence`
```python
class MissionEvidence(BaseModel):
    workspace: dict[str, Any]
    project: dict[str, Any]
    requirements: dict[str, Any]
    constraints: dict[str, Any]
    context: dict[str, Any]
    optimization: dict[str, Any]
    planning: dict[str, Any]
    governance: dict[str, Any]
    model_selection: dict[str, Any]
    execution: dict[str, Any]
    artifacts: list[dict[str, Any]]
```

### 2.7 `Mission`
```python
class Mission(BaseModel):
    mission_id: str
    name: str
    request: MissionRequest
    requirements: MissionRequirements
    constraints: MissionConstraints
    deliverables: MissionDeliverables
    context: MissionContext
    evidence: MissionEvidence
    status: MissionStatus
    result: MissionResult | None = None
    report: MissionReport | None = None
```
