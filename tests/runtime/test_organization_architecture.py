"""Architecture validation tests for Engineering Organization Builder (ACR-005 Phase S1)."""

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
    Capability,
    CapabilityConstraint,
    CapabilityEvidence,
    CapabilityGroup,
    CapabilityPriority,
    CapabilityReport,
    CapabilityRequirement,
    DependencyType,
    EdgeType,
    ExecutionBlueprint,
    ExecutionHierarchy,
    ExecutionReadiness,
    MemberStatus,
    Organization,
    OrganizationDependency,
    OrganizationEvidence,
    OrganizationGraph,
    OrganizationHierarchy,
    OrganizationMember,
    OrganizationReport,
    OrganizationRole,
    OrganizationRoleType,
    ReportingHierarchy,
    ReviewHierarchy,
    SwarmGraph,
    SwarmGraphEdge,
    SwarmGraphNode,
)


def test_canonical_and_extensible_organization_roles():
    canonical_roles = [
        OrganizationRoleType.FRONTEND,
        OrganizationRoleType.BACKEND,
        OrganizationRoleType.DATABASE,
        OrganizationRoleType.SECURITY,
        OrganizationRoleType.QA,
        OrganizationRoleType.DEVOPS,
        OrganizationRoleType.ARCHITECTURE,
        OrganizationRoleType.DOCUMENTATION,
        OrganizationRoleType.REVIEWER,
        OrganizationRoleType.RESEARCH,
        OrganizationRoleType.MOBILE,
        OrganizationRoleType.AI,
        OrganizationRoleType.INFRASTRUCTURE,
    ]
    assert len(canonical_roles) == 13

    # Custom extensible role
    role = OrganizationRole(
        role_id="role-sec-01",
        role_type=OrganizationRoleType.SECURITY,
        title="Security Lead",
        description="Responsible for security auditing and code analysis",
        primary_responsibility="Security auditing",
        inputs=["source_code"],
        outputs=["security_audit_report"],
        boundaries=["No production deployment"],
        allowed_capabilities=["cap-sec-audit"],
    )
    assert role.role_type == "security"

    custom_role = OrganizationRole(
        role_id="role-quantum-01",
        role_type="quantum_computing_specialist",
        title="Quantum Algorithm Specialist",
        description="Extensible custom domain role",
        primary_responsibility="Quantum circuit optimization",
    )
    assert custom_role.role_type == "quantum_computing_specialist"


def test_capability_models():
    cap = Capability(
        capability_id="cap-be-fastapi",
        name="FastAPI Backend Development",
        domain="backend",
        description="REST API development using Python FastAPI framework",
        required_skills=["skill-python-fastapi"],
    )
    group = CapabilityGroup(
        group_id="grp-be",
        name="Backend Engineering Group",
        domain="backend",
        description="Group of backend engineering capabilities",
        capabilities=[cap],
    )
    constraint = CapabilityConstraint(
        constraint_id="cst-001",
        capability_id=cap.capability_id,
        local_only=True,
    )
    req = CapabilityRequirement(
        requirement_id="req-001",
        mission_id="msn-001",
        capability_id=cap.capability_id,
        priority=CapabilityPriority.CRITICAL,
        source_requirement="Build backend API",
        constraints=[constraint],
    )
    evidence = CapabilityEvidence(
        evidence_id="ev-001",
        capability_id=cap.capability_id,
        asserted_by="CapabilityAnalyzer",
        provenance_details={"rule": "keyword_match"},
    )
    report = CapabilityReport(
        report_id="rep-cap-001",
        mission_id="msn-001",
        total_capabilities_analyzed=1,
        capabilities=[cap],
        groups=[group],
        requirements=[req],
        evidence=[evidence],
    )

    assert report.total_capabilities_analyzed == 1
    assert report.requirements[0].priority == CapabilityPriority.CRITICAL
    assert report.requirements[0].constraints[0].local_only is True


def test_organization_models():
    role_be = OrganizationRole(
        role_id="role-be",
        role_type=OrganizationRoleType.BACKEND,
        title="Backend Engineer",
        description="Implements API services",
        primary_responsibility="API implementation",
    )
    member_be = OrganizationMember(
        member_id="mem-be-01",
        role=role_be,
        capability_ids=["cap-be-fastapi"],
        status=MemberStatus.READY,
    )
    hierarchy = OrganizationHierarchy(
        reporting_relationships=[{"subordinate_id": "mem-be-01", "supervisor_id": "mem-eng-dir"}]
    )
    dependency = OrganizationDependency(
        dependency_id="dep-001",
        source_member_id="mem-db-01",
        target_member_id="mem-be-01",
        dependency_type=DependencyType.BLOCKING,
        description="Database schema must be provisioned before API service",
    )
    graph = OrganizationGraph(
        nodes=[member_be],
        edges=[dependency],
        reporting_links=[{"subordinate": "mem-be-01", "supervisor": "mem-eng-dir"}],
    )
    evidence = OrganizationEvidence(
        evidence_id="ev-org-001",
        decision_summary="Allocated backend member mem-be-01",
    )
    org_report = OrganizationReport(
        report_id="rep-org-001",
        organization_id="org-msn-001",
        total_members=1,
        total_roles=1,
        total_dependencies=1,
        summary="Organization validated successfully",
    )
    org = Organization(
        organization_id="org-msn-001",
        name="SaaS Web App Engineering Swarm",
        mission_id="msn-001",
        roles=[role_be],
        members=[member_be],
        hierarchy=hierarchy,
        dependencies=[dependency],
        graph=graph,
        evidence=[evidence],
        report=org_report,
    )

    assert org.organization_id == "org-msn-001"
    assert org.members[0].status == MemberStatus.READY
    assert org.dependencies[0].dependency_type == DependencyType.BLOCKING


