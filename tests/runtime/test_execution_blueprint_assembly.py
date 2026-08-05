"""Tests for Execution Blueprint Assembly (ACR-005 Phase S4)."""

from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from runtime.mission import (
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
    BlueprintValidator,
    CapabilityReport,
    CapabilityResolver,
    ExecutionBlueprint,
    ExecutionBlueprintAssembler,
    OrganizationAssembler,
    SwarmGraph,
    SwarmGraphBuilder,
)

runner = CliRunner()


def _get_test_execution_request() -> ExecutionRequest:
    msn_req = MissionRequest(
        mission_id="msn-bp-201",
        original_command="Build a microservice backend with FastAPI and PostgreSQL",
        normalized_command="Build a microservice backend with FastAPI and PostgreSQL",
        raw_prompt="Build a microservice backend with FastAPI and PostgreSQL",
    )
    msn = Mission(
        mission_id="msn-bp-201",
        name="Build Microservice Backend",
        request=msn_req,
        requirements=MissionRequirements(
            intent_category="create",
            primary_goal="Build a microservice backend with FastAPI and PostgreSQL",
            functional_requirements=["Build FastAPI REST endpoints", "Design PostgreSQL schema"],
            non_functional_requirements=["Audit code security"],
        ),
        constraints=MissionConstraints(local_only=True, timeout_seconds=300),
        deliverables=MissionDeliverables(),
        context=MissionContext(
            workspace_id="ws-bp-01",
            workspace_root=Path("/tmp/ws"),
            engine_root=Path("/opt/oniroute"),
        ),
        status=MissionStatus(current_state=MissionState.PARSED),
    )
    return ExecutionRequest(
        request_id="exreq-bp-201",
        mission=msn,
        mission_context=msn.context,
        mission_constraints=msn.constraints,
        execution_evidence=MissionEvidence(),
    )


def test_swarm_graph_builder():
    exec_req = _get_test_execution_request()
    cap_report = CapabilityResolver().resolve_capabilities(exec_req)
    org = OrganizationAssembler().assemble_organization(cap_report)

    sg_builder = SwarmGraphBuilder()
    swarm_graph = sg_builder.build_swarm_graph(org)

    assert isinstance(swarm_graph, SwarmGraph)
    assert swarm_graph.mission_id == exec_req.mission.mission_id
    assert len(swarm_graph.nodes) == len(org.members)
    assert len(swarm_graph.edges) > 0

    assert len(swarm_graph.reporting_hierarchy.supervisor_subordinate_pairs) > 0
    assert len(swarm_graph.execution_hierarchy.execution_levels) > 0
    assert len(swarm_graph.approval_hierarchy.approval_gates) > 0


def test_blueprint_assembler_end_to_end():
    exec_req = _get_test_execution_request()
    bp_assembler = ExecutionBlueprintAssembler()
    blueprint = bp_assembler.assemble_blueprint(exec_req)

    assert isinstance(blueprint, ExecutionBlueprint)
    assert blueprint.blueprint_id == f"blp-{exec_req.mission.mission_id}"
    assert blueprint.mission.mission_id == exec_req.mission.mission_id
    assert blueprint.readiness.is_ready is True
    assert blueprint.validation_report["readiness_verdict"] == "PASSED"
    assert len(blueprint.department_structure) > 0
    assert len(blueprint.execution_dependencies) >= 0


def test_blueprint_validator_integrity():
    exec_req = _get_test_execution_request()
    bp_assembler = ExecutionBlueprintAssembler()
    blueprint = bp_assembler.assemble_blueprint(exec_req)

    validator = BlueprintValidator()
    readiness, report = validator.validate_blueprint(blueprint)

    assert readiness.is_ready is True
    assert report["duplicate_members_count"] == 0
    assert report["broken_dependencies_count"] == 0
    assert len(report["orphan_departments"]) == 0
    assert len(report["missing_capabilities"]) == 0


def test_cli_oniroute_blueprint_text():
    result = runner.invoke(app, ["blueprint", "Create CRM"])
    assert result.exit_code == 0
    assert "Sealed Execution Blueprint" in result.output
    assert "Execution Blueprint Readiness Verification" in result.output


def test_cli_oniroute_blueprint_json():
    result = runner.invoke(app, ["blueprint", "--json", "Build REST API"])
    assert result.exit_code == 0
    assert '"blueprint_id":' in result.output
    assert '"organization":' in result.output
    assert '"dependencies":' in result.output
    assert '"validation_report":' in result.output
