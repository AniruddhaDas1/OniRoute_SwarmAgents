"""Tests for Agent Execution Engine (ACR-006 Phase R3).

Uses mock InvocationEngine to ensure deterministic tests without live network calls.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.agent import (
    AgentExecutionEngine,
    ArtifactCollector,
    ExecutionReporter,
    ExecutionResult,
    ExecutionStatus,
    RuntimeEventType,
    RuntimeReport,
    RuntimeState,
    SessionCoordinator,
)
from runtime.invocation.models import Usage
from runtime.invocation.response import InvocationResponse
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
from runtime.organization import ExecutionBlueprintAssembler
from runtime.organization.blueprint import ExecutionBlueprint

runner = CliRunner()

REPO_ROOT = Path(__file__).parents[2]


def _make_blueprint() -> ExecutionBlueprint:
    req = MissionRequest(
        mission_id="msn-exec-501",
        original_command="Build a portfolio website",
        normalized_command="Build a portfolio website",
        raw_prompt="Build a portfolio website",
    )
    mission = Mission(
        mission_id="msn-exec-501",
        name="Portfolio Website",
        request=req,
        requirements=MissionRequirements(
            intent_category="create",
            primary_goal="Build a portfolio website",
            functional_requirements=["Landing page", "Projects section", "Contact form"],
            non_functional_requirements=["Responsive design"],
        ),
        constraints=MissionConstraints(local_only=True, timeout_seconds=300),
        deliverables=MissionDeliverables(),
        context=MissionContext(
            workspace_id="ws-exec-01",
            workspace_root=Path("/tmp/ws"),
            engine_root=Path("/opt/oniroute"),
        ),
        status=MissionStatus(current_state=MissionState.PARSED),
    )
    exec_req = ExecutionRequest(
        request_id="exreq-exec-501",
        mission=mission,
        mission_context=mission.context,
        mission_constraints=mission.constraints,
        execution_evidence=MissionEvidence(),
    )
    return ExecutionBlueprintAssembler().assemble_blueprint(exec_req)


def _fake_response() -> InvocationResponse:
    return InvocationResponse(
        text="Here is the structured execution plan for the portfolio website...",
        usage=Usage(input_tokens=120, output_tokens=480, total_tokens=600),
        latency_ms=142.0,
        finish_reason="stop",
        metadata={"model": "qwen2.5:32b", "provider": "ollama", "protocol": "ollama"},
    )


# ---------------------------------------------------------------------------
# ArtifactCollector Tests
# ---------------------------------------------------------------------------

def test_artifact_collector_registers():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]

    from runtime.agent import ArtifactRecord, ArtifactType
    collector = ArtifactCollector()
    artifact = ArtifactRecord(
        artifact_id="art-test-001",
        artifact_type=ArtifactType.REPORT,
        owner_session_id=session.session_id,
        owner_member_id=session.member_id,
        capability_id="cap-test",
        name="Test Artifact",
    )
    registered = collector.register_artifact(session, artifact)
    assert registered.artifact_id == "art-test-001"
    assert collector.total == 1
    assert len(collector.get_artifacts(session.session_id)) == 1


def test_artifact_collector_appends_to_session():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]

    from runtime.agent import ArtifactRecord, ArtifactType
    collector = ArtifactCollector()
    artifact = ArtifactRecord(
        artifact_id="art-test-002",
        artifact_type=ArtifactType.CODE,
        owner_session_id=session.session_id,
        owner_member_id=session.member_id,
        capability_id="cap-test",
        name="Code Artifact",
    )
    collector.register_artifact(session, artifact)
    assert len(session.artifacts) == 1


# ---------------------------------------------------------------------------
# ExecutionReporter Tests
# ---------------------------------------------------------------------------

def test_execution_reporter_completed():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    # Manually drive sessions to COMPLETED
    from runtime.agent import SessionManager
    mgr = SessionManager()
    for s in sessions:
        mgr.transition_state(s, RuntimeState.RUNNING)
        mgr.transition_state(s, RuntimeState.COMPLETED)

    reporter = ExecutionReporter()
    report = reporter.compile_report(blueprint, sessions)

    assert isinstance(report, RuntimeReport)
    assert report.completed_sessions == len(sessions)
    assert report.failed_sessions == 0


def test_execution_reporter_failed():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    from runtime.agent import SessionManager
    mgr = SessionManager()
    for s in sessions:
        mgr.transition_state(s, RuntimeState.RUNNING)
        mgr.transition_state(s, RuntimeState.FAILED)

    reporter = ExecutionReporter()
    report = reporter.compile_report(blueprint, sessions)

    assert report.failed_sessions == len(sessions)
    assert report.completed_sessions == 0


# ---------------------------------------------------------------------------
# AgentExecutionEngine Tests (mocked InvocationEngine)
# ---------------------------------------------------------------------------

def _make_patched_engine(fake_resp: InvocationResponse) -> AgentExecutionEngine:
    engine = AgentExecutionEngine.__new__(AgentExecutionEngine)
    engine._repo_root = REPO_ROOT
    engine._endpoint = "http://127.0.0.1:11434"
    engine._governance = MagicMock()
    from runtime.governance.models import Decision, PolicyResult
    engine._governance.evaluate.return_value = PolicyResult(decision=Decision.ALLOW)
    engine._governance.authorize.return_value = PolicyResult(decision=Decision.ALLOW)
    engine._manager = MagicMock()
    engine._invocation_engine = MagicMock()
    engine._invocation_engine.invoke.return_value = fake_resp
    from runtime.agent import SessionManager, EventRecorder
    from runtime.agent.artifact_collector import ArtifactCollector
    from runtime.agent.execution_reporter import ExecutionReporter
    engine._session_manager = SessionManager()
    engine._artifact_collector = ArtifactCollector()
    engine._event_recorder = EventRecorder()
    engine._reporter = ExecutionReporter()
    return engine


def test_execute_session_success():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]

    engine = _make_patched_engine(_fake_response())
    result = engine.execute_session(session, blueprint)

    assert result.status == ExecutionStatus.DONE
    assert len(result.artifacts_produced) == 1
    assert session.state == RuntimeState.COMPLETED


def test_execute_session_emits_required_events():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]
    initial_event_count = len(session.events)

    engine = _make_patched_engine(_fake_response())
    engine.execute_session(session, blueprint)

    event_types = {e.event_type for e in session.events}
    assert RuntimeEventType.EXECUTION_STARTED in event_types
    assert RuntimeEventType.ARTIFACT_PRODUCED in event_types
    assert RuntimeEventType.EXECUTION_COMPLETED in event_types
    assert RuntimeEventType.STATE_TRANSITION in event_types
    # At least 4 new events appended after session initialization
    assert len(session.events) >= initial_event_count + 4


def test_execute_session_registers_artifact():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]

    engine = _make_patched_engine(_fake_response())
    engine.execute_session(session, blueprint)

    assert len(session.artifacts) == 1
    artifact = session.artifacts[0]
    assert artifact.owner_session_id == session.session_id
    assert artifact.owner_member_id == session.member_id


def test_execute_session_governance_denied():
    from runtime.governance.models import Decision, PolicyResult
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]

    engine = _make_patched_engine(_fake_response())
    engine._governance.evaluate.return_value = PolicyResult(
        decision=Decision.DENY, reasons=("permission policy",)
    )

    result = engine.execute_session(session, blueprint)
    assert result.status == ExecutionStatus.ERROR
    assert "Governance denied" in result.summary
    assert session.state == RuntimeState.FAILED


def test_execute_session_invocation_failure():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]

    engine = _make_patched_engine(_fake_response())
    engine._invocation_engine.invoke.side_effect = RuntimeError("Adapter unreachable")

    result = engine.execute_session(session, blueprint)
    assert result.status == ExecutionStatus.ERROR
    assert "Adapter unreachable" in result.summary
    assert session.state == RuntimeState.FAILED


def test_execute_session_rejects_non_ready():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)
    session = sessions[0]

    # Manually advance session beyond READY
    from runtime.agent import SessionManager
    SessionManager().transition_state(session, RuntimeState.RUNNING)

    engine = _make_patched_engine(_fake_response())
    with pytest.raises(ValueError, match="not READY"):
        engine.execute_session(session, blueprint)


def test_execute_all_success():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    engine = _make_patched_engine(_fake_response())
    results, report = engine.execute_all(blueprint, coordinator.registry)

    assert len(results) == len(sessions)
    assert all(r.status == ExecutionStatus.DONE for r in results)
    assert report.completed_sessions == len(sessions)
    assert report.failed_sessions == 0
    assert report.total_artifacts == len(sessions)


def test_execute_all_report_structure():
    blueprint = _make_blueprint()
    coordinator = SessionCoordinator()
    _, sessions, _ = coordinator.initialize_sessions(blueprint)

    engine = _make_patched_engine(_fake_response())
    _, report = engine.execute_all(blueprint, coordinator.registry)

    assert isinstance(report, RuntimeReport)
    assert report.blueprint_id == blueprint.blueprint_id
    assert report.mission_id == blueprint.mission.mission_id
    assert report.total_events > 0


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------

def test_cli_execute_text():
    with patch("runtime.agent.execution_engine.InvocationEngine") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = _fake_response()
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["execute", "Create portfolio website"])
        assert result.exit_code == 0
        assert "Autonomous Swarm Execution Overview" in result.output
        assert "Task Execution Results" in result.output


def test_cli_execute_json():
    with patch("runtime.agent.execution_engine.InvocationEngine") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = _fake_response()
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["execute", "--json", "Build REST API"])
        assert result.exit_code == 0
        assert '"snapshot":' in result.output
        assert '"execution_results":' in result.output

