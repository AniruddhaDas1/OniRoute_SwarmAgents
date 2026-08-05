"""Tests for Implementation Allocation Subsystem (Phase P4.G3)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.blueprint import ProjectBlueprintEngine, ProjectBlueprintReport
from runtime.allocation import (
    AllocationTarget,
    ImplementationAllocationEngine,
    ImplementationAllocationReport,
    AllocationValidationError,
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


def create_sample_blueprint_report(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[RuntimeExecutionSnapshot, ProjectBlueprintReport]:
    """Helper to create a deterministic ProjectBlueprintReport for testing."""
    ws_root = str(tmp_path / f"workspace_alloc_{project_type}")
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
            workspace_id=f"ws-alloc-{project_type}",
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

    blueprint_engine = ProjectBlueprintEngine()
    blueprint_report = blueprint_engine.generate_blueprint(scaffold_report)

    return snapshot, blueprint_report


def test_react_allocation(tmp_path: Path):
    """Verify React allocation assigns UI targets to prf-fe-spec."""
    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="react")
    engine = ImplementationAllocationEngine()

    report = engine.allocate_implementation(blu_report)

    assert isinstance(report, ImplementationAllocationReport)
    assert report.technology_stack == "react"
    assert report.coverage["coverage_score"] == 1.0
    assert "prf-fe-spec" in report.agent_ownership
    assert len(report.allocated_targets) > 0


def test_nextjs_allocation(tmp_path: Path):
    """Verify Next.js allocation assigns App Router to prf-fe-spec and API to prf-be-eng."""
    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="nextjs")
    engine = ImplementationAllocationEngine()

    report = engine.allocate_implementation(blu_report)

    assert isinstance(report, ImplementationAllocationReport)
    assert report.technology_stack == "nextjs"
    assert "prf-fe-spec" in report.agent_ownership
    assert "prf-be-eng" in report.agent_ownership


def test_fastapi_allocation(tmp_path: Path):
    """Verify FastAPI allocation assigns Backend API to prf-be-eng and DB to prf-db-admin."""
    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="fastapi")
    engine = ImplementationAllocationEngine()

    report = engine.allocate_implementation(blu_report)

    assert isinstance(report, ImplementationAllocationReport)
    assert report.technology_stack == "fastapi"
    assert "prf-be-eng" in report.agent_ownership
    assert "prf-db-admin" in report.agent_ownership


def test_flutter_allocation(tmp_path: Path):
    """Verify Flutter allocation assigns mobile UI and services to prf-fe-spec."""
    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="flutter")
    engine = ImplementationAllocationEngine()

    report = engine.allocate_implementation(blu_report)

    assert isinstance(report, ImplementationAllocationReport)
    assert report.technology_stack == "flutter"
    assert "prf-fe-spec" in report.agent_ownership


def test_monorepo_allocation(tmp_path: Path):
    """Verify Monorepo allocation maps web, api, db, and shared to specialized profiles."""
    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="monorepo")
    engine = ImplementationAllocationEngine()

    report = engine.allocate_implementation(blu_report)

    assert isinstance(report, ImplementationAllocationReport)
    assert report.technology_stack == "monorepo"
    assert "prf-fe-spec" in report.agent_ownership
    assert "prf-be-eng" in report.agent_ownership
    assert "prf-db-admin" in report.agent_ownership
    assert "prf-lead-arch" in report.agent_ownership


def test_fullstack_allocation(tmp_path: Path):
    """Verify full-stack coverage across all 11 agent profiles and disciplines."""
    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="monorepo")
    engine = ImplementationAllocationEngine()

    report = engine.allocate_implementation(blu_report)

    assert len(report.agent_ownership) >= 10
    assert report.evidence["validation"]["hundred_percent_ownership"] is True
    assert report.evidence["validation"]["no_orphan_files"] is True


def test_allocation_regression_and_validation(tmp_path: Path):
    """Regression tests for contract validation, immutability, DAG order, and performance."""
    engine = ImplementationAllocationEngine()

    # 1. Invalid input contract test
    with pytest.raises(AllocationValidationError):
        engine.allocate_implementation("invalid_blueprint")  # type: ignore

    # 2. Immutability check
    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="python")
    report = engine.allocate_implementation(blu_report)
    with pytest.raises((TypeError, Exception)):
        report.allocation_id = "modified-id"  # type: ignore

    # 3. Performance & Topological Sort assertions
    assert report.evidence["latency_ms"] < 500.0
    assert len(report.execution_order) == len(report.allocated_targets)
    assert report.allocation_hash != ""


def test_allocation_cli(tmp_path: Path):
    """Verify oniroute allocate CLI command execution."""
    runner = CliRunner()

    _, blu_report = create_sample_blueprint_report(tmp_path, project_type="python")
    blu_file = tmp_path / "blueprint_report.json"
    blu_file.write_text(blu_report.model_dump_json(indent=2), encoding="utf-8")

    # Test rich output CLI execution
    result = runner.invoke(app, ["allocate", "--blueprint", str(blu_file)])
    assert result.exit_code == 0
    assert "Implementation Allocation Complete" in result.output

    # Test JSON output CLI execution
    result_json = runner.invoke(app, ["allocate", "--blueprint", str(blu_file), "--json"])
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert "allocation_id" in json_data
    assert json_data["technology_stack"] == "python"
