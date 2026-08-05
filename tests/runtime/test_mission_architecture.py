from pathlib import Path

from runtime.mission import (
    ALLOWED_STATE_TRANSITIONS,
    Mission,
    MissionConstraints,
    MissionContext,
    MissionDeliverables,
    MissionDirectorContract,
    MissionEvidence,
    MissionPipelineContract,
    MissionReport,
    MissionRequest,
    MissionRequirements,
    MissionResult,
    MissionState,
    MissionStatus,
    can_transition,
)


def test_mission_state_lifecycle_enum():
    states = [
        MissionState.RECEIVED,
        MissionState.PARSED,
        MissionState.RESOLVED,
        MissionState.VALIDATED,
        MissionState.PLANNED,
        MissionState.EXECUTING,
        MissionState.COMPLETED,
        MissionState.FAILED,
        MissionState.CANCELLED,
    ]
    assert len(states) == 9
    assert MissionState.RECEIVED.value == "received"
    assert MissionState.COMPLETED.value == "completed"


def test_mission_state_transitions():
    assert can_transition(MissionState.RECEIVED, MissionState.PARSED)
    assert can_transition(MissionState.PARSED, MissionState.RESOLVED)
    assert can_transition(MissionState.RESOLVED, MissionState.VALIDATED)
    assert can_transition(MissionState.VALIDATED, MissionState.PLANNED)
    assert can_transition(MissionState.PLANNED, MissionState.EXECUTING)
    assert can_transition(MissionState.EXECUTING, MissionState.COMPLETED)
    assert can_transition(MissionState.EXECUTING, MissionState.FAILED)
    assert can_transition(MissionState.EXECUTING, MissionState.CANCELLED)

    # Invalid transitions
    assert not can_transition(MissionState.COMPLETED, MissionState.EXECUTING)
    assert not can_transition(MissionState.FAILED, MissionState.PLANNED)
    assert not can_transition(MissionState.RECEIVED, MissionState.COMPLETED)


def test_mission_model_instantiation():
    req = MissionRequest(
        mission_id="msn-1001",
        request_id="req-1001",
        original_command="Create a premium SaaS landing page",
        normalized_command="Create a premium SaaS landing page",
        raw_prompt="Create a premium SaaS landing page",
        workspace=Path("/tmp/ws"),
    )
    reqs = MissionRequirements(
        intent_category="create",
        primary_goal="Create a premium SaaS landing page",
        functional_requirements=["Landing page layout", "Hero section", "Feature grid"],
    )
    constraints = MissionConstraints(
        max_budget_usd=5.0,
        timeout_seconds=600,
        local_only=False,
    )
    deliverables = MissionDeliverables(
        expected_categories=["SOURCE_CODE", "DOCUMENTATION"],
    )
    context = MissionContext(
        workspace_id="ws-9999",
        workspace_root=Path("/tmp/ws"),
        engine_root=Path("/opt/oniroute"),
        project_type="react",
        read_only_engine_confirmed=True,
    )
    evidence = MissionEvidence()
    status = MissionStatus(current_state=MissionState.RECEIVED)

    mission = Mission(
        mission_id="m-001",
        name="Create SaaS landing page",
        request=req,
        requirements=reqs,
        constraints=constraints,
        deliverables=deliverables,
        context=context,
        evidence=evidence,
        status=status,
    )

    assert mission.mission_id == "m-001"
    assert mission.request.raw_prompt == "Create a premium SaaS landing page"
    assert mission.context.project_type == "react"
    assert mission.status.current_state == MissionState.RECEIVED


def test_mission_evidence_recording():
    evidence = MissionEvidence()
    e1 = evidence.record_stage("workspace", {"root": "/tmp/ws", "valid": True})
    e2 = e1.record_stage("project", {"type": "python", "name": "my_app"})
    e3 = e2.record_stage("requirements", {"goal": "build api"})
    e4 = e3.record_stage("constraints", {"budget": 10.0})
    e5 = e4.record_stage("context", {"snapshot_id": "snap-123"})
    e6 = e5.record_stage("optimization", {"tokens_saved": 450})
    e7 = e6.record_stage("planning", {"plan_id": "p-1"})
    e8 = e7.record_stage("governance", {"policy_passed": True})
    e9 = e8.record_stage("model_selection", {"model": "gemini-3.6-flash"})
    e10 = e9.record_stage("execution", {"status": "completed"})
    e11 = e10.record_stage("artifacts", {"filename": "app.py", "category": "SOURCE_CODE"})

    assert e11.workspace["root"] == "/tmp/ws"
    assert e11.project["type"] == "python"
    assert e11.governance["policy_passed"] is True
    assert len(e11.artifacts) == 1
    assert e11.artifacts[0]["filename"] == "app.py"


def test_mission_director_and_pipeline_contracts():
    assert issubclass(MissionDirectorContract, object)
    assert issubclass(MissionPipelineContract, object)
