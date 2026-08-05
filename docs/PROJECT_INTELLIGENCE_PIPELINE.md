# Project Intelligence Pipeline Specification

## 1. Pipeline Overview
The Project Intelligence pipeline is a sequential 4-stage processing pipeline that operates prior to Mission Intake and Swarm Orchestration.

```
Input Request -> Stage 1 -> Stage 2 -> Stage 3 -> Stage 4 -> Mission Intake
```

---

## 2. Stage Details

### Stage 1: Intent Analysis Engine (Phase P1.I1)
- **Module**: `runtime/intent/analyzer.py`
- **Input**: `raw_prompt: str`, `explicit_workspace: Path | None`
- **Output**: `IntentReport`
- **Responsibilities**:
  - Normalizes raw input request using `MissionNormalizer`.
  - Matches 22 canonical project categories (e.g. `Website`, `REST API`, `CRM`, `AI Agent`, `Mobile App`).
  - Extracts technology stack, authentication providers, database engines, and cloud platforms using regex token matching.
  - Computes intent confidence score ($0.0 - 1.0$).

### Stage 2: Workspace Intelligence (Phase P1.I2)
- **Module**: `runtime/workspace/intelligence.py`
- **Input**: `cwd: Path`, `explicit_workspace: Path | None`
- **Output**: `WorkspaceContext`
- **Responsibilities**:
  - Resolves `workspace_root`, `repository_root`, and `engine_root`.
  - Detects manifest files (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.).
  - Classifies workspace operational state (`EMPTY`, `NEW_PROJECT`, `EXISTING_PROJECT`, `MONOREPO`, `UNKNOWN`).
  - Validates read-only engine safety boundaries.

### Stage 3: Repository Intelligence (Phase P1.I3)
- **Module**: `runtime/workspace/repository.py`
- **Input**: `workspace_context: WorkspaceContext`
- **Output**: `RepositoryContext`
- **Responsibilities**:
  - Scans directory tree while pruning ignored paths (`node_modules`, `.venv`, `.git`, `dist`, `build`, etc.).
  - Maps top-level directory topology and layout patterns (`src_layout`, `flat_layout`, `monorepo`).
  - Detects specialized directory roots (`source_root`, `test_root`, `config_root`, `doc_root`, `api_root`, `component_root`).
  - Identifies entry points (`main.py`, `index.ts`, `main.go`, `Program.cs`, `next.config.js`, `Dockerfile`).
  - Classifies files and summarizes test presence, assets, and infrastructure.

### Stage 4: Engineering Execution Plan (Phase P1.I4)
- **Module**: `runtime/workspace/plan.py`
- **Input**: `intent_report: IntentReport`, `workspace_context: WorkspaceContext`, `repository_context: RepositoryContext`
- **Output**: `EngineeringExecutionPlan`
- **Responsibilities**:
  - Resolves single repository modification strategy (`NEW_PROJECT`, `EXTEND_EXISTING`, `FEATURE_ADDITION`, `BUG_FIX`, `REFACTOR_EXISTING`, `DOCUMENTATION`, `UNKNOWN`).
  - Detects required engineering disciplines (`Frontend`, `Backend`, `Database`, `DevOps`, `Security`, `QA`, `Documentation`, `Mobile`, `AI`).
  - Plans deliverables across 5 high-level milestone stages.
  - Identifies architectural risks, missing information, and success criteria.

---

## 3. Data Integrity & Downstream Handoff
Once generated, the `EngineeringExecutionPlan` (along with `intent_report`, `workspace_context`, and `repository_context`) is attached to `MissionIntake.process_intake()` via the `parameters` dictionary:

```python
mission_request = intake.process_intake(
    raw_prompt,
    explicit_workspace=explicit_ws,
    parameters={
        "intent_report": intent_report.model_dump(mode="json"),
        "workspace_context": ws_context.model_dump(mode="json"),
        "repository_context": repo_context.model_dump(mode="json"),
        "engineering_execution_plan": exec_plan.model_dump(mode="json"),
    },
)
```
This payload is preserved down through `MissionResolver`, `MissionOrchestrator`, and `ExecutionRequest`, enabling downstream Organization and Skill Intelligence layers to consume structured plan data cleanly.
