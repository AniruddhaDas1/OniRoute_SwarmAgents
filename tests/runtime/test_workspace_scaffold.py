"""Tests for Workspace Scaffold Subsystem (Phase P4.G1)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.scaffold import (
    MANDATORY_DIRECTORIES,
    ScaffoldBoundaryViolation,
    ScaffoldValidationError,
    WorkspaceScaffoldEngine,
    WorkspaceScaffoldReport,
)
from runtime.swarm.models import (
    BudgetStatus,
    CheckpointStatus,
    EventBusReferences,
    ExecutionCursor,
    RuntimeExecutionSnapshot,
    StorageReferences,
    WorkspaceReferences,
    RetryStatus,
)


def create_sample_snapshot(
    tmp_path: Path,
    project_type: str = "python",
    exec_ctx: dict | None = None,
) -> RuntimeExecutionSnapshot:
    """Helper to create a deterministic RuntimeExecutionSnapshot for testing."""
    ws_root = str(tmp_path / "target_workspace")
    eng_root = str(tmp_path / "engine_root")

    Path(ws_root).mkdir(parents=True, exist_ok=True)
    Path(eng_root).mkdir(parents=True, exist_ok=True)

    return RuntimeExecutionSnapshot(
        snapshot_id="snap-test123456",
        mission_id="msn-test123456",
        deployment_plan_id="plan-test123456",
        execution_uuid="exec-uuid-test123456",
        execution_cursor=ExecutionCursor(
            current_wave_number=1,
            current_step_index=0,
            state="READY",
        ),
        execution_context=exec_ctx or {"technology_stack": project_type},
        budget_status=BudgetStatus(
            total_budget_usd=50.0,
            spent_budget_usd=0.0,
            remaining_budget_usd=50.0,
            is_exhausted=False,
        ),
        retry_status=RetryStatus(
            max_retries_per_step=3,
        ),
        checkpoint_status=CheckpointStatus(
            current_checkpoint_id="chk-init-001",
        ),
        event_bus_references=EventBusReferences(
            bus_id="bus-test123",
        ),
        storage_references=StorageReferences(
            workspace_root=ws_root,
            sessions_root=f"{ws_root}/.oniroute/sessions",
            traces_root=f"{ws_root}/.oniroute/traces",
            logs_root=f"{ws_root}/.oniroute/logs",
            history_root=f"{ws_root}/.oniroute/history",
            reports_root=f"{ws_root}/.oniroute/reports",
            artifacts_root=f"{ws_root}/.oniroute/artifacts",
        ),
        workspace_references=WorkspaceReferences(
            workspace_id="ws-test123",
            workspace_root=ws_root,
            engine_root=eng_root,
            is_engine_read_only=True,
            project_type=project_type,
        ),
        evidence={"validation": {"initialized": True}},
        timestamp="2026-08-06T00:00:00Z",
        snapshot_hash="a" * 64,
    )


def test_react_workspace_scaffold(tmp_path: Path):
    """Verify React workspace scaffold creates expected markers and structure."""
    snapshot = create_sample_snapshot(tmp_path, project_type="react")
    ws_path = Path(snapshot.workspace_references.workspace_root)
    engine = WorkspaceScaffoldEngine()

    report = engine.scaffold_workspace(snapshot)

    assert isinstance(report, WorkspaceScaffoldReport)
    assert report.technology_stack == "react"
    assert len(report.created_directories) == 10
    for d in MANDATORY_DIRECTORIES:
        assert (ws_path / d).is_dir()

    assert (ws_path / "package.json").is_file()
    assert (ws_path / "vite.config.js").is_file()
    assert (ws_path / "tsconfig.json").is_file()
    assert (ws_path / "eslint.config.js").is_file()
    assert (ws_path / ".gitignore").is_file()

    pkg_data = json.loads((ws_path / "package.json").read_text(encoding="utf-8"))
    assert "react" in pkg_data.get("dependencies", {})
    assert report.evidence["engine_safety_passed"] is True


def test_nextjs_workspace_scaffold(tmp_path: Path):
    """Verify Next.js workspace scaffold creates Next.js markers and configs."""
    snapshot = create_sample_snapshot(tmp_path, project_type="nextjs")
    ws_path = Path(snapshot.workspace_references.workspace_root)
    engine = WorkspaceScaffoldEngine()

    report = engine.scaffold_workspace(snapshot)

    assert isinstance(report, WorkspaceScaffoldReport)
    assert report.technology_stack == "nextjs"
    assert (ws_path / "next.config.mjs").is_file()
    assert (ws_path / "package.json").is_file()

    pkg_data = json.loads((ws_path / "package.json").read_text(encoding="utf-8"))
    assert "next" in pkg_data.get("dependencies", {})


def test_python_workspace_scaffold(tmp_path: Path):
    """Verify Python workspace scaffold creates pyproject.toml and pytest configs."""
    snapshot = create_sample_snapshot(tmp_path, project_type="python")
    ws_path = Path(snapshot.workspace_references.workspace_root)
    engine = WorkspaceScaffoldEngine()

    report = engine.scaffold_workspace(snapshot)

    assert isinstance(report, WorkspaceScaffoldReport)
    assert report.technology_stack == "python"
    assert (ws_path / "pyproject.toml").is_file()
    assert (ws_path / "requirements.txt").is_file()
    assert (ws_path / "pytest.ini").is_file()
    assert (ws_path / "ruff.toml").is_file()


def test_fastapi_workspace_scaffold(tmp_path: Path):
    """Verify FastAPI workspace scaffold includes FastAPI dependencies."""
    snapshot = create_sample_snapshot(tmp_path, project_type="fastapi")
    ws_path = Path(snapshot.workspace_references.workspace_root)
    engine = WorkspaceScaffoldEngine()

    report = engine.scaffold_workspace(snapshot)

    assert isinstance(report, WorkspaceScaffoldReport)
    assert report.technology_stack == "fastapi"
    assert (ws_path / "pyproject.toml").is_file()
    reqs_text = (ws_path / "requirements.txt").read_text(encoding="utf-8")
    assert "fastapi" in reqs_text.lower()


def test_flutter_workspace_scaffold(tmp_path: Path):
    """Verify Flutter workspace scaffold creates pubspec.yaml and analysis options."""
    snapshot = create_sample_snapshot(tmp_path, project_type="flutter")
    ws_path = Path(snapshot.workspace_references.workspace_root)
    engine = WorkspaceScaffoldEngine()

    report = engine.scaffold_workspace(snapshot)

    assert isinstance(report, WorkspaceScaffoldReport)
    assert report.technology_stack == "flutter"
    assert (ws_path / "pubspec.yaml").is_file()
    assert (ws_path / "analysis_options.yaml").is_file()


def test_monorepo_workspace_scaffold(tmp_path: Path):
    """Verify Monorepo workspace scaffold creates workspace configs."""
    snapshot = create_sample_snapshot(tmp_path, project_type="monorepo")
    ws_path = Path(snapshot.workspace_references.workspace_root)
    engine = WorkspaceScaffoldEngine()

    report = engine.scaffold_workspace(snapshot)

    assert isinstance(report, WorkspaceScaffoldReport)
    assert report.technology_stack == "monorepo"
    assert (ws_path / "pnpm-workspace.yaml").is_file()
    assert (ws_path / "package.json").is_file()
    assert (ws_path / "tsconfig.base.json").is_file()


def test_scaffold_regression_and_safety(tmp_path: Path):
    """Regression tests for input validation, immutability, safety, and collision handling."""
    engine = WorkspaceScaffoldEngine()

    # 1. Invalid input type raises ScaffoldValidationError
    with pytest.raises(ScaffoldValidationError):
        engine.scaffold_workspace("invalid_snapshot")  # type: ignore

    # 2. Immutable report contract test
    snapshot = create_sample_snapshot(tmp_path, project_type="python")
    report = engine.scaffold_workspace(snapshot)
    with pytest.raises((TypeError, Exception)):
        report.scaffold_id = "modified-id"  # type: ignore

    # 3. Collision handling: pre-existing user file is preserved
    ws_path = Path(snapshot.workspace_references.workspace_root)
    user_file = ws_path / "pyproject.toml"
    user_file.parent.mkdir(parents=True, exist_ok=True)
    user_file.write_text("# Pre-existing custom configuration\n", encoding="utf-8")

    report2 = engine.scaffold_workspace(snapshot)
    assert user_file.read_text(encoding="utf-8") == "# Pre-existing custom configuration\n"
    assert report2.configuration_summary.get("pyproject.toml") == "preserved_existing"

    # 4. Engine Root safety violation check
    eng_root = Path(snapshot.workspace_references.engine_root)
    with pytest.raises(ScaffoldBoundaryViolation):
        engine.scaffold_workspace(snapshot, workspace_override=eng_root)


def test_scaffold_cli(tmp_path: Path):
    """Verify oniroute scaffold CLI command execution."""
    runner = CliRunner()

    snapshot = create_sample_snapshot(tmp_path, project_type="python")
    snap_file = tmp_path / "snapshot.json"
    snap_file.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")

    target_ws = tmp_path / "cli_workspace"

    # Test rich text CLI output
    result = runner.invoke(
        app,
        ["scaffold", "--workspace", str(target_ws), "--snapshot", str(snap_file)],
    )
    assert result.exit_code == 0
    assert "Workspace Scaffold Complete" in result.output

    # Test JSON CLI output
    result_json = runner.invoke(
        app,
        ["scaffold", "--workspace", str(target_ws), "--snapshot", str(snap_file), "--json"],
    )
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert "scaffold_id" in json_data
    assert json_data["technology_stack"] == "python"
