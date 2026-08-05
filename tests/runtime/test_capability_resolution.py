"""Tests for Capability Resolution (ACR-005 Phase S2)."""

from pathlib import Path

import typer
from typer.testing import CliRunner

from cli.main import app
from runtime.mission import (
    ExecutionRequest,
    Mission,
    MissionConstraints,
    MissionContext,
    MissionDeliverables,
    MissionEvidence,
    MissionIntake,
    MissionOrchestrator,
    MissionRequest,
    MissionRequirements,
    MissionResolver,
    MissionState,
    MissionStatus,
)
from runtime.organization import (
    CapabilityConstraint,
    CapabilityEvidence,
    CapabilityPriority,
    CapabilityReport,
    CapabilityRequirement,
    CapabilityResolver,
    CapabilityValidator,
)

runner = CliRunner()


def test_capability_extraction_and_resolution():
    msn_req = MissionRequest(
        mission_id="msn-cap-101",
        original_command="Create a SaaS CRM with REST API and PostgreSQL database",
        normalized_command="Create a SaaS CRM with REST API and PostgreSQL database",
        raw_prompt="Create a SaaS CRM with REST API and PostgreSQL database",
    )
    msn = Mission(
        mission_id="msn-cap-101",
        name="Create SaaS CRM",
        request=msn_req,
        requirements=MissionRequirements(
            intent_category="create",
            primary_goal="Create a SaaS CRM with REST API and PostgreSQL database",
            functional_requirements=["Build REST API endpoints", "Design PostgreSQL schema", "Build React UI"],
            non_functional_requirements=["Audit code security", "Ensure high performance"],
        ),
        constraints=MissionConstraints(local_only=True, timeout_seconds=600),
        deliverables=MissionDeliverables(),
        context=MissionContext(
            workspace_id="ws-cap-01",
            workspace_root=Path("/tmp/ws"),
            engine_root=Path("/opt/oniroute"),
        ),
        status=MissionStatus(current_state=MissionState.PARSED),
    )
    exec_req = ExecutionRequest(
        request_id="exreq-cap-101",
        mission=msn,
        mission_context=msn.context,
        mission_constraints=msn.constraints,
        execution_evidence=MissionEvidence(),
    )

    resolver = CapabilityResolver()
    report = resolver.resolve_capabilities(exec_req)

    assert isinstance(report, CapabilityReport)
    assert report.mission_id == "msn-cap-101"
    assert report.total_capabilities_analyzed > 0
    assert len(report.capabilities) == report.total_capabilities_analyzed

    # Domain checks
    domains = {cap.domain for cap in report.capabilities}
    assert "architecture" in domains
    assert "backend" in domains
    assert "database" in domains
    assert "frontend" in domains

    # Priority check
    arch_cap = next(c for c in report.capabilities if c.domain == "architecture")
    assert arch_cap.priority == CapabilityPriority.CRITICAL


def test_capability_registry_lookup():
    resolver = CapabilityResolver()
    reg_resolver = resolver._get_resolver()

    # Verify existing registries are non-empty and queryable
    assert len(reg_resolver.registry.agents) > 0 or len(reg_resolver.registry.sub_agents) > 0
    assert len(reg_resolver.registry.skills) > 0
    assert len(reg_resolver.registry.workflows) > 0

    skills = reg_resolver.search("api")
    assert isinstance(skills, list)


def test_capability_constraint_handling():
    msn_req = MissionRequest(
        mission_id="msn-cst-102",
        original_command="Build REST API",
        normalized_command="Build REST API",
        raw_prompt="Build REST API",
    )
    msn = Mission(
        mission_id="msn-cst-102",
        name="Build REST API",
        request=msn_req,
        requirements=MissionRequirements(primary_goal="Build REST API"),
        constraints=MissionConstraints(local_only=True, allowed_providers=["ollama"], max_budget_usd=10.0),
        deliverables=MissionDeliverables(),
        context=MissionContext(
            workspace_id="ws-02",
            workspace_root=Path("/tmp/ws"),
            engine_root=Path("/opt/oniroute"),
        ),
        status=MissionStatus(current_state=MissionState.PARSED),
    )
    exec_req = ExecutionRequest(
        request_id="exreq-cst-102",
        mission=msn,
        mission_context=msn.context,
        mission_constraints=msn.constraints,
        execution_evidence=MissionEvidence(),
    )

    resolver = CapabilityResolver()
    report = resolver.resolve_capabilities(exec_req)

    assert len(report.capability_constraints) > 0
    global_cst = next(c for c in report.capability_constraints if c.capability_id == "global")
    assert global_cst.local_only is True
    assert "ollama" in global_cst.allowed_providers


def test_capability_validator_coverage_and_conflicts():
    validator = CapabilityValidator()

    req = CapabilityRequirement(
        requirement_id="req-01",
        mission_id="msn-val-01",
        capability_id="cap-be-01",
        source_requirement="Backend API",
    )
    evidence = CapabilityEvidence(
        evidence_id="ev-01",
        capability_id="cap-be-01",
        asserted_by="Test",
    )
    cst_pass = CapabilityConstraint(
        constraint_id="cst-01",
        capability_id="cap-be-01",
        local_only=True,
        allowed_providers=["local"],
    )

    from runtime.organization import Capability
    cap = Capability(
        capability_id="cap-be-01",
        name="Backend API",
        domain="backend",
        description="Backend API cap",
    )

    coverage, readiness = validator.validate_capability_set(
        capabilities=[cap],
        requirements=[req],
        constraints=[cst_pass],
        evidence_list=[evidence],
    )

    assert coverage["coverage_ratio"] == 1.0
    assert readiness["is_ready"] is True
    assert readiness["constraint_violations"] == 0

    # Conflict test
    cst_fail = CapabilityConstraint(
        constraint_id="cst-02",
        capability_id="cap-be-01",
        local_only=True,
        allowed_providers=["openai"],
    )

    _, readiness_fail = validator.validate_capability_set(
        capabilities=[cap],
        requirements=[req],
        constraints=[cst_fail],
        evidence_list=[evidence],
    )

    assert readiness_fail["is_ready"] is False
    assert readiness_fail["constraint_violations"] == 1


def test_cli_oniroute_capability_text():
    result = runner.invoke(app, ["capability", "Create a CRM"])
    assert result.exit_code == 0
    assert "Resolved Capability Report" in result.output
    assert "Capability Validation" in result.output
    assert "Readiness" in result.output


def test_cli_oniroute_capability_json():
    result = runner.invoke(app, ["capability", "--json", "Build REST API"])
    assert result.exit_code == 0
    assert '"report_id":' in result.output
    assert '"capabilities":' in result.output
    assert '"coverage_summary":' in result.output
    assert '"readiness":' in result.output
