# Workspace Storage Audit & Specification (`.oniroute/`)

## Executive Summary

This document specifies the canonical directory layout, ownership model, read/write rules, creation policies, and persistence guarantees for the OniRoute Workspace Storage subsystem (`WorkspaceStorage`).

All workspace state is stored under `<workspace_root>/.oniroute/`. The directory tree is managed lazily, ensuring subdirectories are created on first write while validating Engine Root safety prior to any filesystem mutation.

---

## 1. Global Storage Rules & Engine Safety

- **Storage Location**: `<workspace_root>/.oniroute/`
- **Ownership**: Strictly owned by the User Workspace Root.
- **Engine Safety Boundary**: Every write operation passes through `assert_no_engine_write(target_path, workspace_root, engine_root)`. If `target_path` is inside the Engine Root or outside the Workspace Root, an `EngineWriteViolation` or `WorkspaceBoundaryViolation` is raised immediately.
- **Creation Policy**: Lazy creation upon access via `WorkspaceStorage.ensure_dir("<subdir_name>")` or `ensure_all()`.
- **Serialization**: Canonical metadata is serialized to `.oniroute/workspace.yaml`.

---

## 2. Directory Audit & Subdirectory Specifications

### 2.1 `sessions/`
- **Ownership**: User Workspace (`SessionStorage`)
- **Purpose**: Persists session lifecycle metadata, session state snapshots, and conversation history across runs.
- **Read/Write Rules**: Read/Write on session creation, update, and resume. Read-only on diagnostic listing.
- **Creation Policy**: Lazily created when the first session is created or loaded.
- **Persistence**: Permanent per workspace; retained across restarts.

### 2.2 `history/`
- **Ownership**: User Workspace (`ExecutionHistoryStorage`)
- **Purpose**: Stores structured execution records (`<execution_id>.json`) summarizing workflow status, duration, step status, and output metadata.
- **Read/Write Rules**: Write once upon workflow execution completion; read-only during CLI inspection (`oniroute history`).
- **Creation Policy**: Lazily created when the first workflow execution finishes.
- **Persistence**: Permanent append-only history log.

### 2.3 `plans/`
- **Ownership**: User Workspace (`ArtifactRouter` / `WorkflowEngine`)
- **Purpose**: Holds execution plans, step graphs, and mission breakdown documents generated before or during workflow execution.
- **Read/Write Rules**: Written during planning phase (`oniroute plan workflow`); read during execution phase.
- **Creation Policy**: Lazily created when a plan is generated or saved.
- **Persistence**: Retained for auditability and step re-execution.

### 2.4 `traces/`
- **Ownership**: User Workspace (`TraceStorage`)
- **Purpose**: Stores fine-grained event execution streams as JSON Lines (`<execution_id>.jsonl`) for telemetry and debugging.
- **Read/Write Rules**: Appended to during step execution; read-only during CLI trace inspection (`oniroute events`).
- **Creation Policy**: Lazily created on the first emitted trace event.
- **Persistence**: Permanent append-only event stream.

### 2.5 `artifacts/`
- **Ownership**: User Workspace (`ArtifactRouter`)
- **Purpose**: Stores non-code generated assets including documentation, Markdown briefs, diagrams, images, slide decks, and architecture designs.
- **Read/Write Rules**: Written by agents and skills via `ArtifactRouter.route_artifact()`. Read-only by users/agents.
- **Creation Policy**: Lazily created when the first documentation or image asset is generated.
- **Persistence**: Permanent workspace artifacts.

### 2.6 `generated/`
- **Ownership**: User Workspace (`ArtifactRouter`)
- **Purpose**: Stores machine-generated source code, refactored code modules, unit tests, and integration test suites.
- **Read/Write Rules**: Written by code-generating skills and agents via `ArtifactRouter`.
- **Creation Policy**: Lazily created when source code or tests are generated.
- **Persistence**: Permanent generated project code assets.

### 2.7 `temporary/`
- **Ownership**: User Workspace (`ArtifactRouter` / Scratch utilities)
- **Purpose**: Holds intermediate scratch files, transient build outputs, and temporary processing buffers.
- **Read/Write Rules**: Read/Write during active execution; purgeable during workspace cleanup.
- **Creation Policy**: Lazily created when temporary outputs are required.
- **Persistence**: Transient / Ephemeral (purgeable).

