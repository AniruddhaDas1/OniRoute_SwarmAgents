# ACR-003 Phase W5: Workspace Architecture Specification & Certification

## Executive Summary

ACR-003 Phase W5 certifies, validates, and permanently freezes the **Workspace Architecture** for the OniRoute framework (v1.0.0).

The Workspace Architecture establishes a strict, provider-independent architectural boundary decoupling the **OniRoute Engine Root** (the framework installation containing agent definitions, workflows, skills, policies, and core runtime engines) from the **User Workspace Root** (the target repository owning user source code, state, memory, session logs, and generated artifacts).

```text
+-----------------------------------------------------------------------+
|                         OniRoute Engine Root                          |
|             (/path/to/OniRoute_SwarmAgents installation)             |
|                       PERMANENTLY READ-ONLY                           |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                           ExecutionContext                            |
|             (Combines Engine Root + User Workspace Root)              |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                          User Workspace Root                          |
|                       (Target Project Directory)                      |
|                     OWNS ALL MUTABLE STATE & OUTPUTS                  |
|                                                                       |
|   Workspace Root/                                                     |
|   ├── src/                 (User Source Files)                    |
|   ├── docs/                (User Documentation)                   |
|   └── .oniroute/           (Workspace Storage Tree)               |
|       ├── sessions/        (Session State)                        |
|       ├── history/         (Execution Records)                    |
|       ├── plans/           (Execution Plans)                      |
|       ├── traces/          (Event Streams)                        |
|       ├── artifacts/       (Outputs & Mockups)                    |
|       ├── generated/       (Generated Code & Tests)               |
|       ├── temporary/       (Transient Scratch Files)              |
|       ├── reports/         (Audit & Governance Reports)           |
|       ├── approvals/       (Human Approval State)                 |
|       ├── cache/           (Workspace Cache)                      |
|       ├── logs/            (Runtime Logs)                         |
|       ├── memory/          (Workspace Memory Context)             |
|       ├── context/         (Context Snapshots)                    |
|       ├── knowledge/       (Local Workspace Knowledge)            |
|       ├── runtime/         (Runtime Ephemeral State)              |
|       └── locks/           (Concurrency Locks)                    |
+-----------------------------------------------------------------------+
```

---

## 1. Architectural Principles & Boundaries

1. **Engine Root Read-Only Invariant**: Under all execution modes, the OniRoute Engine Root remains permanently read-only. No runtime operation, swarm action, context optimization, or artifact generation may write, mutate, or create files within the Engine Root.
2. **Workspace Root Sovereignty**: All generated code, execution history, trace logs, session states, governance audit records, context snapshots, and temporary files are stored exclusively inside `<workspace_root>/.oniroute/`.
3. **Engine Safety Guards**: All filesystem operations are filtered through `assert_no_engine_write()`, which asserts that paths reside strictly inside the Workspace Root and strictly outside the Engine Root.
4. **Provider-Independent Discovery**: Workspaces are discovered dynamically using a deterministic 4-tier priority cascade without hardcoded provider dependencies.
5. **Declarative Contracts**: Workspace management, discovery, storage, and artifact routing implement explicit abstract contracts (`WorkspaceManagerContract`, `WorkspaceResolverContract`, `ArtifactRouterContract`, `EngineResolverContract`).

---

## 2. Dynamic Workspace Discovery & Priority Rules

Workspace resolution determines the active Workspace Root location using the following deterministic priority order:

| Priority Level | Resolution Method | Trigger & Description | Confidence |
|---|---|---|---|
| **Level 1** | `EXPLICIT_ARGUMENT` | Passed explicitly via CLI `--workspace <path>` or programmatic parameter | `1.00` |
| **Level 2** | `CURRENT_WORKING_DIRECTORY` | Current directory contains a manifest (`pyproject.toml`, `package.json`, `.oniroute/`, `.git`, etc.) | `1.00` |
| **Level 3** | `PARENT_PROJECT_DETECTION` | Traverses parent directories up the filesystem tree searching for project manifests | `0.85` |
| **Level 4** | `WORKSPACE_CONFIGURATION` | System configuration default or fallback to current working directory | `0.50` |

---

## 3. Canonical Data Models

