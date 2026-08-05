# Master Organization Builder Architecture (`docs/ORGANIZATION_ARCHITECTURE.md`)

## Executive Summary

This document establishes the overarching architecture specification for the **Engineering Organization Builder** in OniRoute (v1.0.0, ACR-005 Phase S1).

The Engineering Organization Builder sits between Mission Orchestration (ACR-004) and future Agent Execution Runtimes. It converts frozen `ExecutionRequest` payloads into deterministic, validated engineering organization topologies represented as immutable `ExecutionBlueprint` objects.

Phase S1 is strictly an **ARCHITECTURE ONLY** release. It introduces canonical models, contracts, and schema definitions without implementing runtime execution or AI model invocations.

---

## 1. End-to-End Architectural Pipeline

```text
+---------------------------------------------------------------------------------------+
|                                    ExecutionRequest                                   |
|                        (Produced by Mission Orchestrator ACR-004)                      |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                  Capability Analysis                                  |
|            (Extracts capability requirements, constraints, and priorities)            |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                 Organization Builder                                  |
|            (Determines engineering roles, member slots, and department hierarchy)      |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                Organization Validation                                |
|            (Validates boundaries, structural integrity, and constraint rules)          |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                      Swarm Graph                                      |
|      (Constructs dependency, reporting, execution, review, and approval graphs)       |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                   Execution Blueprint                                 |
|            (Seals immutable execution payload for future Agent Runtime handoff)        |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                 Agent Runtime (Future)                                |
+---------------------------------------------------------------------------------------+
```

---

## 2. Comprehensive Model Architecture

The architecture is implemented in the `runtime.organization` Python package across six dedicated modules:

1. **`roles.py`**: Defines `OrganizationRoleType` (13 canonical engineering roles + custom extensible types) and `OrganizationRole`.
2. **`capability.py`**: Defines `Capability`, `CapabilityGroup`, `CapabilityPriority`, `CapabilityConstraint`, `CapabilityRequirement`, `CapabilityEvidence`, and `CapabilityReport`.
3. **`models.py`**: Defines `OrganizationMember`, `OrganizationHierarchy`, `OrganizationDependency`, `OrganizationGraph`, `OrganizationEvidence`, `OrganizationReport`, and `Organization`.
4. **`swarm_graph.py`**: Defines `SwarmGraphNode`, `SwarmGraphEdge`, `ReportingHierarchy`, `ExecutionHierarchy`, `ReviewHierarchy`, `ApprovalHierarchy`, and `SwarmGraph`.
5. **`blueprint.py`**: Defines `ExecutionReadiness` and `ExecutionBlueprint`.
6. **`contracts.py`**: Defines `CapabilityAnalyzerContract`, `OrganizationBuilderContract`, `OrganizationValidatorContract`, `SwarmGraphBuilderContract`, and `ExecutionBlueprintBuilderContract`.

---

## 3. Department & Discipline Ownership Matrix

The Organization Builder maps all swarm roles to three core organizational departments:

```text
                               +-----------------------------+
                               |    Executive Department     |
                               | (Strategic Goals & Context) |
                               +-----------------------------+
                                              |
                                              v
                               +-----------------------------+
                               |   Engineering Department    |
                               | (Software Design & Systems) |
                               +-----------------------------+
                                              |
      +-------------------+-------------------+-------------------+-------------------+
      |                   |                   |                   |                   |
      v                   v                   v                   v                   v
+------------+     +------------+     +------------+     +------------+     +------------+
| Frontend   |     | Backend    |     | Database   |     | Security   |     | QA         |
| Discipline |     | Discipline |     | Discipline |     | Discipline |     | Discipline |
+------------+     +------------+     +------------+     +------------+     +------------+
      |                   |                   |                   |                   |
      +-------------------+-------------------+-------------------+-------------------+
                                              |
                                              v
                               +-----------------------------+
                               |     Platform Department     |
                               |  (Tech Advisory & Infra)    |
                               +-----------------------------+
```

### Department Responsibilities
- **Executive Department**: Strategic direction, context validation, high-level governance, and final sign-off gates.
- **Engineering Department**: Core software engineering across 13 disciplines (Architecture, Presentation, Motion, Frontend, Backend, Database, Security, QA, DevOps, Documentation, Reviewer, Research, Mobile, AI, Infrastructure).
- **Platform Department**: Vendor-specific infrastructure guidance, cloud platform options, managed service integration, and environment provisioning advisories.

---

## 4. Integration Matrix with Existing Frozen Engines

| Engine | Integration Type | Boundary Rule |
| :--- | :--- | :--- |
| **Mission Orchestrator** | Input Source | Consumes `ExecutionRequest` payload; no modification to orchestrator |
| **Workspace** | Read-Only Context | Consumes `WorkspaceResolver` and root paths; no filesystem writes |
| **Resolution Engine** | Registry Interface | Consumes Agent/Skill/Knowledge/Package schemas; no dynamic loading |
| **Context Engine** | Context Boundary | Consumes `ContextPacket` and token budgets |
| **ICOE** | Context Optimization | Consumes context compression outputs |
| **Planning Engine** | Contract Consumer | References plan requirements; no plan generation |
| **Governance** | Boundary Rules | Enforces compliance constraints; no policy overrides |
| **UMAL** | Model Abstraction | References capability interfaces; no model selection |

---

## 5. Architectural Verification & Zero-Side-Effect Guarantees

All models and contracts in `runtime.organization` satisfy the following strict architecture criteria:

1. **Zero Runtime Side-Effects**: Importing and instantiating models performs zero network I/O, file system mutations, or background thread creation.
2. **Zero AI Invocation**: Models do not invoke LLM APIs, prompt compilers, or neural inference engines.
3. **Zero Model Selection**: Model selection remains 100% isolated within UMAL.
4. **Zero Workflow Generation**: Task sequencing remains 100% isolated within Planning Engine.
5. **Pydantic Immutability**: All model instances are declarative, strongly-typed schema data containers.

---

## 6. Implementation Roadmap

- **Phase S1 (Architecture Only - COMPLETED)**: Canonical pipeline, models, schemas, multi-view graph definitions, blueprint contracts, documentation, and architecture validation tests.
- **Phase S2 (Capability Resolution - Next)**: Map `ExecutionRequest` to capability requirements using existing Agent, Skill, Knowledge, Package, and Workflow registries without AI execution.
- **Phase S3 (Organization Synthesis)**: Implement deterministic topology builders for role allocation and hierarchy generation.
- **Phase S4 (Swarm Graph Generation)**: Implement directed graph synthesis for multi-perspective dependency, execution, review, and approval views.
- **Phase S5 (Execution Blueprint Seal)**: Implement blueprint builder and readiness validator for Agent Runtime handoff.
