"""Freeze and contract immutability tests for Organization Builder (ACR-005 Phase S5)."""

from pathlib import Path

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
    ApprovalHierarchy,
    BlueprintValidator,
    Capability,
    CapabilityConstraint,
    CapabilityEvidence,
    CapabilityGroup,
    CapabilityPriority,
    CapabilityReport,
    CapabilityRequirement,
    CapabilityResolver,
    CapabilityValidator,
    DependencyType,
    EdgeType,
    ExecutionBlueprint,
    ExecutionBlueprintAssembler,
    ExecutionHierarchy,
    ExecutionReadiness,
    MemberStatus,
    Organization,
    OrganizationAssembler,
    OrganizationDependency,
    OrganizationEvidence,
    OrganizationGraph,
    OrganizationHierarchy,
    OrganizationMember,
    OrganizationReport,
    OrganizationRole,
    OrganizationRoleType,
    OrganizationValidator,
    ReportingHierarchy,
    ReviewHierarchy,
    SwarmGraph,
    SwarmGraphBuilder,
    SwarmGraphEdge,
    SwarmGraphNode,
)


def _build_test_execution_request() -> ExecutionRequest:
    msn_req = MissionRequest(
        mission_id="msn-freeze-301",
        original_command="Build a SaaS landing page with React and Python backend",
        normalized_command="Build a SaaS landing page with React and Python backend",
        raw_prompt="Build a SaaS landing page with React and Python backend",
    )
    msn = Mission(
        mission_id="msn-freeze-301",
        name="Build SaaS Landing Page",
        request=msn_req,
        requirements=MissionRequirements(
            intent_category="create",
            primary_goal="Build a SaaS landing page with React and Python backend",
            functional_requirements=["Build React landing page", "Build Python backend API"],
            non_functional_requirements=["Ensure high performance", "Audit security"],
        ),
        constraints=MissionConstraints(local_only=True, timeout_seconds=300),
        deliverables=MissionDeliverables(),
        context=MissionContext(
            workspace_id="ws-freeze-01",
            workspace_root=Path("/tmp/ws"),
            engine_root=Path("/opt/oniroute"),
        ),
        status=MissionStatus(current_state=MissionState.PARSED),
    )
    return ExecutionRequest(
        request_id="exreq-freeze-301",
        mission=msn,
        mission_context=msn.context,
        mission_constraints=msn.constraints,
        execution_evidence=MissionEvidence(),
    )


def test_full_organization_builder_pipeline_freeze():
    exec_req = _build_test_execution_request()

    # 1. Capability Resolution
    cap_resolver = CapabilityResolver()
    cap_report = cap_resolver.resolve_capabilities(exec_req)
    assert isinstance(cap_report, CapabilityReport)
    assert cap_report.readiness["is_ready"] is True

    # 2. Organization Assembly
    org_assembler = OrganizationAssembler()
    org = org_assembler.assemble_organization(cap_report, mission_id=exec_req.mission.mission_id)
    assert isinstance(org, Organization)
    assert org.report is not None
    assert org.report.structural_integrity_verified is True

    # 3. Swarm Graph Construction
    sg_builder = SwarmGraphBuilder()
    swarm_graph = sg_builder.build_swarm_graph(org)
    assert isinstance(swarm_graph, SwarmGraph)
    assert len(swarm_graph.nodes) == len(org.members)

    # 4. Blueprint Assembly & Sealing
    bp_assembler = ExecutionBlueprintAssembler()
    blueprint = bp_assembler.create_blueprint(exec_req, org, cap_report, swarm_graph)
    assert isinstance(blueprint, ExecutionBlueprint)
    assert blueprint.readiness.is_ready is True


def test_model_json_serialization_roundtrip():
    exec_req = _build_test_execution_request()
    bp_assembler = ExecutionBlueprintAssembler()
    blueprint = bp_assembler.assemble_blueprint(exec_req)

    # Serialize to dict and validate roundtrip
    dump_dict = blueprint.model_dump(mode="json")
    restored_blueprint = ExecutionBlueprint.model_validate(dump_dict)

    assert restored_blueprint.blueprint_id == blueprint.blueprint_id
    assert restored_blueprint.mission.mission_id == blueprint.mission.mission_id
    assert len(restored_blueprint.organization.members) == len(blueprint.organization.members)
    assert len(restored_blueprint.dependencies.nodes) == len(blueprint.dependencies.nodes)
    assert restored_blueprint.readiness.is_ready is True


def test_frozen_contracts_integrity():
    # Verify presence of abstract contract classes
    from runtime.organization.contracts import (
        CapabilityAnalyzerContract,
        ExecutionBlueprintBuilderContract,
        OrganizationBuilderContract,
        OrganizationValidatorContract,
        SwarmGraphBuilderContract,
    )

    assert hasattr(CapabilityAnalyzerContract, "analyze_capabilities")
    assert hasattr(OrganizationBuilderContract, "build_organization")
    assert hasattr(OrganizationValidatorContract, "validate_organization")
    assert hasattr(SwarmGraphBuilderContract, "build_swarm_graph")
    assert hasattr(ExecutionBlueprintBuilderContract, "create_blueprint")
