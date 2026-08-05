"""Tests for OniRoute Mission Resolution (ACR-004 Phase O3)."""

import pytest
from pathlib import Path

from cli.main import REGISTERED_CLI_COMMANDS, main
from runtime.mission import (
    InvalidMissionStateError,
    Mission,
    MissionDirector,
    MissionIntake,
    MissionRequest,
    MissionResolutionError,
    MissionResolver,
    MissionState,
    MissionValidationError,
)


def test_mission_resolution_workspace_analysis():
    intake = MissionIntake()
    request = intake.process_intake("Create portfolio website")
    resolver = MissionResolver()

    mission = resolver.resolve_mission(request)

    assert isinstance(mission, Mission)
    assert mission.context.workspace_root == request.workspace
    assert mission.evidence.workspace["workspace_root"] == str(request.workspace)
    assert "read_only_engine_confirmed" in mission.evidence.workspace
    assert mission.evidence.workspace["read_only_engine_confirmed"] is True


def test_mission_resolution_project_analysis():
    intake = MissionIntake()
    request = intake.process_intake("Build REST API")
    resolver = MissionResolver()

    mission = resolver.resolve_mission(request)

    proj_ev = mission.evidence.project
    assert "project_type" in proj_ev
    assert "language" in proj_ev
    assert "build_system" in proj_ev
    assert "package_manager" in proj_ev
    assert "repository_layout" in proj_ev


def test_mission_resolution_repository_analysis():
    intake = MissionIntake()
    request = intake.process_intake("Review this repository")
    resolver = MissionResolver()

    mission = resolver.resolve_mission(request)

    repo_ev = mission.evidence.repository
    assert "symbols_count" in repo_ev
    assert "configuration_files" in repo_ev
    assert "documentation_files" in repo_ev
    assert repo_ev["no_planning"] is True


def test_mission_resolution_context_resolution():
    intake = MissionIntake()
    request = intake.process_intake("Refactor authentication module")
    resolver = MissionResolver()

    mission = resolver.resolve_mission(request)

    ctx_ev = mission.evidence.context
    icoe_ev = mission.evidence.optimization
    assert "mission_context" in ctx_ev
    assert "request_id" in icoe_ev
    assert "measurements" in icoe_ev


def test_mission_resolution_knowledge_resolution():
    intake = MissionIntake()
    request = intake.process_intake("Create a SaaS landing page")
    resolver = MissionResolver()

    mission = resolver.resolve_mission(request)

    know_ev = mission.evidence.knowledge
    assert "knowledge_sources" in know_ev
    assert "packages" in know_ev
    assert "mappings" in know_ev
    assert know_ev["skills_selected"] is False
    assert know_ev["agents_selected"] is False


def test_mission_resolution_constraint_resolution():
    intake = MissionIntake()
    request = intake.process_intake(
        "Build payment integration",
        parameters={
            "max_budget_usd": 10.0,
            "timeout_seconds": 600,
            "local_only": True,
            "require_human_approval": True,
        },
    )
    resolver = MissionResolver()

    mission = resolver.resolve_mission(request)

    assert mission.constraints.max_budget_usd == 10.0
    assert mission.constraints.timeout_seconds == 600
    assert mission.constraints.local_only is True
    assert mission.constraints.require_human_approval is True

    const_ev = mission.evidence.constraints
    assert const_ev["user_constraints"]["max_budget_usd"] == 10.0


def test_mission_resolution_validation_and_state_transitions():
    intake = MissionIntake()
    request = intake.process_intake("Fix failing tests")
    director = MissionDirector()

    mission = director.receive_mission(request)
    mission = director.supervise_orchestration(mission)

    assert mission.status.current_state == MissionState.VALIDATED
    assert mission.result is None  # Zero execution
    assert mission.report is not None
    assert mission.report.evidence_summary["validation"] is True

    val_ev = mission.evidence.validation
    assert val_ev["validated"] is True
    assert val_ev["no_planning"] is True
    assert val_ev["no_workflows"] is True
    assert val_ev["no_agent_selection"] is True
    assert val_ev["no_skill_selection"] is True
    assert val_ev["no_model_selection"] is True
    assert val_ev["no_execution"] is True


def test_mission_resolution_evidence_completeness():
    intake = MissionIntake()
    request = intake.process_intake("Review performance")
    resolver = MissionResolver()

    mission = resolver.resolve_mission(request)
    evidence = mission.evidence

    assert bool(evidence.workspace)
    assert bool(evidence.project)
    assert bool(evidence.repository)
    assert bool(evidence.context)
    assert bool(evidence.optimization)
    assert bool(evidence.knowledge)
    assert bool(evidence.constraints)
    assert bool(evidence.requirements)
    assert bool(evidence.validation)


def test_cli_mission_command_inspection(capsys):
    assert "mission" in REGISTERED_CLI_COMMANDS

    with pytest.raises(SystemExit) as exc_info:
        main(["mission", "Create", "portfolio", "website", "--json"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert '"request_id"' in captured.out or "OniRoute Swarm AI Engine" in captured.out or "Project Generated" in captured.out


def test_cli_natural_language_flows_through_resolution(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["Create", "a", "premium", "SaaS", "landing", "page"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    # CLI now renders Rich execution experience instead of raw JSON
    assert "OniRoute Swarm AI Engine" in captured.out or "Project Generated" in captured.out
    assert "Production Ready" in captured.out or "Certification ID" in captured.out or "cert-" in captured.out


def test_invalid_state_transition_raises():
    director = MissionDirector()
    intake = MissionIntake()
    request = intake.process_intake("Create portfolio")
    mission = director.receive_mission(request)

    # Attempt invalid transition from VALIDATED directly to COMPLETED (skipping PLANNED, EXECUTING)
    with pytest.raises(InvalidMissionStateError):
        director.transition_state(mission, MissionState.COMPLETED)
