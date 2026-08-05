"""Tests for Organization Assembly (ACR-005 Phase S3)."""

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
    Capability,
    CapabilityReport,
    CapabilityResolver,
    MemberStatus,
    Organization,
    OrganizationAssembler,
    OrganizationValidator,
)

runner = CliRunner()


def _get_test_capability_report() -> CapabilityReport:
    cap_arch = Capability(
        capability_id="cap-arch-01",
        name="Architecture Design",
        domain="architecture",
        description="System decomposition & architecture design",
    )
    cap_be = Capability(
        capability_id="cap-be-01",
        name="Backend API",
        domain="backend",
        description="FastAPI REST service",
        dependencies=["cap-arch-01"],
    )
    cap_fe = Capability(
        capability_id="cap-fe-01",
        name="Frontend UI",
        domain="frontend",
        description="React UI dashboard",
        dependencies=["cap-be-01"],
    )
    return CapabilityReport(
        report_id="rep-cap-test-101",
        mission_id="msn-test-101",
        total_capabilities_analyzed=3,
        capabilities=[cap_arch, cap_be, cap_fe],
    )


def test_organization_assembler_role_and_member_allocation():
    cap_report = _get_test_capability_report()
    assembler = OrganizationAssembler()
    org = assembler.assemble_organization(cap_report)

    assert isinstance(org, Organization)
    assert org.mission_id == "msn-test-101"
    assert len(org.members) >= 4  # Executive + Arch + Backend + Frontend
    assert len(org.roles) == len(org.members)

    arch_member = next(m for m in org.members if m.role.role_type == "architecture")
    assert arch_member.member_id == "mem-architecture-01"
    assert arch_member.status == MemberStatus.ALLOCATED
    assert "cap-arch-01" in arch_member.capability_ids
    assert len(arch_member.evidence) > 0


def test_department_assembly_and_hierarchy():
    cap_report = _get_test_capability_report()
    assembler = OrganizationAssembler()
    org = assembler.assemble_organization(cap_report)

    assert "Executive" in org.departments
    assert "Architecture" in org.departments or "Engineering" in org.departments

    assert len(org.hierarchy.reporting_relationships) > 0
    # Executive member should supervise subordinates
    exec_reports = [r for r in org.hierarchy.reporting_relationships if r["supervisor_id"] == "mem-executive-01"]
    assert len(exec_reports) >= 3


def test_organization_dependencies_mapping():
    cap_report = _get_test_capability_report()
    assembler = OrganizationAssembler()
    org = assembler.assemble_organization(cap_report)

    assert len(org.dependencies) > 0
    fe_be_dep = next(
        (d for d in org.dependencies if d.source_member_id == "mem-backend-01" and d.target_member_id == "mem-frontend-01"),
        None,
    )
    assert fe_be_dep is not None


def test_organization_validator():
    cap_report = _get_test_capability_report()
    assembler = OrganizationAssembler()
    org = assembler.assemble_organization(cap_report)

    validator = OrganizationValidator()
    report = validator.validate_organization(org)

    assert report.structural_integrity_verified is True
    assert report.validation_details["duplicate_members_count"] == 0
    assert len(report.validation_details["unallocated_roles"]) == 0


def test_cli_oniroute_organization_text():
    result = runner.invoke(app, ["organization", "Create CRM"])
    assert result.exit_code == 0
    assert "Assembled Organization" in result.output
    assert "Structural Integrity" in result.output


def test_cli_oniroute_organization_json():
    result = runner.invoke(app, ["organization", "--json", "Build REST API"])
    assert result.exit_code == 0
    assert '"organization_id":' in result.output
    assert '"members":' in result.output
    assert '"departments":' in result.output
    assert '"report":' in result.output