### 2.8 `reports/`
- **Ownership**: User Workspace (`ReportStorage`)
- **Purpose**: Persists governance audit reports, budget usage summaries, optimization benchmark reports, and compliance matrices.
- **Read/Write Rules**: Written by `GovernanceEngine` and `OptimizationEngine`; read by CLI report tools (`oniroute optimize report`, `oniroute audit`).
- **Creation Policy**: Lazily created when audit or optimization reports are generated.
- **Persistence**: Permanent audit record.

### 2.9 `approvals/`
- **Ownership**: User Workspace (`GovernanceEngine`)
- **Purpose**: Stores human-in-the-loop approval requests, approval status tokens, and permission policy overrides.
- **Read/Write Rules**: Written when human verification is requested or granted; read during policy evaluation.
- **Creation Policy**: Lazily created when an approval event is logged.
- **Persistence**: Permanent governance security record.

### 2.10 `cache/`
- **Ownership**: User Workspace (`ContextEngine` / Optimization)
- **Purpose**: Stores workspace symbol indexes, AST caches, token count caches, and prompt optimization caches.
- **Read/Write Rules**: Read/Write during context building and prompt optimization to accelerate repeat invocations.
- **Creation Policy**: Lazily created on first cache store.
- **Persistence**: Re-buildable workspace cache.

### 2.11 `logs/`
- **Ownership**: User Workspace (`LogStorage`)
- **Purpose**: Stores diagnostic execution logs, framework runtime logs, and console output streams (`<execution_id>.log`).
- **Read/Write Rules**: Appended to during framework execution; read-only during debugging.
- **Creation Policy**: Lazily created when logging starts.
- **Persistence**: Permanent diagnostic log files.

### 2.12 `memory/`
- **Ownership**: User Workspace (`WorkspaceStorage` / Memory context)
- **Purpose**: Stores workspace-level contextual memory, semantic entity graphs, and long-term project summaries.
- **Read/Write Rules**: Updated during multi-step swarm executions; read during context assembly.
- **Creation Policy**: Lazily created on memory persistence.
- **Persistence**: Long-term persistent workspace memory.

### 2.13 `context/`
- **Ownership**: User Workspace (`ContextBuilder`)
- **Purpose**: Stores serialized context snapshots (`.json`) capturing exact context states passed to models.
- **Read/Write Rules**: Written prior to LLM invocation for inspectability and reproduction.
- **Creation Policy**: Lazily created when context inspection or logging is enabled.
- **Persistence**: Audit context snapshots.

### 2.14 `knowledge/`
- **Ownership**: User Workspace (`KnowledgeEngine`)
- **Purpose**: Holds project-specific domain knowledge rules, architectural guidelines, and local knowledge overrides.
- **Read/Write Rules**: Read during resolution; updated when local workspace knowledge is edited.
- **Creation Policy**: Lazily created when local knowledge is introduced.
- **Persistence**: Permanent project knowledge base.

### 2.15 `runtime/`
- **Ownership**: User Workspace (`WorkflowEngine`)
- **Purpose**: Stores active process PIDs, active execution locks, and live execution runtime state indicators.
- **Read/Write Rules**: Written during active execution; cleared on execution termination or workspace shutdown.
- **Creation Policy**: Lazily created during runtime startup.
- **Persistence**: Ephemeral active execution state.

### 2.16 `locks/`
- **Ownership**: User Workspace (`WorkspaceStorage`)
- **Purpose**: Stores file-based concurrency locks ensuring atomic multi-process access to workspace storage.
- **Read/Write Rules**: Created on acquiring lock; deleted on releasing lock.
- **Creation Policy**: Lazily created on concurrent lock requirement.
- **Persistence**: Ephemeral locking primitives.

---

## 3. Storage Introspection API Reference

The `WorkspaceStorage` class provides programmatically certified status methods:

```python
storage = WorkspaceStorage(workspace_metadata)

# Inspect all canonical directory names
names = storage.all_subdir_names

# Check existence of .oniroute/
exists = storage.exists()

# Map directory name -> existence boolean
status = storage.storage_status()

# Count entries in a specific subdirectory
count = storage.count_entries("history")

# Create all subdirectories lazily
paths = storage.ensure_all()
```
