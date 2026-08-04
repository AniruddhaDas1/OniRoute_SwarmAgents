# ACR-003 Phase W1: Workspace Architecture Foundation

## Executive Summary

ACR-003 Phase W1 establishes the provider-independent Workspace Architecture Foundation for the OniRoute framework. This architectural extension formally decouples the **OniRoute Engine** (the core framework, CLI, agents, skills, and configuration) from the **User Workspace** (the target project repository containing user source code, generated artifacts, execution logs, sessions, and state).

Under normal operation, the **OniRoute Engine remains permanently read-only**. All outputs, source code edits, generated tests, documentation, images, execution logs, and memory sessions are strictly bound to and routed into the **User Workspace Root**.

```
                           +----------------------------------+
                           |       OniRoute Engine Root       |
                           |   (Installed OniRoute Framework) |
                           |       PERMANENTLY READ-ONLY      |
                           +----------------------------------+
                                             |
                                             v
                           +----------------------------------+
                           |        Execution Context         |
                           |  (Engine Root + Workspace Root)  |
                           +----------------------------------+
                                             |
                                             v
                           +----------------------------------+
                           |        User Workspace Root       |
                           |    (Target Project Repository)   |
                           |    OWNS ALL GENERATED ARTIFACTS  |
                           +----------------------------------+
```

---

## 1. Engine Root vs Workspace Root Boundaries

### 1.1 Engine Root
- **Definition**: Represents the absolute filesystem path to the OniRoute framework installation (e.g. `/opt/oniroute/OniRoute_SwarmAgents` or `B_Landing/OniRoute_SwarmAgents`).
- **Contents**:
  - Runtime Core (`runtime/`)
  - Agent Definitions (`agents/`)
  - Skill Registry & Packs (`skills/`)
  - Workflow Specifications (`workflows/`)
  - Knowledge Sources & Schemas (`knowledge/`)
  - Packages & Mappings (`packages/`, `mappings/`)
  - CLI & Typer App (`cli/`)
  - Base Configuration (`config/`)
- **Operational Boundary**: **Strictly Read-Only**. Normal runtime execution, swarm operations, context optimization, and artifact generation MUST NEVER write to or mutate files within the Engine Root.

### 1.2 Workspace Root
- **Definition**: Represents the target project workspace or repository being analyzed, modified, or constructed (e.g. `B_Landing/` or `/home/user/my-app`).
- **Ownership**: The Workspace Root owns all output directories, generated source code, project documentation, test suites, execution logs, session states, and transient memory files.
- **Directory Structure Standard**:
  ```text
  Workspace Root/
  ├── src/                       (Target Project Source Code)
  ├── docs/                      (Project Documentation)
  └── .oniroute/                 (Workspace Sub-Roots)
      ├── config/                (Workspace Configuration Root)
      ├── artifacts/             (Generated Artifact Root)
      ├── sessions/              (Session State Root)
      ├── logs/                  (Execution Logs Root)
      └── memory/                (Workspace Memory Root)
  ```

---

## 2. Declarative Workspace Discovery Rules

Workspace discovery determines the active Workspace Root location using a deterministic, declarative priority order. Phase W1 establishes the metadata specifications and priority order without implementing discovery logic:

| Priority | Strategy | Description |
|---|---|---|
| **1** | `EXPLICIT_ARGUMENT` | Passed via CLI `--workspace <path>` or programmatic API argument |
| **2** | `CURRENT_WORKING_DIRECTORY` | Derived from the current working directory (`cwd`) where execution is invoked |
| **3** | `PARENT_PROJECT_DETECTION` | Derived by searching ancestor directories for project manifests (`package.json`, `pyproject.toml`, `.git`, `.oniroute/`) |
| **4** | `WORKSPACE_CONFIGURATION` | Default fallback specified in system configuration |

---

## 3. Canonical Workspace Model

The canonical Workspace model (`runtime.workspace.models.WorkspaceMetadata`) defines the workspace identity, lifecycle state, root directories, and trust parameters:

```python
class WorkspaceMetadata(BaseModel):
    workspace_id: str
    name: str
    workspace_root: Path
    engine_root: Path
    project_type: ProjectType
    lifecycle: WorkspaceLifecycle
    status: WorkspaceStatus
    created: str
    version: str
    owner: str | None
    artifact_root: Path
    session_root: Path
    logs_root: Path
    memory_root: Path
    configuration_root: Path
    validation: ValidationState
    trust: TrustLevel
```

### 3.1 Workspace Enums & Types
- **`WorkspaceLifecycle`**: `UNINITIALIZED`, `INITIALIZING`, `ACTIVE`, `SUSPENDED`, `ARCHIVED`
- **`WorkspaceStatus`**: `VALID`, `DEGRADED`, `INVALID`, `UNVERIFIED`
- **`TrustLevel`**: `UNTRUSTED`, `RESTRICTED`, `TRUSTED`, `VERIFIED`

