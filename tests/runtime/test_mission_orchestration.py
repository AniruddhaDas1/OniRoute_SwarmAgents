"""Tests for OniRoute Mission Orchestration (ACR-004 Phase O4)."""

import pytest
from pathlib import Path

from cli.main import REGISTERED_CLI_COMMANDS, main
from runtime.mission import (
    ExecutionRequest,
    InvalidMissionStateError,
    MissionDirector,
    MissionIntake,
    MissionOrchestrator,
    MissionResolver,
    MissionState,
)


def test_execution_request_schema_and_instantiation():
    intake = MissionIntake()
    request = intake.process_intake("Create portfolio website")
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)

    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)

    assert isinstance(exec_req, ExecutionRequest)
    assert exec_req.request_id.startswith("exreq-")
    assert exec_req.execution_state == MissionState.ORCHESTRATED
    assert exec_req.mission.status.current_state == MissionState.ORCHESTRATED
    assert exec_req.mission.result is None  # Zero execution result


def test_planning_preparation():
    intake = MissionIntake()
    request = intake.process_intake("Build REST API", parameters={"priority": "high", "risk_level": "medium"})
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)

    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)

    plan_req = exec_req.planning_request
    assert plan_req["mission_id"] == mission.mission_id
    assert plan_req["primary_goal"] == "Build REST API"
    assert plan_req["priority"] == "high"
    assert plan_req["risk_level"] == "medium"
    assert plan_req["status"] == "PREPARED"
    assert plan_req["no_plan_generated"] is True

    plan_ev = exec_req.execution_evidence.planning_prep
    assert plan_ev["planning_prepared"] is True
    assert plan_ev["no_execution_plan"] is True


def test_governance_preparation():
    intake = MissionIntake()
    request = intake.process_intake("Refactor auth", parameters={"require_human_approval": True})
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)

    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)

    gov_req = exec_req.governance_request
    assert "workspace:read" in gov_req["permissions"]
    assert "engine_read_only" in gov_req["policies"]
    assert gov_req["approvals"] == "REQUIRE_APPROVAL"
    assert gov_req["status"] == "PREPARED"
    assert gov_req["no_policy_evaluated"] is True

    gov_ev = exec_req.execution_evidence.governance_prep
    assert gov_ev["governance_prepared"] is True
    assert gov_ev["no_policy_evaluated"] is True


def test_workspace_preparation():
    intake = MissionIntake()
    request = intake.process_intake("Fix tests")
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)

    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)

    ws_req = exec_req.workspace_metadata
    assert "workspace_root" in ws_req or "engine_root" in ws_req

    ws_ev = exec_req.execution_evidence.workspace_prep
    assert ws_ev["workspace_prepared"] is True
    assert ws_ev["canonical_directories_count"] == 16
    assert ws_ev["no_filesystem_writes"] is True


def test_umal_preparation():
    intake = MissionIntake()
    request = intake.process_intake("Create SaaS landing page", parameters={"local_only": True})
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)

    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)

    umal_req = exec_req.umal_request
    assert umal_req["constraints"]["local_only"] is True
    assert umal_req["provider_independence"] is True
    assert umal_req["status"] == "PREPARED"
    assert umal_req["no_model_selected"] is True

    umal_ev = exec_req.execution_evidence.umal_prep
    assert umal_ev["umal_prepared"] is True
    assert umal_ev["no_model_selected"] is True


def test_invocation_preparation():
    intake = MissionIntake()
    request = intake.process_intake("Review repo", parameters={"streaming": True})
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)

    orchestrator = MissionOrchestrator()
    exec_req = orchestrator.orchestrate_mission(mission)

    inv_req = exec_req.invocation_request
    assert inv_req["streaming"] is True
    assert inv_req["tracing"] is True
    assert inv_req["status"] == "PREPARED"
    assert inv_req["no_invocation"] is True

    inv_ev = exec_req.execution_evidence.invocation_prep
    assert inv_ev["invocation_prepared"] is True
    assert inv_ev["no_invocation_executed"] is True


def test_mission_state_transition_validated_to_orchestrated():
    intake = MissionIntake()
    request = intake.process_intake("Create dashboard")
    resolver = MissionResolver()
    mission = resolver.resolve_mission(request)

    assert mission.status.current_state == MissionState.VALIDATED

    director = MissionDirector()
    exec_req = director.orchestrate_mission(mission)

    assert exec_req.execution_state == MissionState.ORCHESTRATED
    assert exec_req.mission.status.current_state == MissionState.ORCHESTRATED

    transitions = [s["to_state"] for s in exec_req.mission.status.state_history]
    assert "orchestrated" in transitions


def test_cli_mission_orchestrate_command(capsys):
    assert "mission" in REGISTERED_CLI_COMMANDS

    with pytest.raises(SystemExit) as exc_info:
        main(["mission", "orchestrate", "Create", "portfolio", "website", "--json"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert '"request_id"' in captured.out
    assert '"execution_state": "orchestrated"' in captured.out or '"execution_state":"orchestrated"' in captured.out
    assert '"no_execution": true' in captured.out.lower() or '"no_execution":true' in captured.out.lower() or '"no_execution"' in captured.out.lower()


def test_cli_natural_language_flows_through_orchestration(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["Create", "a", "premium", "SaaS", "landing", "page"])
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert '"request_id"' in captured.out
    assert '"execution_state": "orchestrated"' in captured.out or '"execution_state":"orchestrated"' in captured.out
