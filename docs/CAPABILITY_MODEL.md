# Capability Model Architecture (`docs/CAPABILITY_MODEL.md`)

## Executive Summary

The **Capability Model** establishes immutable, declarative schemas for analyzing, categorizing, prioritizing, and constraining engineering capabilities required to execute a mission.

Under ACR-005 Phase S1, the Capability Model is strictly an **ARCHITECTURE ONLY** definition. It introduces immutable Pydantic models for capability tracking without implementing resolution logic, agent selection, or AI model execution.

---

## 1. Capability Model Taxonomy

The Capability Model comprises seven core immutable schemas implemented in `runtime.organization.capability`:

```text
+-------------------------------------------------------------------------------+
|                               CapabilityReport                                |
|  +-------------------------------------------------------------------------+  |
|  |  Requirement 1 (CapabilityRequirement)                                   |  |
|  |    -> Capability (Capability)                                            |  |
|  |        -> Priority (CapabilityPriority: CRITICAL/HIGH/MEDIUM/etc.)       |  |
|  |        -> Constraints (list[CapabilityConstraint])                       |  |
|  |  +-------------------------------------------------------------------+  |  |
|  |  |  CapabilityGroup (grp-web-fullstack)                              |  |  |
|  |  |    -> [ cap-frontend-react, cap-backend-fastapi, cap-db-postgres ]|  |  |
|  |  +-------------------------------------------------------------------+  |  |
|  |  Evidence (CapabilityEvidence)                                           |  |
|  +-------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------+
```

---

## 2. Core Model Definitions

### `Capability`
Represents a discrete engineering domain or technical capability (e.g. `cap-backend-fastapi`).

```python
class Capability(BaseModel):
    capability_id: str
    name: str
    domain: str
    description: str
    version: str = "1.0.0"
    required_skills: list[str] = []
    required_knowledge: list[str] = []
    required_packages: list[str] = []
    metadata: dict[str, Any] = {}
```

### `CapabilityGroup`
Logical grouping of related engineering capabilities that form a coherent sub-system domain (e.g. `grp-web-fullstack`).

```python
class CapabilityGroup(BaseModel):
    group_id: str
    name: str
    domain: str
    description: str
    capabilities: list[Capability] = []
    metadata: dict[str, Any] = {}
```

### `CapabilityPriority`
Enum establishing clear priority rankings for capability fulfillment:

- `CRITICAL`: Required for fundamental mission viability; mission cannot proceed without it.
- `HIGH`: Major feature requirement; failure impacts core deliverables.
- `MEDIUM`: Standard functional or non-functional requirement.
- `LOW`: Secondary enhancement or optional documentation detail.
- `OPTIONAL`: Good-to-have capability if budget and execution time allow.

### `CapabilityConstraint`
Operational, security, and resource boundaries restricting capability execution.

```python
class CapabilityConstraint(BaseModel):
    constraint_id: str
    capability_id: str
    local_only: bool = False
    allowed_providers: list[str] = []
    max_memory_mb: int | None = None
    max_duration_seconds: int | None = None
    security_clearance_level: str = "standard"
    custom_rules: dict[str, Any] = {}
```

### `CapabilityRequirement`
Formal specification linking a mission requirement from an `ExecutionRequest` to a target `Capability`.

```python
class CapabilityRequirement(BaseModel):
    requirement_id: str
    mission_id: str
    capability_id: str
    priority: CapabilityPriority = CapabilityPriority.HIGH
    source_requirement: str
    constraints: list[CapabilityConstraint] = []
    metadata: dict[str, Any] = {}
```

### `CapabilityEvidence`
Immutable audit record establishing the provenance and reasoning behind capability extraction.

```python
class CapabilityEvidence(BaseModel):
    evidence_id: str
    capability_id: str
    source_stage: str = "capability_analysis"
    asserted_by: str
    provenance_details: dict[str, Any] = {}
    timestamp: str
```

### `CapabilityReport`
Consolidated audit summary report produced by the Capability Analyzer.

```python
class CapabilityReport(BaseModel):
    report_id: str
    mission_id: str
    total_capabilities_analyzed: int = 0
    capabilities: list[Capability] = []
    groups: list[CapabilityGroup] = []
    requirements: list[CapabilityRequirement] = []
    evidence: list[CapabilityEvidence] = []
    generated_at: str
```

---

## 3. Analysis Pipeline Integration

The Capability Model receives inputs from:
- `ExecutionRequest.mission.requirements` (functional & non-functional requirements)
- `ExecutionRequest.mission_context` (project type, workspace metadata)
- `ExecutionRequest.mission_constraints` (budget, local execution flags)

The Capability Analyzer emits an immutable `CapabilityReport` which is passed directly to the Organization Builder.

---

## 4. Architectural Boundaries

- **No Resolution Implementation**: Mapping capabilities to specific agents or skills is deferred to ACR-005 Phase S2 (Capability Resolution).
- **No Model Selection**: Capability constraints do not choose LLM providers or models.
- **No AI Execution**: Analysis is declarative schema modeling only.
