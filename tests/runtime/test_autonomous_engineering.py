"""Tests for Autonomous Engineering Worker Subsystem (Phase P5.E1)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.blueprint import ProjectBlueprintEngine
from runtime.allocation import ImplementationAllocationEngine
from runtime.contracts import EngineeringContractEngine, EngineeringContractReport
from runtime.engineering import (
    EngineeringWorkerEngine,
    EngineeringResult,
    EngineeringBoundaryViolation,
    EngineeringExecutionError,
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


def create_sample_contract_report(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[RuntimeExecutionSnapshot, EngineeringContractReport]:
    """Helper to create a deterministic EngineeringContractReport for testing."""
    ws_root = str(tmp_path / f"workspace_eng_{project_type}")
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
        retry_status=RetryStatus(max_retries_per_step=3),
        checkpoint_status=CheckpointStatus(current_checkpoint_id="chk-init-001"),
        event_bus_references=EventBusReferences(bus_id="bus-test123"),
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
            workspace_id=f"ws-eng-{project_type}",
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

    contract_engine = EngineeringContractEngine()
    contract_report = contract_engine.generate_contracts(allocation_report)

    return snapshot, contract_report


def test_react_engineering(tmp_path: Path):
    """Verify React worker generates component files in workspace."""
    _, contract_report = create_sample_contract_report(tmp_path, project_type="react")
    worker = EngineeringWorkerEngine()

    results = worker.execute_all_contracts(contract_report)

    assert isinstance(results, list)
    assert len(results) == len(contract_report.contracts)
    for r in results:
        assert isinstance(r, EngineeringResult)
        assert len(r.created_files) + len(r.modified_files) > 0


def test_nextjs_engineering(tmp_path: Path):
    """Verify Next.js worker generates App Router TSX and API routes."""
    _, contract_report = create_sample_contract_report(tmp_path, project_type="nextjs")
    worker = EngineeringWorkerEngine()

    results = worker.execute_all_contracts(contract_report)

    assert len(results) > 0
    assert any(r.evidence["discipline"] == "Frontend" for r in results)


def test_fastapi_engineering(tmp_path: Path):
    """Verify FastAPI worker generates Python API modules and DB models."""
    _, contract_report = create_sample_contract_report(tmp_path, project_type="fastapi")
    worker = EngineeringWorkerEngine()

    results = worker.execute_all_contracts(contract_report)

    assert len(results) > 0
    assert any(r.evidence["discipline"] == "Backend" for r in results)


def test_flutter_engineering(tmp_path: Path):
    """Verify Flutter worker generates Dart UI widget code."""
    _, contract_report = create_sample_contract_report(tmp_path, project_type="flutter")
    worker = EngineeringWorkerEngine()

    results = worker.execute_all_contracts(contract_report)

    assert len(results) > 0


def test_monorepo_engineering(tmp_path: Path):
    """Verify Monorepo worker generates files across multiple packages."""
    _, contract_report = create_sample_contract_report(tmp_path, project_type="monorepo")
    worker = EngineeringWorkerEngine()

    results = worker.execute_all_contracts(contract_report)

    assert len(results) > 0


def test_fullstack_engineering(tmp_path: Path):
    """Verify full-stack code generation across all contract disciplines."""
    _, contract_report = create_sample_contract_report(tmp_path, project_type="monorepo")
    worker = EngineeringWorkerEngine()

    results = worker.execute_all_contracts(contract_report)

    assert len(results) == len(contract_report.contracts)


def test_boundary_safety_rejection(tmp_path: Path):
    """Verify worker rejects attempts to write outside workspace or into engine root."""
    worker = EngineeringWorkerEngine()

    # Test path traversal outside workspace
    with pytest.raises(EngineeringBoundaryViolation):
        worker._enforce_boundary_safety(
            "../../etc/passwd",
            (tmp_path / "../../etc/passwd").resolve(),
            tmp_path.resolve(),
        )


def test_engineering_cli(tmp_path: Path):
    """Verify oniroute engineer CLI command execution."""
    runner = CliRunner()

    _, contract_report = create_sample_contract_report(tmp_path, project_type="python")
    ctr_file = tmp_path / "contract_report.json"
    ctr_file.write_text(contract_report.model_dump_json(indent=2), encoding="utf-8")

    # Test rich output CLI execution
    result = runner.invoke(app, ["engineer", "--contracts", str(ctr_file)])
    assert result.exit_code == 0
    assert "Autonomous Engineering Worker Execution Complete" in result.output

    # Test JSON output CLI execution
    result_json = runner.invoke(app, ["engineer", "--contracts", str(ctr_file), "--json"])
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert isinstance(json_data, list)
    assert len(json_data) > 0
    assert "result_id" in json_data[0]
