"""Tests for Agent Session Management (ACR-006 Phase R2)."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from runtime.agent import (
    AgentSession,
    EventRecorder,
    ExecutionStatus,
    RuntimeContext,
    RuntimeEventType,
    RuntimeReport,
    RuntimeState,
    SessionCoordinator,
    SessionManager,
    SessionRegistry,
)
from runtime.mission.models import (
    ExecutionRequest,
    Mission,
    MissionConstraints,
    MissionContext,
    MissionDeliverables,
    MissionEvidence,
    MissionRequest,
    MissionRequirements,
    MissionState,
    MissionStatus,
)
from runtime.organization import (
    CapabilityResolver,
    ExecutionBlueprintAssembler,
    OrganizationAssembler,
    SwarmGraphBuilder,
)
from runtime.organization.blueprint import ExecutionBlueprint

runner = CliRunner()


def _make_exec_request() -> ExecutionRequest:
    req = MissionRequest(
        mission_id="msn-sm-401",
        original_command="Build microservice with FastAPI",
        normalized_command="Build microservice with FastAPI",
        raw_prompt="Build microservice with FastAPI",
    )
    mission = Mission(
        mission_id="msn-sm-401",
        name="Build Microservice",
        request=req,
        requirements=MissionRequirements(
            intent_category="create",
            primary_goal="Build microservice with FastAPI",
            functional_requirements=["Build FastAPI endpoints", "Connect PostgreSQL"],
            non_functional_requirements=["Audit security"],
        ),
        constraints=MissionConstraints(local_only=True, timeout_seconds=300),
        deliverables=MissionDeliverables(),
        context=MissionContext(
            workspace_id="ws-sm-01",
            workspace_root=Path("/tmp/ws"),
            engine_root=Path("/opt/oniroute"),
        ),
        status=MissionStatus(current_state=MissionState.PARSED),
    )
    return ExecutionRequest(
        request_id="exreq-sm-401",
        mission=mission,
        mission_context=mission.context,
        mission_constraints=mission.constraints,
        execution_evidence=MissionEvidence(),
    )


def _make_blueprint() -> ExecutionBlueprint:
    exec_req = _make_exec_request()
    assembler = ExecutionBlueprintAssembler()
    return assembler.assemble_blueprint(exec_req)


def test_session_coordinator_creates_all_sessions():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    context, sessions, report = coordinator.initialize_sessions(blueprint)

    assert isinstance(context, RuntimeContext)
    assert context.blueprint_id == blueprint.blueprint_id

    assert len(sessions) == len(blueprint.organization.members)
    assert len(context.active_session_ids) == len(sessions)
    assert report.total_sessions == len(sessions)


def test_all_sessions_reach_ready_state():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    for session in sessions:
        assert session.state == RuntimeState.READY, f"{session.session_id} not READY"
        assert session.status == ExecutionStatus.PENDING


def test_session_inherits_blueprint_fields():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    for session in sessions:
        assert session.blueprint_id == blueprint.blueprint_id
        assert session.member_id != ""
        assert session.role_id != ""
        assert session.role_title != ""


def test_each_session_has_events():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    for session in sessions:
        event_types = {e.event_type for e in session.events}
        assert RuntimeEventType.SESSION_CREATED in event_types
        assert RuntimeEventType.STATE_TRANSITION in event_types


def test_unique_session_ids():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    ids = [s.session_id for s in sessions]
    assert len(ids) == len(set(ids)), "Duplicate session IDs detected"


def test_session_registry_operations():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    registry = coordinator.registry

    assert registry.total == len(sessions)

    first = sessions[0]
    found = registry.get_session(first.session_id)
    assert found is not None
    assert found.session_id == first.session_id

    ready_sessions = registry.find_by_state(RuntimeState.READY)
    assert len(ready_sessions) == len(sessions)

    by_member = registry.find_by_member(first.member_id)
    assert len(by_member) >= 1

    by_role = registry.find_by_role(first.role_id)
    assert len(by_role) >= 1


def test_session_registry_rejects_duplicates():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    import pytest
    with pytest.raises(ValueError, match="Duplicate session ID"):
        coordinator.registry.register(sessions[0])


def test_session_manager_transition_guard():
    blueprint = _make_blueprint()
    mgr = SessionManager()
    session = mgr.create_session(blueprint, blueprint.organization.members[0].member_id)
    assert session.state == RuntimeState.READY

    # Valid transition: READY → RUNNING
    session = mgr.transition_state(session, RuntimeState.RUNNING)
    assert session.state == RuntimeState.RUNNING

    # Invalid transition: RUNNING → INITIALIZED (backward)
    import pytest
    with pytest.raises(ValueError, match="Invalid transition"):
        mgr.transition_state(session, RuntimeState.INITIALIZED)


def test_runtime_report_structure():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, report = coordinator.initialize_sessions(blueprint)

    assert isinstance(report, RuntimeReport)
    assert report.blueprint_id == blueprint.blueprint_id
    assert report.total_sessions == len(sessions)
    assert report.total_events > 0
    assert report.failed_sessions == 0
    assert len(report.execution_results) == len(sessions)


def test_cli_oniroute_session_text():
    result = runner.invoke(app, ["session", "Create CRM"])
    assert result.exit_code == 0
    assert "Agent Sessions" in result.output
    assert "READY" in result.output
    assert "Session Initialization Runtime Report" in result.output


def test_cli_oniroute_session_json():
    result = runner.invoke(app, ["session", "--json", "Build REST API"])
    assert result.exit_code == 0
    assert '"report_id":' in result.output
    assert '"total_sessions":' in result.output
    assert '"blueprint_id":' in result.output
    assert '"execution_results":' in result.output
