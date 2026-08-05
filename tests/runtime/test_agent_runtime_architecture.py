"""Architecture tests for the Agent Runtime (ACR-006 Phase R1)."""

from runtime.agent import (
    ALLOWED_RUNTIME_TRANSITIONS,
    AgentSession,
    ArtifactRecord,
    ArtifactType,
    ExecutionEvent,
    ExecutionResult,
    ExecutionStatus,
    RuntimeContext,
    RuntimeEventType,
    RuntimeMetrics,
    RuntimeReport,
    RuntimeState,
    can_runtime_transition,
)
from runtime.agent.contracts import (
    ArtifactCollectorContract,
    EventRecorderContract,
    ExecutionCoordinatorContract,
    ExecutionReporterContract,
    RuntimeInitializerContract,
    SessionManagerContract,
)


def test_runtime_state_lifecycle_completeness():
    """All canonical lifecycle states must be defined and reachable."""
    required_states = {
        "initialized", "ready", "running", "waiting",
        "review", "completed", "failed", "cancelled",
    }
    defined = {s.value for s in RuntimeState}
    assert required_states == defined


def test_allowed_transitions_dag():
    """Every state must appear in the transition table; terminal states have no exits."""
    for state in RuntimeState:
        assert state in ALLOWED_RUNTIME_TRANSITIONS

    # Terminal states have no outbound transitions
    assert ALLOWED_RUNTIME_TRANSITIONS[RuntimeState.COMPLETED] == set()
    assert ALLOWED_RUNTIME_TRANSITIONS[RuntimeState.FAILED] == set()
    assert ALLOWED_RUNTIME_TRANSITIONS[RuntimeState.CANCELLED] == set()


def test_can_runtime_transition_guard():
    """Transition guard must allow valid paths and block invalid ones."""
    assert can_runtime_transition(RuntimeState.INITIALIZED, RuntimeState.READY) is True
    assert can_runtime_transition(RuntimeState.READY, RuntimeState.RUNNING) is True
    assert can_runtime_transition(RuntimeState.RUNNING, RuntimeState.COMPLETED) is True
    assert can_runtime_transition(RuntimeState.RUNNING, RuntimeState.FAILED) is True

    # Cannot go backwards
    assert can_runtime_transition(RuntimeState.COMPLETED, RuntimeState.RUNNING) is False
    assert can_runtime_transition(RuntimeState.FAILED, RuntimeState.READY) is False
    assert can_runtime_transition(RuntimeState.CANCELLED, RuntimeState.INITIALIZED) is False


def test_agent_session_schema():
    """AgentSession must be fully instantiatable from declared schema."""
    session = AgentSession(
        session_id="sess-mem-backend-01-001",
        member_id="mem-backend-01",
        role_id="role-backend-lead",
        role_title="Backend Engineer",
        blueprint_id="blp-msn-test-001",
        capability_ids=["cap-backend-01", "cap-backend-02"],
    )
    assert session.state == RuntimeState.INITIALIZED
    assert session.status == ExecutionStatus.PENDING
    assert len(session.artifacts) == 0
    assert len(session.events) == 0


def test_execution_event_schema():
    """ExecutionEvent must capture all required event fields."""
    event = ExecutionEvent(
        event_id="ev-001",
        event_type=RuntimeEventType.SESSION_CREATED,
        session_id="sess-mem-backend-01-001",
        member_id="mem-backend-01",
        description="Session created for Backend Engineer",
        previous_state=None,
        next_state=RuntimeState.INITIALIZED,
    )
    assert event.event_type == RuntimeEventType.SESSION_CREATED
    assert event.next_state == RuntimeState.INITIALIZED


def test_artifact_record_schema():
    """ArtifactRecord must capture lineage, ownership, and type."""
    artifact = ArtifactRecord(
        artifact_id="art-001",
        artifact_type=ArtifactType.CODE,
        owner_session_id="sess-mem-backend-01-001",
        owner_member_id="mem-backend-01",
        capability_id="cap-backend-01",
        name="FastAPI REST Service",
        lineage=[],
    )
    assert artifact.artifact_type == ArtifactType.CODE
    assert artifact.owner_member_id == "mem-backend-01"


def test_runtime_context_schema():
    """RuntimeContext must be instantiatable with blueprint and mission references."""
    ctx = RuntimeContext(
        context_id="ctx-test-001",
        blueprint_id="blp-msn-test-001",
        mission_id="msn-test-001",
        organization_id="org-msn-test-001",
        workspace_root="/projects/workspace",
        engine_root="/opt/oniroute",
    )
    assert ctx.blueprint_id == "blp-msn-test-001"
    assert len(ctx.active_session_ids) == 0


def test_runtime_report_schema():
    """RuntimeReport must aggregate session outcomes from all members."""
    report = RuntimeReport(
        report_id="rep-rt-001",
        blueprint_id="blp-msn-test-001",
        mission_id="msn-test-001",
        total_sessions=5,
        completed_sessions=5,
        failed_sessions=0,
        cancelled_sessions=0,
        total_artifacts=8,
        total_events=20,
        summary="All 5 sessions completed successfully.",
    )
    assert report.total_sessions == 5
    assert report.failed_sessions == 0


def test_all_contracts_are_abstract():
    """All runtime contracts must be abstract and non-instantiatable."""
    import inspect

    for contract_cls in (
        RuntimeInitializerContract,
        SessionManagerContract,
        ExecutionCoordinatorContract,
        ArtifactCollectorContract,
        EventRecorderContract,
        ExecutionReporterContract,
    ):
        assert inspect.isabstract(contract_cls), f"{contract_cls.__name__} must be abstract"


def test_runtime_event_types_completeness():
    """All canonical event types must be defined."""
    required = {
        "session_created", "execution_started", "execution_paused",
        "execution_completed", "execution_failed", "artifact_produced",
        "review_requested", "review_completed", "state_transition",
    }
    defined = {e.value for e in RuntimeEventType}
    assert required == defined


def test_execution_result_schema():
    """ExecutionResult must represent finalized session outcome."""
    result = ExecutionResult(
        result_id="res-001",
        session_id="sess-mem-backend-01-001",
        member_id="mem-backend-01",
        status=ExecutionStatus.DONE,
        artifacts_produced=["art-001", "art-002"],
        events_recorded=5,
        summary="Backend API delivered.",
    )
    assert result.status == ExecutionStatus.DONE
    assert len(result.artifacts_produced) == 2
