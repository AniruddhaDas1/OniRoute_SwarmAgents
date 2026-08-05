# Phase P4.G1 — Workspace Scaffold Specification

## 1. Subsystem Overview

Phase P4.G1 (**Workspace Scaffold**) is the first stage of Phase 4 (Workspace Scaffolding & Code Generation Foundation) in OniRoute v1.2.

```
RuntimeExecutionSnapshot (P3) ──► Workspace Scaffold Engine (P4.G1) ──► WorkspaceScaffoldReport ──► Project Structure (P4.G2)
```

The Workspace Scaffold Engine processes an immutable [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L135) to deterministically initialize the target workspace directory layout, technology build markers, configuration files, environment placeholders, and tool settings.

It operates **strictly without**:
- Invoking LLMs or AI providers
- Executing build scripts or runtime logic
- Generating actual source code (P4.G2+ responsibility)
- Modifying engine root files (Engine Root is permanently read-only)

---

## 2. Mandatory Existing Component Audit

| Existing Component | Reuse Strategy | New Code Required |
|---|---|---|
| [`Workspace Runtime`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/__init__.py) | Reused `WorkspaceManager`, `EngineResolver`, and safety assertions `assert_no_engine_write` | Consumed in boundary validation |
| [`Workspace Storage`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/storage.py) | Reused `WorkspaceStorage` directory paths and `.oniroute/` layout | Connected without duplicating storage logic |
| [`Artifact Router`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/artifact_router.py) | Reused `ArtifactRouter` for destination path classification | Connected for scaffold report artifact routing |
| [`MissionDeploymentPlan`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/deployment/models.py#L180) | Reused via snapshot references for deployment metadata | Preserved unchanged |
| [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L135) | Sole input contract for workspace scaffolding | Input contract consumed by `WorkspaceScaffoldEngine` |
| [`AgentProfileReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/skills/models.py#L187) | Reused profile metadata embedded in snapshot sessions | Preserved unchanged |
| `Execution Artifacts` | Reused `ReportStorage`, `LogStorage`, `TraceStorage`, `SessionStorage` | Connected to `.oniroute/` subdirectories |
| [`Project Detector`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/project.py) | Reused `ProjectDetector` and `ProjectType` classification | Used for technology stack detection fallback |
| [`Workspace Discovery`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/workspace/discovery.py) | Reused `WorkspaceResolver` for workspace root discovery | Connected for CLI workspace resolution |

---

## 3. Subsystem Responsibilities & Boundaries

- **Input Contract**: Consumes **ONLY** [`RuntimeExecutionSnapshot`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/swarm/models.py#L135).
- **Output Contract**: Produces **ONLY** immutable [`WorkspaceScaffoldReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/scaffold/models.py#L9).
- **Responsibilities**:
  1. Validate input snapshot type and resolve target `workspace_root`.
  2. Enforce Engine Root safety assertions (`assert_no_engine_write`).
  3. Detect target technology stack (`react`, `nextjs`, `python`, `fastapi`, `flutter`, `monorepo`).
  4. Initialize 10 mandatory workspace directories:
     - `.oniroute/`
     - `src/`
     - `tests/`
     - `docs/`
     - `public/`
     - `assets/`
     - `scripts/`
     - `configs/`
     - `logs/`
     - `reports/`
  5. Create deterministic project metadata (`.oniroute/project_metadata.json`, `.oniroute/config.yaml`).
  6. Create technology markers & build files (`package.json`, `vite.config.js`, `next.config.mjs`, `pyproject.toml`, `pubspec.yaml`, `pnpm-workspace.yaml`).
  7. Create configuration files (`tsconfig.json`, `eslint.config.js`, `pytest.ini`, `ruff.toml`, `analysis_options.yaml`).
  8. Create environment placeholders (`.env.example`, `.env.local`).
  9. Create tool configuration (`.gitignore`, `.editorconfig`).
  10. Compute validation evidence and SHA-256 Scaffold Hash.

---

## 4. CLI Reference

```bash
# Scaffold current workspace deterministically
oniroute scaffold

# Scaffold with raw JSON report output
oniroute scaffold --json

# Scaffold specific workspace with custom snapshot file
oniroute scaffold --workspace /path/to/workspace --snapshot /path/to/snapshot.json
```

---

## 5. Verification & Integrity

The scaffold operation verifies workspace structure integrity, read-write permissions, collision safety, engine root read-only protection, and returns a frozen Pydantic [`WorkspaceScaffoldReport`](file:///Users/aniruddhadas/Ani/Coding%20Projects/Google%20Antigravity/Development%20Products/Open%20Source%20Projects/OniRoute_SwarmAgents/runtime/scaffold/models.py#L9) with complete audit evidence.
