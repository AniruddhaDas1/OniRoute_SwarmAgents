# Phase P4.G2 — Project Blueprint Specification

## 1. Subsystem Overview

Phase P4.G2 (**Project Blueprint**) is the second stage of Phase 4 (Workspace Scaffolding & Code Generation Foundation) in OniRoute v1.2.

```
WorkspaceScaffoldReport (P4.G1) ──► Project Blueprint Engine (P4.G2) ──► ProjectBlueprintReport ──► File Allocation (P4.G3)
```

The Project Blueprint Engine processes an immutable [`WorkspaceScaffoldReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/scaffold/models.py#L9) to deterministically define project modules, directory ownership, logical components, technology stack mappings, expected files, and deliverables across 11 engineering disciplines.

It operates **strictly without**:
- Invoking LLMs or AI providers
- Writing source code implementations
- Creating physical files on disk (Scaffold P4.G1 created physical folders; Blueprint P4.G2 defines structural contracts)
- Modifying engine root files (Engine Root is permanently read-only)

---

## 2. Mandatory Existing Component Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| [`WorkspaceScaffoldReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/scaffold/models.py#L9) | Primary input contract for workspace directory paths & technology stack | Consumed in `ProjectBlueprintEngine.generate_blueprint` |
| [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L135) | Reused via scaffold snapshot evidence references | Preserved unchanged |
| [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) | Reused via snapshot references for deployment metadata | Preserved unchanged |
| [`AgentProfileReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L187) | Reused profile metadata for discipline mapping | Preserved unchanged |
| [`ExecutionSkillBundleReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L143) | Reused skill capabilities for logical component mapping | Preserved unchanged |
| [`Project Detector`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/project.py) | Reused `ProjectDetector` and `ProjectType` classification | Used for technology stack mapping details |
| `Existing Workspace models` | Reused `WorkspaceMetadata`, `ProjectMetadata` | Connected to blueprint report output |

---

## 3. Engineering Disciplines Supported

Phase P4.G2 maps all workspace modules and directories onto 11 engineering disciplines:

1. **Frontend**: UI components, pages, client routes, state management, assets.
2. **Backend**: REST/GraphQL/gRPC APIs, business logic controllers, service layers.
3. **Database**: Database models, ORM schemas, migration scripts, persistence layers.
4. **Infrastructure**: Deployment manifests, Docker/K8s configs, environment templates.
5. **Security**: Auth policies, secret scanners, security governance rules.
6. **Testing**: Unit tests, integration suites, end-to-end regression tests.
7. **Documentation**: System architecture specs, API docs, developer guides.
8. **Automation**: Build scripts, code generators, CI/CD workflow scripts.
9. **Analytics**: Performance telemetry, execution logs, analytics dashboards.
10. **AI**: Agent manifests, skill specs, prompt templates, swarm configurations.
11. **Shared**: Common types, shared utilities, core constants.

---

## 4. CLI Reference

```bash
# Generate project blueprint from scaffolded workspace
oniroute blueprint-project

# Output raw JSON ProjectBlueprintReport
oniroute blueprint-project --json

# Generate blueprint from explicit scaffold report JSON file
oniroute blueprint-project --scaffold /path/to/scaffold_report.json
```

---

## 5. Verification & Integrity

The blueprint engine validates that every module and directory is assigned to exactly one discipline, orphan modules are prohibited, duplicate ownership is prevented, and dependency DAG integrity is verified with 100% coverage.