---

## 4. Provider-Independent Project Model

Projects inside the Workspace are modeled independently of AI provider implementations (`runtime.workspace.models.ProjectMetadata`). Supported project types include:

- **`PYTHON`**: Python libraries, apps, virtualenv structures
- **`NODE`**: Node.js applications and packages
- **`REACT`**: React single-page applications
- **`NEXTJS`**: Next.js full-stack web applications
- **`VUE`**: Vue.js applications
- **`ANGULAR`**: Angular applications
- **`GO`**: Go modules and applications
- **`RUST`**: Rust Cargo projects
- **`JAVA`**: Java Maven/Gradle projects
- **`DOTNET`**: .NET solutions and projects
- **`FLUTTER`**: Flutter cross-platform applications
- **`REACT_NATIVE`**: React Native mobile applications
- **`EMPTY`**: Empty directory workspace awaiting initialization
- **`UNKNOWN`**: Unclassified target workspace

---

## 5. Artifact Routing Model

All generated content is classified into canonical `ArtifactCategory` types and routed into designated destinations under `Workspace Root`.

### 5.1 Artifact Categories
- `SOURCE_CODE`: Application source files, refactored modules, generated code
- `DOCUMENTATION`: Markdown docs, API specs, architectural diagrams
- `IMAGES`: Visual assets, diagrams, UI mockups
- `REPORTS`: Audit reports, benchmark summaries, coverage matrices
- `TESTS`: Unit tests, integration suites, test fixtures
- `PRESENTATIONS`: Slide decks, visual briefs
- `ARCHITECTURE`: System blueprints, schema definitions
- `LOGS`: Execution traces, agent telemetry, diagnostics
- `PLANS`: Mission plans, execution strategies
- `SESSIONS`: Session transcripts, state snapshots
- `TEMPORARY_OUTPUTS`: Intermediate build artifacts, scratch scripts

### 5.2 Boundary Verification Invariant
Every resolved `ArtifactDestination` MUST satisfy:
$$\text{Path}_{\text{destination}} \subseteq \text{Path}_{\text{Workspace Root}} \quad \land \quad \text{Path}_{\text{destination}} \nsubseteq \text{Path}_{\text{Engine Root}}$$

The `ArtifactDestination.validate_boundary()` method asserts this condition prior to any downstream write operation.

---

## 6. Runtime Architecture Impact

The runtime responsibilities pipeline decouples workspace management from execution:

```text
Workspace Manager
      ↓
Engine Resolver
      ↓
Workspace Resolver
      ↓
Runtime Execution Context
      ↓
Artifact Router
      ↓
Execution Pipeline
```

Every runtime component receives an immutable `ExecutionContext` encapsulating both `engine_root` and `workspace_root`.

---

## 7. CLI Contract Specification (Future)

Phase W1 defines the future CLI interaction contract without adding command implementations:

### 7.1 `oniroute doctor`
When invoked, `oniroute doctor` will output diagnostic information detailing:
- Workspace ID & Name
- Workspace Root Path
- Engine Root Path
- OniRoute Version
- Read-Only Engine Status
- Workspace Integrity & Validation Status

### 7.2 `oniroute --workspace`
Global CLI flag enabling explicit workspace targeting:
```bash
oniroute --workspace /path/to/target/project doctor
```

---

## 8. Phase W1 Validation Summary

- **Distinct Concepts**: Engine Root and Workspace Root are explicitly separated in models, contracts, and execution contexts.
- **Workspace Artifact Ownership**: All artifact destination models route into `workspace_root`.
- **Engine Protection**: `ExecutionContext` and `ArtifactDestination` enforce read-only assertion on `engine_root`.
- **Provider Independence**: All models use pure, provider-neutral types.
- **Zero Runtime Regression**: 34 pre-existing runtime unit tests and 5 new workspace architecture foundation unit tests pass cleanly ($39/39$ tests passing).
- **Frozen Architecture Intact**: No modifications made to frozen layers (Agent Architecture v0.1, Motion ACR-001, ICOE ACR-002 v1.1).
- `git diff --check` passes with zero formatting errors.

---

## 9. Recommendation for ACR-003 Phase W2

Phase W2 should implement:
1. **Deterministic Workspace Discovery**: Resolver implementation executing the 4-level priority rules (`EXPLICIT_ARGUMENT` $\rightarrow$ `CURRENT_WORKING_DIRECTORY` $\rightarrow$ `PARENT_PROJECT_DETECTION` $\rightarrow$ `WORKSPACE_CONFIGURATION`).
2. **Declarative Project Detection**: File-based detection engine for manifest files (`pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, etc.) mapping target projects to `ProjectType`.
3. **Workspace Validation Engine**: Structural and permission checks asserting workspace read/write access while verifying engine read-only protection.
4. **Engine Discovery Engine**: Robust resolution of the OniRoute Engine installation root across environments.
