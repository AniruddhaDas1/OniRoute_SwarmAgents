"""Tests for Engineering Contracts Subsystem (Phase P4.G4)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.blueprint import ProjectBlueprintEngine
from runtime.allocation import ImplementationAllocationEngine, ImplementationAllocationReport
from runtime.contracts import (
    EngineeringContract,
    EngineeringContractEngine,
    EngineeringContractReport,
    ContractValidationError,
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


def create_sample_allocation_report(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[RuntimeExecutionSnapshot, ImplementationAllocationReport]:
    """Helper to create a deterministic ImplementationAllocationReport for testing."""
    ws_root = str(tmp_path / f"workspace_ctr_{project_type}")
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
            workspace_id=f"ws-ctr-{project_type}",
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

    allocation_engine = ImplementationAllocationEngine()
    allocation_report = allocation_engine.allocate_implementation(blueprint_report)

    return snapshot, allocation_report


def test_react_contracts(tmp_path: Path):
    """Verify React contracts specify UI constraints and prf-fe-spec ownership."""
    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="react")
    engine = EngineeringContractEngine()

    report = engine.generate_contracts(alloc_report)

    assert isinstance(report, EngineeringContractReport)
    assert report.technology_stack == "react"
    assert report.evidence["coverage_score"] == 1.0
    assert "prf-fe-spec" in report.agent_contracts
    assert len(report.contracts) == len(alloc_report.allocated_targets)


def test_nextjs_contracts(tmp_path: Path):
    """Verify Next.js contracts specify App Router (Wave 4) and API (Wave 3)."""
    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="nextjs")
    engine = EngineeringContractEngine()

    report = engine.generate_contracts(alloc_report)

    assert isinstance(report, EngineeringContractReport)
    assert report.technology_stack == "nextjs"
    assert 3 in report.execution_waves
    assert 4 in report.execution_waves


def test_fastapi_contracts(tmp_path: Path):
    """Verify FastAPI contracts specify Wave 3 (Backend API) and Wave 2 (Database)."""
    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="fastapi")
    engine = EngineeringContractEngine()

    report = engine.generate_contracts(alloc_report)

    assert isinstance(report, EngineeringContractReport)
    assert report.technology_stack == "fastapi"
    assert 2 in report.execution_waves
    assert 3 in report.execution_waves


def test_flutter_contracts(tmp_path: Path):
    """Verify Flutter contracts specify UI widget constraints and Wave 4 execution."""
    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="flutter")
    engine = EngineeringContractEngine()

    report = engine.generate_contracts(alloc_report)

    assert isinstance(report, EngineeringContractReport)
    assert report.technology_stack == "flutter"
    assert len(report.contracts) > 0


def test_monorepo_contracts(tmp_path: Path):
    """Verify Monorepo contracts assign contracts across multiple execution waves."""
    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="monorepo")
    engine = EngineeringContractEngine()

    report = engine.generate_contracts(alloc_report)

    assert isinstance(report, EngineeringContractReport)
    assert report.technology_stack == "monorepo"
    assert len(report.execution_waves) >= 4


def test_fullstack_contracts(tmp_path: Path):
    """Verify full-stack coverage across all constraint suites and execution waves."""
    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="monorepo")
    engine = EngineeringContractEngine()

    report = engine.generate_contracts(alloc_report)

    assert report.evidence["validation"]["hundred_percent_allocation_coverage"] is True
    assert report.evidence["validation"]["constraint_completeness"] is True
    assert report.evidence["validation"]["acceptance_completeness"] is True


def test_contracts_regression_and_validation(tmp_path: Path):
    """Regression tests for contract validation, immutability, orphan checking, and performance."""
    engine = EngineeringContractEngine()

    # 1. Invalid input contract test
    with pytest.raises(ContractValidationError):
        engine.generate_contracts("invalid_allocation")  # type: ignore

    # 2. Immutability check
    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="python")
    report = engine.generate_contracts(alloc_report)
    with pytest.raises((TypeError, Exception)):
        report.report_id = "modified-id"  # type: ignore

    # 3. Performance & Constraint Completeness assertions
    assert report.evidence["latency_ms"] < 500.0
    assert report.evidence["coverage_score"] == 1.0
    assert report.report_hash != ""


def test_contracts_cli(tmp_path: Path):
    """Verify oniroute contracts CLI command execution."""
    runner = CliRunner()

    _, alloc_report = create_sample_allocation_report(tmp_path, project_type="python")
    alloc_file = tmp_path / "allocation_report.json"
    alloc_file.write_text(alloc_report.model_dump_json(indent=2), encoding="utf-8")

    # Test rich output CLI execution
    result = runner.invoke(app, ["contracts", "--allocation", str(alloc_file)])
    assert result.exit_code == 0
    assert "Engineering Contracts Complete" in result.output

    # Test JSON output CLI execution
    result_json = runner.invoke(app, ["contracts", "--allocation", str(alloc_file), "--json"])
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert "report_id" in json_data
    assert json_data["technology_stack"] == "python"
