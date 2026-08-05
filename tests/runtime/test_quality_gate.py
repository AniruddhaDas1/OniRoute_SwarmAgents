"""Tests for Quality Gate (Cross-Agent Review) Subsystem (Phase P5.E2)."""

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
from runtime.engineering import EngineeringWorkerEngine, EngineeringResult
from runtime.review import (
    QualityGateEngine,
    QualityReport,
    QualityFinding,
    ReviewValidationError,
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


def create_sample_engineering_results(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[EngineeringContractReport, List[EngineeringResult]]:
    """Helper to create deterministic EngineeringResults for testing."""
    ws_root = str(tmp_path / f"workspace_rev_{project_type}")
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
            workspace_id=f"ws-rev-{project_type}",
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

    worker_engine = EngineeringWorkerEngine()
    results = worker_engine.execute_all_contracts(contract_report)

    return contract_report, results


def test_architecture_review(tmp_path: Path):
    """Verify architecture review checks provider independence and read-only engine safety."""
    ctr_report, results = create_sample_engineering_results(tmp_path, project_type="python")
    gate_engine = QualityGateEngine()

    q_reports = gate_engine.review_all_results(results, ctr_report)

    assert len(q_reports) == len(results)
    for q in q_reports:
        assert isinstance(q, QualityReport)
        assert q.architecture_score >= 0.8
        assert "prf-lead-arch" in q.reviewer_profiles


def test_security_review(tmp_path: Path):
    """Verify security review checks secret scanning and path safety."""
    ctr_report, results = create_sample_engineering_results(tmp_path, project_type="python")
    gate_engine = QualityGateEngine()

    q_reports = gate_engine.review_all_results(results, ctr_report)

    for q in q_reports:
        assert q.security_score >= 0.8
        assert "prf-sec-auditor" in q.reviewer_profiles


def test_performance_review(tmp_path: Path):
    """Verify performance review audits latency and resource bounds."""
    ctr_report, results = create_sample_engineering_results(tmp_path, project_type="python")
    gate_engine = QualityGateEngine()

    q_reports = gate_engine.review_all_results(results, ctr_report)

    for q in q_reports:
        assert q.performance_score >= 0.8
        assert "prf-devops-eng" in q.reviewer_profiles


def test_documentation_review(tmp_path: Path):
    """Verify documentation review audits docstrings and README files."""
    ctr_report, results = create_sample_engineering_results(tmp_path, project_type="python")
    gate_engine = QualityGateEngine()

    q_reports = gate_engine.review_all_results(results, ctr_report)

    for q in q_reports:
        assert q.documentation_score >= 0.8
        assert "prf-doc-spec" in q.reviewer_profiles


def test_contract_compliance_review(tmp_path: Path):
    """Verify contract compliance audit checks produced artifacts against contracts."""
    ctr_report, results = create_sample_engineering_results(tmp_path, project_type="python")
    gate_engine = QualityGateEngine()

    q_reports = gate_engine.review_all_results(results, ctr_report)

    for q in q_reports:
        assert q.contract_compliance is True
        assert q.approval_status in ("APPROVED", "CONDITIONALLY_APPROVED")


def test_quality_gate_regression(tmp_path: Path):
    """Regression tests for invalid input validation, immutability, and zero workspace mutation."""
    gate_engine = QualityGateEngine()

    # 1. Invalid input validation test
    with pytest.raises(ReviewValidationError):
        gate_engine.review_result("invalid_result")  # type: ignore

    # 2. Immutability check
    ctr_report, results = create_sample_engineering_results(tmp_path, project_type="python")
    q_report = gate_engine.review_result(results[0])
    with pytest.raises((TypeError, Exception)):
        q_report.report_id = "modified-id"  # type: ignore

    # 3. Performance & Zero workspace mutation assertions
    assert q_report.evidence["zero_workspace_write"] is True
    assert q_report.evidence["latency_ms"] < 500.0
    assert q_report.report_hash != ""


def test_review_cli(tmp_path: Path):
    """Verify oniroute review CLI command execution."""
    runner = CliRunner()

    _, results = create_sample_engineering_results(tmp_path, project_type="python")
    res_file = tmp_path / "engineering_results.json"
    res_file.write_text(json.dumps([r.model_dump(mode="json") for r in results], indent=2), encoding="utf-8")

    # Test rich output CLI execution
    result = runner.invoke(app, ["review", "--result", str(res_file)])
    assert result.exit_code == 0
    assert "Quality Gate Review Complete" in result.output

    # Test JSON output CLI execution
    result_json = runner.invoke(app, ["review", "--result", str(res_file), "--json"])
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert isinstance(json_data, list)
    assert len(json_data) > 0
    assert "report_id" in json_data[0]