def test_swarm_graph_hierarchy_perspectives():
    node_a = SwarmGraphNode(
        node_id="n-01",
        member_id="mem-arch-01",
        role_id="role-arch",
        domain="architecture",
    )
    node_b = SwarmGraphNode(
        node_id="n-02",
        member_id="mem-be-01",
        role_id="role-be",
        domain="backend",
    )
    edge = SwarmGraphEdge(
        edge_id="e-01",
        source_node_id="n-01",
        target_node_id="n-02",
        edge_type=EdgeType.DEPENDENCY,
    )
    rep_hier = ReportingHierarchy(supervisor_subordinate_pairs=[{"supervisor_id": "mem-arch-01", "subordinate_id": "mem-be-01"}])
    exec_hier = ExecutionHierarchy(execution_levels=[["mem-arch-01"], ["mem-be-01"]])
    rev_hier = ReviewHierarchy(review_pairs=[{"author_member_id": "mem-be-01", "reviewer_member_id": "mem-arch-01"}])
    app_hier = ApprovalHierarchy(approval_gates=[{"gate_id": "gate-arch-signoff", "approver_id": "mem-arch-01"}])

    swarm_graph = SwarmGraph(
        graph_id="sg-msn-001",
        mission_id="msn-001",
        organization_id="org-msn-001",
        nodes=[node_a, node_b],
        edges=[edge],
        reporting_hierarchy=rep_hier,
        execution_hierarchy=exec_hier,
        review_hierarchy=rev_hier,
        approval_hierarchy=app_hier,
    )

    assert len(swarm_graph.nodes) == 2
    assert len(swarm_graph.edges) == 1
    assert swarm_graph.execution_hierarchy.execution_levels == [["mem-arch-01"], ["mem-be-01"]]


def test_execution_blueprint_assembly():
    # Setup dummy ExecutionRequest
    msn_req = MissionRequest(
        mission_id="msn-001",
        original_command="Build REST API",
        normalized_command="Build REST API",
        raw_prompt="Build REST API",
    )
    msn = Mission(
        mission_id="msn-001",
        name="Build REST API",
        request=msn_req,
        requirements=MissionRequirements(primary_goal="Build REST API"),
        constraints=MissionConstraints(),
        deliverables=MissionDeliverables(),
        context=MissionContext(
            workspace_id="ws-01",
            workspace_root=Path("/tmp/ws"),
            engine_root=Path("/opt/oniroute"),
        ),
        status=MissionStatus(current_state=MissionState.PARSED),
    )
    exec_req = ExecutionRequest(
        request_id="exreq-001",
        mission=msn,
        mission_context=msn.context,
        mission_constraints=msn.constraints,
        execution_evidence=msn.evidence,
    )

    cap_report = CapabilityReport(report_id="rep-01", mission_id="msn-001")
    role = OrganizationRole(
        role_id="r-be",
        role_type=OrganizationRoleType.BACKEND,
        title="Backend Engineer",
        description="Backend API authoring",
        primary_responsibility="API development",
    )
    org = Organization(
        organization_id="org-msn-001",
        name="API Engineering Swarm",
        mission_id="msn-001",
        roles=[role],
    )
    sg = SwarmGraph(graph_id="sg-001", mission_id="msn-001", organization_id="org-msn-001")
    readiness = ExecutionReadiness(is_ready=True)

    blueprint = ExecutionBlueprint(
        blueprint_id="blp-msn-001",
        organization=org,
        mission=exec_req.mission,
        capabilities=cap_report,
        dependencies=sg,
        readiness=readiness,
        execution_metadata={"env": "test"},
    )

    assert blueprint.blueprint_id == "blp-msn-001"
    assert blueprint.mission.mission_id == "msn-001"
    assert blueprint.readiness.is_ready is True


def test_documentation_files_exist():
    docs_dir = Path(__file__).resolve().parents[2] / "docs"
    expected_files = [
        "ORGANIZATION_BUILDER.md",
        "CAPABILITY_MODEL.md",
        "SWARM_GRAPH.md",
        "EXECUTION_BLUEPRINT.md",
        "ORGANIZATION_ARCHITECTURE.md",
    ]
    for filename in expected_files:
        filepath = docs_dir / filename
        assert filepath.exists(), f"Missing required architecture doc: {filename}"
        assert filepath.stat().st_size > 100, f"Doc file {filename} is empty or insufficient"
