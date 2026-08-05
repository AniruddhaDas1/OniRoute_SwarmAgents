# Phase P4.G3 — Implementation Allocation Specification

## 1. Subsystem Overview

Phase P4.G3 (**Implementation Allocation**) is the third stage of Phase 4 (Workspace Scaffolding & Code Generation Foundation) in OniRoute v1.2.

```
ProjectBlueprintReport (P4.G2) ──► Implementation Allocation Engine (P4.G3) ──► ImplementationAllocationReport ──► Generation Contracts (P4.G4)
```

The Implementation Allocation Engine processes an immutable [`ProjectBlueprintReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/blueprint/models.py#L31) to deterministically assign every implementation target (files, directories, modules, components, configuration, documentation, tests, assets, and shared libraries) to an **Engineering Discipline** and an **Agent Profile ID**.

It operates **strictly without**:
- Invoking LLMs or AI providers
- Writing source code implementations
- Executing code or build pipelines
- Modifying engine root files (Engine Root is permanently read-only)

---

## 2. Mandatory Existing Component Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| [`ProjectBlueprintReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/blueprint/models.py#L31) | Sole input contract for modules, expected files, and directory ownership | Consumed in `ImplementationAllocationEngine.allocate_implementation` |
| [`WorkspaceScaffoldReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/scaffold/models.py#L9) | Reused via blueprint references for directory layout & technology stack | Preserved unchanged |
| [`AgentProfileReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L187) | Reused profile definitions for profile assignment | Mapped to discipline profile IDs |
| [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) | Reused via blueprint references for deployment metadata | Preserved unchanged |
| [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L135) | Reused via blueprint snapshot references | Preserved unchanged |
| `Existing Workspace models` | Reused `WorkspaceMetadata`, `ProjectMetadata` | Connected to allocation report output |

---

## 3. Discipline to Agent Profile Assignment Matrix

Every implementation target is mapped to a specific Agent Profile ID and Role Title:

| Discipline | Agent Profile ID | Agent Profile Role Title |
|---|---|---|
| **Frontend** | `prf-fe-spec` | Frontend Specialist |
| **Backend** | `prf-be-eng` | Backend Engineer |
| **Database** | `prf-db-admin` | Database Administrator |
| **Infrastructure** | `prf-devops-eng` | DevOps Infrastructure Engineer |
| **Security** | `prf-sec-auditor` | Security Auditor |
| **Testing** | `prf-qa-eng` | QA Automation Engineer |
| **Documentation** | `prf-doc-spec` | Technical Writer & Documentation Specialist |
| **Automation** | `prf-auto-eng` | Build & Automation Engineer |
| **Analytics** | `prf-telemetry-spec` | Telemetry & Analytics Engineer |
| **AI** | `prf-ai-architect` | AI & Swarm Systems Architect |
| **Shared** | `prf-lead-arch` | Lead System Architect |

---

## 4. CLI Reference

```bash
# Allocate implementation targets for current workspace
oniroute allocate

# Output raw JSON ImplementationAllocationReport
oniroute allocate --json

# Run with explicit ProjectBlueprintReport JSON file
oniroute allocate --blueprint /path/to/blueprint_report.json
```

---

## 5. Verification & Integrity

The allocation engine validates 100% target ownership, zero orphan files, zero duplicate ownership, acyclic DAG dependency sorting, and returns a frozen Pydantic [`ImplementationAllocationReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/allocation/models.py#L31).
