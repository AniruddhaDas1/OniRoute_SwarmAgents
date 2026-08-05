"""Tests for Self-Healing Subsystem (Phase P5.E3)."""

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
from runtime.review import QualityGateEngine, QualityReport, QualityFinding, ReviewSeverity
from runtime.healing import (
    RepairPlanner,
    SelfHealingEngine,
    RepairPlan,
    UpdatedEngineeringResult,
    SelfHealingBoundaryViolation,
    RepairPlanningError,
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


def create_sample_quality_reports(
    tmp_path: Path, project_type: str = "python"
) -> Tuple[str, List[EngineeringResult], List[QualityReport]]:
    """Helper to create deterministic QualityReports and EngineeringResults for testing."""
    ws_root = str(tmp_path / f"workspace_heal_{project_type}")
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
            workspace_id=f"ws-heal-{project_type}",
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

    return ws_root, results, q_reports


def test_repair_planner_creation(tmp_path: Path):
    """Verify RepairPlanner creates deterministic RepairPlan from QualityReport."""
    _, _, q_reports = create_sample_quality_reports(tmp_path, project_type="python")
    planner = RepairPlanner()

    # Add a synthetic HIGH severity finding to test repair planning
    synthetic_finding = QualityFinding(
        finding_id="fnd-test-0001",
        category="Architecture",
        severity=ReviewSeverity.HIGH.value,
        reviewer_profile_id="prf-lead-arch",
        reviewer_role="Lead System Architect",
        description="Modular boundary issue detected.",
        target_path="src/main.py",
        recommended_fix="Refactor modular dependencies.",
    )

    base_q = q_reports[0]
    updated_findings = list(base_q.findings) + [synthetic_finding]
    custom_q = QualityReport(
        report_id=base_q.report_id,
        engineering_result_id=base_q.engineering_result_id,
        contract_id=base_q.contract_id,
        reviewer_profiles=base_q.reviewer_profiles,
        findings=updated_findings,
        architecture_score=0.7,
        security_score=base_q.security_score,
        performance_score=base_q.performance_score,
        testing_score=base_q.testing_score,
        documentation_score=base_q.documentation_score,
        contract_compliance=True,
        approval_status="CONDITIONALLY_APPROVED",
        required_fixes=["[Architecture] Refactor modular dependencies."],
        evidence=base_q.evidence,
        timestamp=base_q.timestamp,
        report_hash=base_q.report_hash,
    )

    plan = planner.create_repair_plan(custom_q)

    assert isinstance(plan, RepairPlan)
    assert len(plan.actions) >= 1
    assert "src/main.py" in plan.target_files


def test_self_healing_execution(tmp_path: Path):
    """Verify SelfHealingEngine executes repairs and produces UpdatedEngineeringResult."""
    ws_root, results, q_reports = create_sample_quality_reports(tmp_path, project_type="python")
    planner = RepairPlanner()
    healing_engine = SelfHealingEngine()

    synthetic_finding = QualityFinding(
        finding_id="fnd-sec-0002",
        category="Security",
        severity=ReviewSeverity.CRITICAL.value,
        reviewer_profile_id="prf-sec-auditor",
        reviewer_role="Security Auditor",
        description="Path safety warning.",
        target_path=results[0].artifacts[0],
        recommended_fix="Add strict path validation.",
    )

    base_q = q_reports[0]
    custom_q = QualityReport(
        report_id=base_q.report_id,
        engineering_result_id=results[0].result_id,
        contract_id=base_q.contract_id,
        reviewer_profiles=base_q.reviewer_profiles,
        findings=[synthetic_finding],
        architecture_score=base_q.architecture_score,
        security_score=0.5,
        performance_score=base_q.performance_score,
        testing_score=base_q.testing_score,
        documentation_score=base_q.documentation_score,
        contract_compliance=True,
        approval_status="REJECTED",
        required_fixes=["[Security] Add strict path validation."],
        evidence=base_q.evidence,
        timestamp=base_q.timestamp,
        report_hash=base_q.report_hash,
    )

    plan = planner.create_repair_plan(custom_q)
    updated_result = healing_engine.apply_repairs(plan, results[0], ws_root)

    assert isinstance(updated_result, UpdatedEngineeringResult)
    assert len(updated_result.applied_repairs) == 1
    assert len(updated_result.resolved_findings) == 1
    assert updated_result.original_result_id == results[0].result_id


def test_self_healing_boundary_safety(tmp_path: Path):
    """Verify SelfHealingEngine rejects repair attempts outside workspace or into engine root."""
    healing_engine = SelfHealingEngine()

    with pytest.raises(SelfHealingBoundaryViolation):
        healing_engine._enforce_repair_safety(
            "../../etc/passwd",
            (tmp_path / "../../etc/passwd").resolve(),
            tmp_path.resolve(),
        )


def test_heal_cli(tmp_path: Path):
    """Verify oniroute heal CLI command execution."""
    runner = CliRunner()

    ws_root, results, q_reports = create_sample_quality_reports(tmp_path, project_type="python")
    rep_file = tmp_path / "quality_reports.json"
    res_file = tmp_path / "engineering_results.json"

    rep_file.write_text(json.dumps([q.model_dump(mode="json") for q in q_reports], indent=2), encoding="utf-8")
    res_file.write_text(json.dumps([r.model_dump(mode="json") for r in results], indent=2), encoding="utf-8")

    # Test rich output CLI execution
    result = runner.invoke(app, ["heal", "--report", str(rep_file), "--result", str(res_file), "--workspace", ws_root])
    assert result.exit_code == 0
    assert "Self-Healing Execution Complete" in result.output

    # Test JSON output CLI execution
    result_json = runner.invoke(app, ["heal", "--report", str(rep_file), "--result", str(res_file), "--workspace", ws_root, "--json"])
    assert result_json.exit_code == 0
    json_data = json.loads(result_json.output)
    assert isinstance(json_data, list)
    assert len(json_data) > 0
    assert "updated_result_id" in json_data[0]
