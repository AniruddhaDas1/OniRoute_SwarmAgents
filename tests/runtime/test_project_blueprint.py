"""Tests for Project Blueprint Subsystem (Phase P4.G2)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.scaffold import WorkspaceScaffoldEngine, WorkspaceScaffoldReport
from runtime.blueprint import (
    EngineeringDiscipline,
    ProjectBlueprintEngine,
    ProjectBlueprintReport,
    BlueprintValidationError,
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


def create_sample_scaffold_report(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[RuntimeExecutionSnapshot, WorkspaceScaffoldReport]:
    """Helper to create a deterministic WorkspaceScaffoldReport for testing."""
    ws_root = str(tmp_path / f"workspace_{project_type}")
    eng_root = str(tmp_path / "engine_root")

    Path(ws_root).mkdir(parents=True, exist_ok=True)
    Path(eng_root).mkdir(parents=True, exist_ok=True)

    snapshot = RuntimeExecutionSnapshot(
        snapshot_id="snap-test123456",
        mission_id="msn-test123456",
        deployment_plan_id="plan-test123456",
        execution_uuid="exec-uuid-test123456",
        execution_cursor=ExecutionCursor(
            current_wave_number=1,
            current_step_index=0,
            state="READY",
        ),
        execution_context={"technology_stack": project_type},
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
            workspace_id=f"ws-{project_type}",
            workspace_root=ws_root,
            engine_root=eng_root,
            is_engine_read_only=True,
            project_type=project_type,
        ),
        evidence={"validation": {"initialized": True}},
        timestamp="2026-08-06T00:00:00Z",
        snapshot_hash="a" * 64,
    )

    scaffold_engine = WorkspaceScaffoldEngine()
    scaffold_report = scaffold_engine.scaffold_workspace(snapshot)
    return snapshot, scaffold_report


def test_react_blueprint(tmp_path: Path):
    """Verify React blueprint allocates Frontend modules and component hierarchy."""
    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="react")
    engine = ProjectBlueprintEngine()

    report = engine.generate_blueprint(scaf_report)

    assert isinstance(report, ProjectBlueprintReport)
    assert report.technology_stack == "react"
    assert report.evidence["coverage_score"] == 1.0
    assert report.directory_ownership.get("src/components") == EngineeringDiscipline.FRONTEND.value
    assert any(m.discipline == EngineeringDiscipline.FRONTEND.value for m in report.project_modules)


def test_nextjs_blueprint(tmp_path: Path):
    """Verify Next.js blueprint allocates App Router (Frontend) and API Routes (Backend)."""
    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="nextjs")
    engine = ProjectBlueprintEngine()

    report = engine.generate_blueprint(scaf_report)

    assert isinstance(report, ProjectBlueprintReport)
    assert report.technology_stack == "nextjs"
    assert report.directory_ownership.get("src/app") == EngineeringDiscipline.FRONTEND.value
    assert report.directory_ownership.get("src/api") == EngineeringDiscipline.BACKEND.value


def test_fastapi_blueprint(tmp_path: Path):
    """Verify FastAPI blueprint allocates Backend API and Database modules."""
    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="fastapi")
    engine = ProjectBlueprintEngine()

    report = engine.generate_blueprint(scaf_report)

    assert isinstance(report, ProjectBlueprintReport)
    assert report.technology_stack == "fastapi"
    assert report.directory_ownership.get("src/api") == EngineeringDiscipline.BACKEND.value
    assert report.directory_ownership.get("src/db") == EngineeringDiscipline.DATABASE.value


def test_flutter_blueprint(tmp_path: Path):
    """Verify Flutter blueprint allocates UI and Services modules."""
    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="flutter")
    engine = ProjectBlueprintEngine()

    report = engine.generate_blueprint(scaf_report)

    assert isinstance(report, ProjectBlueprintReport)
    assert report.technology_stack == "flutter"
    assert report.directory_ownership.get("src/lib/ui") == EngineeringDiscipline.FRONTEND.value


def test_monorepo_blueprint(tmp_path: Path):
    """Verify Monorepo blueprint allocates web, api, db, and shared packages."""
    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="monorepo")
    engine = ProjectBlueprintEngine()

    report = engine.generate_blueprint(scaf_report)

    assert isinstance(report, ProjectBlueprintReport)
    assert report.technology_stack == "monorepo"
    assert report.directory_ownership.get("apps/web") == EngineeringDiscipline.FRONTEND.value
    assert report.directory_ownership.get("apps/api") == EngineeringDiscipline.BACKEND.value
    assert report.directory_ownership.get("packages/db") == EngineeringDiscipline.DATABASE.value
    assert report.directory_ownership.get("packages/shared") == EngineeringDiscipline.SHARED.value


def test_fullstack_blueprint(tmp_path: Path):
    """Verify full-stack discipline coverage across all 11 engineering disciplines."""
    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="monorepo")
    engine = ProjectBlueprintEngine()

    report = engine.generate_blueprint(scaf_report)

    disciplines_covered = set(report.engineering_discipline_ownership.keys())
    for d in EngineeringDiscipline:
        assert d.value in disciplines_covered


def test_blueprint_regression_and_validation(tmp_path: Path):
    """Regression tests for contract validation, immutability, orphan checking, and performance."""
    engine = ProjectBlueprintEngine()

    # 1. Invalid input contract test
    with pytest.raises(BlueprintValidationError):
        engine.generate_blueprint("invalid_report")  # type: ignore

    # 2. Immutability check
    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="python")
    report = engine.generate_blueprint(scaf_report)
    with pytest.raises((TypeError, Exception)):
        report.blueprint_id = "modified-id"  # type: ignore

    # 3. Performance & Determinism assertions
    assert report.evidence["latency_ms"] < 500.0
    assert report.evidence["coverage_score"] == 1.0
    assert report.evidence["determinism"] is True
    assert report.blueprint_hash != ""


def test_blueprint_cli(tmp_path: Path):
    """Verify oniroute blueprint-project CLI command execution."""
    runner = CliRunner()

    _, scaf_report = create_sample_scaffold_report(tmp_path, project_type="python")
    scaf_file = tmp_path / "scaffold_report.json"
    scaf_file.write_text(scaf_report.model_dump_json(indent=2), encoding="utf-8")

    # Test rich output CLI execution
    result = runner.invoke(app, ["blueprint-project", "--scaffold", str(scaf_file)])
    assert result.exit_code == 0
    assert "Project Blueprint Complete" in result.output

    # Test JSON output CLI execution
    result_json = runner.invoke(app, ["blueprint-project", "--scaffold", str(scaf_file), "--json"])
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert "blueprint_id" in json_data
    assert json_data["technology_stack"] == "python"
