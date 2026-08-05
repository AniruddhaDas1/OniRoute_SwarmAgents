# Workspace CLI Reference (`docs/WORKSPACE_CLI.md`)

## Executive Summary

The OniRoute CLI provides comprehensive workspace discovery, integrity diagnostics, execution history inspection, trace event viewing, and report auditing commands.

All workspace CLI commands accept the global `--workspace <path>` (`-w`) flag to explicitly override the target workspace path.

---

## 1. Primary Commands

### 1.1 `oniroute workspace`
Discovers and displays active workspace metadata, detected project framework, discovery method, and detailed `.oniroute/` storage status tables.

```bash
oniroute workspace [--workspace /path/to/target]
```

**Displayed Sections**:
1. **Workspace Discovery Table**:
   - `Workspace Root`: Absolute path to workspace root.
   - `Engine Root`: Absolute path to read-only engine root.
   - `Project Type`: Detected project framework (e.g. `PYTHON`, `NEXTJS`).
   - `Discovery Method`: Priority level used (`explicit_argument`, `current_working_directory`, etc.).
   - `Validation Status`: Workspace validity (`VALID`, `INVALID`).
2. **Workspace Storage Summary**:
   - Counts for sessions, artifacts, history, traces, logs.
   - `Storage Initialized`: `YES` / `NO`.
3. **Storage Directory Detail**:
   - Table detailing existence and entry counts for all 16 canonical `.oniroute/` subdirectories.
4. **Runtime Statistics**:
   - Counts for plans, reports, memory, context, runtime files, knowledge, cache, approvals, locks.

---

### 1.2 `oniroute doctor`
Performs comprehensive diagnostic health checks across the target repository and active workspace context.

```bash
oniroute doctor [--workspace /path/to/target]
```

**Displayed Sections**:
- `Workspace`: Workspace root path.
- `Engine`: Engine root path.
- `Project`: Framework type and project name.
- `Workspace Status`: Health status.
- `Read-only Engine`: `CONFIRMED` / `FAILED` assertion output.
- Repository metadata records count and validation report status.

---

### 1.3 `oniroute history`
Inspects persisted execution history records from the workspace `.oniroute/history/` directory.

```bash
oniroute history [--workspace /path/to/target]
```

**Output Table**:
- `Execution`: Execution ID (`exec-<timestamp>`).
- `Workflow`: Executed workflow ID.
- `Status`: Execution outcome (`completed`, `failed`).

---

### 1.4 `oniroute events` (Traces)
Views execution event streams persisted inside `.oniroute/traces/`.

```bash
oniroute events [--workspace /path/to/target]
```

**Output Table**:
- `Type`: Event type (e.g., `step_started`, `tool_invoked`).
- `Execution`: Associated execution ID.
- `Subject`: Subject identifier (agent/skill/step ID).

---

### 1.5 `oniroute optimize report`
Inspects optimization benchmark and trace reports persisted in `.oniroute/reports/`.

```bash
oniroute optimize report [--workspace /path/to/target]
```

**Output**: JSON payload detailing execution count, optimization records count, and trace array.

---

### 1.6 `oniroute audit`
Inspects governance policy audit records persisted in `.oniroute/reports/governance/`.

```bash
oniroute audit [--workspace /path/to/target]
```

**Output**: JSON array of governance audit records.

---

## 2. Global CLI Flags

| Flag | Short | Description | Example |
|---|---|---|---|
| `--workspace PATH` | `-w` | Explicitly targets a specific Workspace Root | `oniroute --workspace /tmp/my-project workspace` |
| `--repository-root PATH` | N/A | Sets explicit engine framework root path | `oniroute --repository-root /opt/oniroute doctor` |

---

## 3. Example CLI Usage Scenarios

```bash
# Diagnostic workspace audit of current directory
oniroute workspace

# Target an external project directory for inspection
oniroute --workspace ~/projects/saas-app doctor

# Review past workflow executions in the workspace
oniroute history

# Review fine-grained event traces
oniroute events
```