### 3.1 `WorkspaceMetadata`
Defines the canonical metadata identity of a workspace:
- `workspace_id`: Unique identifier (e.g. `ws-123456`).
- `name`: Workspace display name derived from project detector or directory name.
- `workspace_root`: Resolved absolute `Path` to the workspace root.
- `engine_root`: Resolved absolute `Path` to the read-only framework installation root.
- `project_type`: Detected framework project type (`ProjectType`).
- `lifecycle`: Operational status (`UNINITIALIZED`, `INITIALIZING`, `ACTIVE`, `SUSPENDED`, `ARCHIVED`).
- `status`: Health status (`VALID`, `DEGRADED`, `INVALID`, `UNVERIFIED`).
- `trust`: Security trust level (`UNTRUSTED`, `RESTRICTED`, `TRUSTED`, `VERIFIED`).
- `created`: ISO-8601 UTC timestamp string.
- `version`: Metadata schema version (`1.0.0`).
- Subdirectory root paths: `artifact_root`, `session_root`, `logs_root`, `memory_root`, `configuration_root`, `plans_root`, `history_root`, `traces_root`, `generated_root`, `temporary_root`, `reports_root`, `approvals_root`, `cache_root`, `context_root`, `knowledge_root`, `runtime_root`, `locks_root`.

### 3.2 `ProjectMetadata`
Represents target codebase parameters:
- `project_id`: Project identifier.
- `name`: Target project name.
- `project_type`: Detected ecosystem (`PYTHON`, `NODE`, `REACT`, `NEXTJS`, `VUE`, `ANGULAR`, `GO`, `RUST`, `JAVA`, `DOTNET`, `FLUTTER`, `REACT_NATIVE`, `EMPTY`, `UNKNOWN`).
- `root_path`: Absolute path to project root.
- `manifest_path`: Path to primary project configuration manifest.
- `is_empty`: Boolean indicating whether workspace contains no code files.

### 3.3 `ExecutionContext`
Encapsulates runtime boundaries:
- `engine_root`: Path to Engine Root.
- `workspace_root`: Path to Workspace Root.
- `cwd`: Current execution directory.
- `workspace_metadata`: Optional workspace metadata reference.
- `is_engine_read_only()`: Method asserting `engine_root != workspace_root` or write isolation.

---

## 4. Artifact Routing Subsystem

The `ArtifactRouter` categorizes outputs into canonical types and routes them into the appropriate `.oniroute/` subdirectory:

| Artifact Category | Target Directory | Description |
|---|---|---|
| `SOURCE_CODE` | `.oniroute/generated/` | Application source files, refactored modules, code snippets |
| `TESTS` | `.oniroute/generated/` | Unit tests, test suites, integration tests |
| `DOCUMENTATION` | `.oniroute/artifacts/` | Generated Markdown documentation, API specifications |
| `IMAGES` | `.oniroute/artifacts/` | UI mockups, visual diagrams, image assets |
| `PRESENTATIONS` | `.oniroute/artifacts/` | Slide decks, executive briefs |
| `ARCHITECTURE` | `.oniroute/artifacts/` | Architecture diagrams, schemas |
| `REPORTS` | `.oniroute/reports/` | Optimization reports, audit summaries, governance logs |
| `LOGS` | `.oniroute/logs/` | Runtime execution logs, console output |
| `PLANS` | `.oniroute/plans/` | Execution plan structures, step specs |
| `SESSIONS` | `.oniroute/sessions/` | Session state, serialized conversation contexts |
| `TEMPORARY_OUTPUTS` | `.oniroute/temporary/` | Scratch files, transient build outputs |

### Collision Prevention Policy
- **Lenient Mode** (default): Appends a UTC timestamp (`_YYYYMMDD_HHMMSS_ffffff`) suffix to resolve file naming collisions automatically.
- **Strict Mode**: Raises `ArtifactCollisionError` when a target filename already exists.

---

## 5. Certification & Freeze Confirmation

As of Phase W5 (OniRoute v1.0.0), the Workspace Architecture is certified complete and frozen:
- All 132 tests in the suite pass without regressions.
- Engine safety guards strictly block writes to Engine Root.
- File boundary validation passes across multi-execution runs.
