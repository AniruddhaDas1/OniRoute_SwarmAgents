"""Tests for Autonomous Engineering Certification & Freeze Subsystem (Phase P5.E5)."""

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
from runtime.engineering import EngineeringWorkerEngine, AutonomousEngineeringCertificationEngine, EngineeringCertificationReport
from runtime.review import QualityGateEngine
from runtime.healing import RepairPlanner, SelfHealingEngine, UpdatedEngineeringResult
from runtime.validation import VerificationEngine, AcceptanceEngine
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


def create_full_pipeline_artifacts(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[str, Any, Any, Any, Any, Any, Any]:
    """Helper to run end-to-end P5 pipeline and return all immutable stage artifacts."""
    ws_root = str(tmp_path / f"workspace_cert_{project_type}")
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
            workspace_id=f"ws-cert-{project_type}",
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

    vrf_engine = VerificationEngine()
    verifications = vrf_engine.verify_all_results(updated_results, ws_root)

    acpt_engine = AcceptanceEngine()
    acceptances = acpt_engine.evaluate_all_acceptances(verifications)

    return ws_root, contract_report, results, q_reports, updated_results, verifications, acceptances


def test_autonomous_engineering_certification(tmp_path: Path):
    """Verify AutonomousEngineeringCertificationEngine certifies complete P5 pipeline."""
    ws_root, contract_report, results, q_reports, updated_results, verifications, acceptances = create_full_pipeline_artifacts(tmp_path)

    cert_engine = AutonomousEngineeringCertificationEngine()
    cert_report = cert_engine.certify_engineering_pipeline(
        acceptance_reports=acceptances,
        verification_results=verifications,
        updated_results=updated_results,
        quality_reports=q_reports,
        engineering_results=results,
        contract_report=contract_report,
    )

    assert isinstance(cert_report, EngineeringCertificationReport)
    assert cert_report.production_readiness is True
    assert cert_report.regression_status == "PASSED"
    assert cert_report.pipeline_version == "v1.2"
    assert cert_report.evidence["zero_workspace_write"] is True


def test_certification_cli(tmp_path: Path):
    """Verify oniroute certify-engineering CLI command execution."""
    runner = CliRunner()
    ws_root, _, _, _, _, _, _ = create_full_pipeline_artifacts(tmp_path)

    # Test rich output CLI command
    result = runner.invoke(app, ["certify-engineering", "--workspace", ws_root])
    if result.exit_code != 0:
        print("CLI Output:", result.output)
        if result.exception:
            print("CLI Exception:", result.exception)
    assert result.exit_code == 0
    assert "Autonomous Engineering Pipeline Certified & Frozen" in result.output


    # Test JSON output CLI command
    result_json = runner.invoke(app, ["certify-engineering", "--workspace", ws_root, "--json"])
    assert result_json.exit_code == 0
    data = json.loads(result_json.output)
    assert data["production_readiness"] is True
    assert data["pipeline_version"] == "v1.2"
