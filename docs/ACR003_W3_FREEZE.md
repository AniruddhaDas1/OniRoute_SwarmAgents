# ACR-003 Phase W3 Freeze

## Phase W3: Workspace Storage & Artifact Routing

ACR-003 Phase W3 is complete. The Workspace Storage Architecture and Artifact
Router are frozen and declared production ready for the local-first storage
model.

Under normal operation, the **OniRoute Engine remains permanently read-only**.
All outputs, generated artifacts, execution logs, sessions, history, traces, and
state are strictly bound to and routed into the **User Workspace Root** under
`.oniroute/`.

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
                     |       OWNS ALL GENERATED OUTPUT  |
                     +----------------------------------+
                                              |
                                              v
                     +----------------------------------+
                     |     .oniroute/ Storage Root      |
                     |  sessions/  history/  traces/   |
                     |  artifacts/ generated/ temp/     |
                     |  reports/ plans/ approvals/      |
                     |  cache/ logs/ memory/ context/   |
                     |  knowledge/ runtime/ locks/      |
                     +----------------------------------+
```

---

## 1. Canonical Workspace Directory Model

The workspace-local storage root is `<workspace_root>/.oniroute/`. Directories
are created lazily on first access.

```text
.oniroute/
├── workspace.yaml        Serialized WorkspaceMetadata
├── sessions/             Session state, manifests, transcripts
├── history/              Execution result records (JSON)
├── traces/               Execution trace event logs (JSONL)
├── artifacts/            Docs, images, presentations, architecture
├── generated/            Generated source code and tests
├── temporary/            Scratch and intermediate files
├── reports/              Audit, benchmark, coverage reports
├── approvals/            Governance approval records (future)
├── cache/                Deterministic cache (future)
├── logs/                 oniroute.log (JSONL) and archived logs
├── memory/               Workspace memory (future)
├── context/              Context snapshots (future)
├── knowledge/            Workspace-local knowledge (future)
├── plans/                Mission and execution plans
├── runtime/              Workspace runtime metadata (future)
└── locks/                Concurrency locks (future)
```

> **Discrepancy resolution**: The canonical directory model lists `traces/`
> (plural). The TRACE STORAGE section text references `.oniroute/trace`
> (singular). **Decision**: `traces/` (plural) is authoritative, matching the
> canonical directory model.

---

## 2. Workspace Storage Manager

`WorkspaceStorage` (`runtime/workspace/storage.py`) is the single entry point
for `.oniroute/` directory management:

| Responsibility | Method |
|---|---|
| Lazy directory creation | `ensure_dir(name)` |
| Create all directories | `ensure_all()` |
| Check existence | `exists()` |
| Per-directory existence | `storage_status()` |
| Entry counting | `count_entries(name)` |
| Write workspace.yaml | `write_workspace_yaml(metadata)` |
| Read workspace.yaml | `read_workspace_yaml()` |

Each subdirectory root is available as a property (e.g. `sessions_root`,
`history_root`, `generated_root`, etc.). Roots are resolved from
`WorkspaceMetadata` fields, with fallback derivation from `workspace_root` when
fields are unset (backward compatibility with Phase W1/W2 metadata).

### workspace.yaml

`.oniroute/workspace.yaml` is a YAML serialization of `WorkspaceMetadata`,
written via `WorkspaceStorage.write_workspace_yaml()` and read via
`WorkspaceStorage.read_workspace_yaml()`. If the file does not exist,
`read_workspace_yaml()` returns `None`.

---

## 3. Artifact Router

`ArtifactRouter` (`runtime/workspace/artifact_router.py`) implements
`ArtifactRouterContract` with the following responsibilities:

| Responsibility | Implementation |
|---|---|
| Resolve destination | `CATEGORY_DIR_MAP` maps `ArtifactCategory` → subdirectory |
| Validate ownership | `ArtifactOwnership` model carries full provenance |
| Prevent Engine writes | `assert_no_engine_write()` called on every resolved path |
| Normalize paths | Paths resolved via `Path.resolve()`; `..` traversal blocked |
| Create directories | `WorkspaceStorage.ensure_dir()` (idempotent, lazy) |
| Validate collisions | Timestamp-suffix auto-rename (lenient) or `ArtifactCollisionError` (strict) |
| Support future categories | `register_category()` + `DEFAULT_CATEGORY_DIR` fallback |

### Category → Subdirectory Mapping

| ArtifactCategory | Subdirectory |
|---|---|
| `SOURCE_CODE` | `generated/` |
| `DOCUMENTATION` | `artifacts/` |
| `IMAGES` | `artifacts/` |
| `REPORTS` | `reports/` |
| `TESTS` | `generated/` |
| `PRESENTATIONS` | `artifacts/` |
| `ARCHITECTURE` | `artifacts/` |
| `LOGS` | `logs/` |
| `PLANS` | `plans/` |
| `SESSIONS` | `sessions/` |
| `TEMPORARY_OUTPUTS` | `temporary/` |

Unknown or future categories default to `artifacts/` and can be registered
dynamically via `register_category()`.

### Collision Handling

- **Lenient mode** (default): If `<filename>` exists in the target directory,
  a unique name is generated by inserting a UTC timestamp suffix before the
  extension: `file_20260805_143000_123456.py`.
- **Strict mode** (`strict_collisions=True`): Raises `ArtifactCollisionError`
  on collision instead of auto-renaming.

### Boundary Verification Invariant

Every resolved `ArtifactDestination` MUST satisfy:

```
Path_destination ⊆ Path_Workspace_Root   AND   Path_destination ⊄ Path_Engine_Root
```

The `ArtifactDestination.validate_boundary()` method asserts this condition. The
`ArtifactRouter` raises an `AssertionError` if the invariant is violated.

---

## 4. Artifact Ownership Model

`ArtifactOwnership` (`runtime/workspace/models.py`) declares complete provenance
for every generated artifact:

| Field | Type | Description |
|---|---|---|
| `workspace_id` | `str` | Workspace that owns the artifact |
| `owner` | `str` | Principal owner of the artifact |
| `mission` | `str \| None` | Mission or objective that produced it |
| `workflow` | `str \| None` | Workflow identifier |
| `agent` | `str \| None` | Agent that generated it |
| `timestamp` | `str` (ISO 8601) | When the artifact was created |
| `artifact_type` | `ArtifactCategory` | Classification |
| `generation_source` | `str` | Command or component that produced it |
| `provenance` | `str` | Chain of custody / origin |
| `validation` | `ValidationState` | Validation result |

`ArtifactRecord` pairs an `ArtifactDestination` with its `ArtifactOwnership`.

---

## 5. Workspace-Local Storage Classes

All storage classes are bound to a `WorkspaceMetadata` instance and only write
to `.oniroute/` subdirectories.

| Class | Module | Directory | Key Methods |
|---|---|---|---|
| `SessionStorage` | `session_storage.py` | `sessions/` | `create_session()`, `write_data()`, `read_data()`, `list_sessions()`, `close_session()`, `delete_session()` |
| `ExecutionHistoryStorage` | `history_storage.py` | `history/` | `persist()`, `load()`, `load_all()`, `count()` |
| `TraceStorage` | `trace_storage.py` | `traces/` | `write_trace()`, `read_trace()`, `list_traces()`, `append_trace()`, `count()` |
| `LogStorage` | `log_storage.py` | `logs/` | `write_log()`, `read_logs()`, `count()`, `archive()` |

---

## 6. Engine Safety Assertions

`engine_safety.py` provides three assertion functions and a constant listing
all protected directory names that must never exist inside Engine Root:

| Function | Behavior |
|---|---|
| `assert_within_workspace(path, workspace_root)` | Raises `WorkspaceBoundaryViolation` if path escapes workspace |
| `assert_outside_engine(path, engine_root)` | Raises `EngineWriteViolation` if path is inside engine root |
| `assert_no_engine_write(path, workspace_root, engine_root)` | Combined assertion; returns resolved path on success |

`PROTECTED_ENGINE_TARGETS` lists all 16 subdirectory names:
`artifacts`, `logs`, `sessions`, `plans`, `memory`, `history`, `generated`,
`temporary`, `traces`, `reports`, `approvals`, `cache`, `context`, `knowledge`,
`runtime`, `locks`.

### Enforcement Points

| Component | Guard |
|---|---|
| `WorkspaceStorage.ensure_dir()` | `assert_no_engine_write` |
| `WorkspaceStorage.ensure_workspace_root()` | `assert_no_engine_write` |
| `WorkspaceStorage.write_workspace_yaml()` | `assert_no_engine_write` |
| `ArtifactRouter.route_artifact()` | `assert_no_engine_write` + `validate_boundary()` |
| `SessionStorage.create_session()` / `write_data()` | `assert_no_engine_write` |
| `ExecutionHistoryStorage.persist()` | `assert_no_engine_write` |
| `TraceStorage.write_trace()` / `append_trace()` | `assert_no_engine_write` |
| `LogStorage.write_log()` / `archive()` | `assert_no_engine_write` |

---

## 7. CLI Extension

`oniroute workspace` now displays three tables:

1. **OniRoute Workspace Discovery** — Workspace Root, Engine Root, Project Type,
   Discovery Method, Validation Status (unchanged from Phase W2).
2. **Workspace Storage** — `.oniroute/` path, session count, artifact count,
   history count, traces count, logs count, storage initialized status.
3. **Storage Directory Status** — Each of the 16 subdirectories with existence
   indicator and entry count.

```bash
oniroute workspace
oniroute workspace --workspace /path/to/target/project
```

---

## 8. Phase W3 Validation Summary

- **New tests**: 42 unit tests in `tests/runtime/test_workspace_storage.py`
  covering artifact routing, workspace storage, engine protection, ownership,
  session/history/trace/log storage, and CLI integration.
- **No regression**: All 48 pre-existing tests continue to pass (76 total in
  the W3-affected test runs; 90 across the full suite).
- **Engine protection**: `assert_no_engine_write()` is called at every
  filesystem write point across all storage components.
- **Deterministic storage**: All paths are derived deterministically from
  `WorkspaceMetadata.workspace_root` and `engine_root`.
- **Workspace ownership**: All generated content routes into `.oniroute/`
  subdirectories via `ArtifactRouter`.
- **`git diff --check`**: Passes with zero whitespace errors.
- **Frozen architecture intact**: No modifications to frozen layers
  (Agent Architecture, Motion ACR-001, ICOE ACR-002, Runtime v0.6). The frozen
  `runtime/execution/` modules (`engine.py`, `history.py`, `events.py`) remain
  untouched; W3 adds workspace-local persistence *alongside* them.

---

## 9. Recommendation for ACR-003 Phase W4

Phase W4 should implement the complete Workspace CLI and runtime integration:

1. **Workspace lifecycle commands**
   - `oniroute workspace init` — initialize `.oniroute/` structure with
     `workspace.yaml`
   - `oniroute workspace inspect` — detailed `.oniroute/` tree, storage usage,
     file counts per subdirectory
   - `oniroute workspace clean` — remove temporary/scratch files
   - `oniroute workspace archive` — archive session/trace/log state

2. **Storage diagnostics**
   - `oniroute workspace diagnose` — verify boundary integrity, detect stray
     files in Engine Root, validate path normalization

3. **Developer experience**
   - `oniroute workspace open` — open `.oniroute/` in the system file manager
   - `oniroute workspace path` — print workspace root for shell integration
   - `oniroute workspace env` — export workspace paths as environment variables

4. **Runtime integration** (wire W3 storage into the frozen WorkflowEngine)
   - Persist `ExecutionResult` objects to `.oniroute/history/` via
     `ExecutionHistoryStorage`
   - Persist `ExecutionEvent` streams to `.oniroute/traces/` via `TraceStorage`
   - Route log output to `.oniroute/logs/` via `LogStorage`
   - This unblocks multi-invocation history for CLI `history`, `trace`,
     `explain execution`, and `optimize report` commands

5. **Workspace YAML management**
   - Validate `workspace.yaml` schema and path consistency
   - Auto-regenerate when workspace root or engine root changes
