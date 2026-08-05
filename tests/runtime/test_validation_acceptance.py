"""Tests for Validation & Acceptance Subsystem (Phase P5.E4)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.scaffold import WorkspaceScaffoldEngine
from runtime.blueprint import ProjectBlueprintEngine
from runtime.allocation import ImplementationAllocationEngine
from runtime.contracts import EngineeringContractEngine
from runtime.engineering import EngineeringWorkerEngine
from runtime.review import QualityGateEngine
from runtime.healing import RepairPlanner, SelfHealingEngine, UpdatedEngineeringResult
from runtime.validation import (
    VerificationEngine,
    AcceptanceEngine,
    VerificationResult,
    AcceptanceReport,
    VerificationExecutionError,
    AcceptanceEvaluationError,
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


def create_sample_updated_results(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[str, List[UpdatedEngineeringResult]]:
    """Helper to create deterministic UpdatedEngineeringResults for testing."""
    ws_root = str(tmp_path / f"workspace_val_{project_type}")
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
            workspace_id=f"ws-val-{project_type}",
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

    gate_engine = QualityGateEngine()
    q_reports = gate_engine.review_all_results(results, contract_report)

    planner = RepairPlanner()
    healing_engine = SelfHealingEngine()

    updated_results: List[UpdatedEngineeringResult] = []
    result_map = {r.result_id: r for r in results}
    for q_rep in q_reports:
        repair_plan = planner.create_repair_plan(q_rep)
        orig_res = result_map.get(q_rep.engineering_result_id, results[0])
        upd_res = healing_engine.apply_repairs(repair_plan, orig_res, ws_root)
        updated_results.append(upd_res)

    return ws_root, updated_results


def test_verification_engine(tmp_path: Path):
    """Verify VerificationEngine executes build, test, and security checks."""
    ws_root, updated_results = create_sample_updated_results(tmp_path, project_type="python")
    vrf_engine = VerificationEngine()

    verifications = vrf_engine.verify_all_results(updated_results, ws_root)

    assert len(verifications) == len(updated_results)
    for v in verifications:
        assert isinstance(v, VerificationResult)
        assert v.build_status == "PASSED"
        assert v.test_status == "PASSED"
        assert v.coverage_percentage >= 80.0
        assert v.security_status == "PASSED"
        assert len(v.executed_checks) == 11


def test_acceptance_engine(tmp_path: Path):
    """Verify AcceptanceEngine evaluates criteria, mission status, and production readiness."""
    ws_root, updated_results = create_sample_updated_results(tmp_path, project_type="python")
    vrf_engine = VerificationEngine()
    acpt_engine = AcceptanceEngine()

    verifications = vrf_engine.verify_all_results(updated_results, ws_root)
    acceptances = acpt_engine.evaluate_all_acceptances(verifications)

    assert len(acceptances) == len(verifications)
    for a in acceptances:
        assert isinstance(a, AcceptanceReport)
        assert a.production_ready is True
        assert a.mission_status == "SUCCESS"
        assert a.acceptance_verdict == "ACCEPTED"
        assert len(a.accepted_criteria) == 7
        assert len(a.rejected_criteria) == 0


def test_validation_acceptance_regression(tmp_path: Path):
    """Regression tests for invalid input validation, frozen immutability, and zero workspace write."""
    vrf_engine = VerificationEngine()
    acpt_engine = AcceptanceEngine()

    # 1. Invalid input check
    with pytest.raises(VerificationExecutionError):
        vrf_engine.verify_result("invalid_input", str(tmp_path))  # type: ignore

    with pytest.raises(AcceptanceEvaluationError):
        acpt_engine.evaluate_acceptance("invalid_input")  # type: ignore

    # 2. Immutability check
    ws_root, updated_results = create_sample_updated_results(tmp_path, project_type="python")
    vrf = vrf_engine.verify_result(updated_results[0], ws_root)
    with pytest.raises((TypeError, Exception)):
        vrf.verification_id = "modified-id"  # type: ignore

    acpt = acpt_engine.evaluate_acceptance(vrf)
    with pytest.raises((TypeError, Exception)):
        acpt.acceptance_id = "modified-id"  # type: ignore

    # 3. Performance & zero workspace write assertions
    assert vrf.evidence["zero_workspace_write"] is True
    assert acpt.evidence["zero_workspace_write"] is True
    assert vrf.evidence["latency_ms"] < 500.0
    assert acpt.evidence["latency_ms"] < 500.0


def test_validate_and_accept_cli(tmp_path: Path):
    """Verify oniroute validate and oniroute accept CLI commands."""
    runner = CliRunner()

    ws_root, updated_results = create_sample_updated_results(tmp_path, project_type="python")
    res_file = tmp_path / "updated_results.json"
    res_file.write_text(json.dumps([u.model_dump(mode="json") for u in updated_results], indent=2), encoding="utf-8")

    # Test oniroute validate
    val_result = runner.invoke(app, ["validate", "--result", str(res_file), "--workspace", ws_root])
    assert val_result.exit_code == 0
    assert "Verification Execution Complete" in val_result.output

    # Test oniroute validate --json
    val_json_result = runner.invoke(app, ["validate", "--result", str(res_file), "--workspace", ws_root, "--json"])
    assert val_json_result.exit_code == 0
    vrf_data = json.loads(val_json_result.output)
    assert isinstance(vrf_data, list)
    assert len(vrf_data) > 0

    vrf_file = tmp_path / "verifications.json"
    vrf_file.write_text(val_json_result.output, encoding="utf-8")

    # Test oniroute accept
    acpt_result = runner.invoke(app, ["accept", "--verification", str(vrf_file), "--workspace", ws_root])
    assert acpt_result.exit_code == 0
    assert "Acceptance Evaluation Complete" in acpt_result.output

    # Test oniroute accept --json
    acpt_json_result = runner.invoke(app, ["accept", "--verification", str(vrf_file), "--workspace", ws_root, "--json"])
    assert acpt_json_result.exit_code == 0
    acpt_data = json.loads(acpt_json_result.output)
    assert isinstance(acpt_data, list)
    assert len(acpt_data) > 0
    assert acpt_data[0]["acceptance_verdict"] == "ACCEPTED"
