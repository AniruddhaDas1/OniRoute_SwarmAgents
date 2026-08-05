"""Deterministic Organization Assembler for OniRoute Organization Builder (ACR-005 Phase S3).

Transforms a validated CapabilityReport into a complete, structured engineering Organization:
- Resolves canonical and extensible engineering roles
- Allocates OrganizationMember entries with registry-linked skills, knowledge, packages, and workflows
- Assembles structural departments (Executive, Engineering, Platform, Architecture, Security, QA, Documentation, Operations, Research)
- Constructs reporting and dependency hierarchies
- Validates the organization structure

Contains NO agent runtime execution, NO workflow execution, and NO AI model calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.loader import RepositoryLoader
from runtime.mission.models import ExecutionRequest
from runtime.resolver import Resolver

from .capability import Capability, CapabilityReport
from .contracts import OrganizationBuilderContract
from .models import (
    DependencyType,
    MemberStatus,
    Organization,
    OrganizationDependency,
    OrganizationEvidence,
    OrganizationGraph,
    OrganizationHierarchy,
    OrganizationMember,
    OrganizationReport,
)
from .organization_validator import OrganizationValidator
from .roles import OrganizationRole, OrganizationRoleType


class OrganizationAssembler(OrganizationBuilderContract):
    """Deterministic Organization Assembler engine."""

    def __init__(self, repository_root: Path | str | None = None) -> None:
        self.repository_root = Path(repository_root).resolve() if repository_root else Path.cwd()
        self._loader: RepositoryLoader | None = None
        self._resolver: Resolver | None = None

    def _get_resolver(self) -> Resolver:
        if self._resolver is None:
            self._loader = RepositoryLoader(self.repository_root)
            registry = self._loader.load()
            self._resolver = Resolver(registry)
        return self._resolver

    def build_organization(
        self, execution_request: ExecutionRequest, capability_report: CapabilityReport
    ) -> Organization:
        """Alias satisfying OrganizationBuilderContract interface."""
        return self.assemble_organization(capability_report, mission_id=execution_request.mission.mission_id)

    def assemble_organization(
        self, capability_report: CapabilityReport, mission_id: str | None = None
    ) -> Organization:
        """Assemble a complete Organization from a validated CapabilityReport."""
        resolver = self._get_resolver()
        msn_id = mission_id or capability_report.mission_id
        org_id = f"org-{msn_id}"

        # 1. Group capabilities by domain
        domain_caps: dict[str, list[Capability]] = {}
        for cap in capability_report.capabilities:
            domain_caps.setdefault(cap.domain.lower(), []).append(cap)

        roles: list[OrganizationRole] = []
        members: list[OrganizationMember] = []
        departments: dict[str, list[str]] = {}
        reporting_pairs: list[dict[str, str]] = []
        dependencies: list[OrganizationDependency] = []
        org_evidence: list[OrganizationEvidence] = []

        # Executive Director Member
        exec_role = OrganizationRole(
            role_id="role-executive-director",
            role_type=OrganizationRoleType.CUSTOM,
            title="Executive Director",
            description="Strategic oversight, governance, and organization alignment",
            primary_responsibility="Strategic alignment and governance sign-off",
            inputs=["mission_request"],
            outputs=["strategic_direction"],
            boundaries=["No direct code implementation"],
        )
        exec_member = OrganizationMember(
            member_id="mem-executive-01",
            role=exec_role,
            responsibilities=["Strategic context oversight", "Executive sign-off"],
            status=MemberStatus.READY,
        )
        roles.append(exec_role)
        members.append(exec_member)
        departments.setdefault("Executive", []).append(exec_member.member_id)

        # Domain to role mapping configuration
        role_type_map = {
            "architecture": (OrganizationRoleType.ARCHITECTURE, "Systems Architect", "Architecture"),
            "backend": (OrganizationRoleType.BACKEND, "Backend Engineer", "Engineering"),
            "frontend": (OrganizationRoleType.FRONTEND, "Frontend Engineer", "Engineering"),
            "database": (OrganizationRoleType.DATABASE, "Database Engineer", "Engineering"),
            "security": (OrganizationRoleType.SECURITY, "Security Engineer", "Security"),
            "testing": (OrganizationRoleType.QA, "QA Engineer", "QA"),
            "qa": (OrganizationRoleType.QA, "QA Lead", "QA"),
            "devops": (OrganizationRoleType.DEVOPS, "DevOps Engineer", "Platform"),
            "infrastructure": (OrganizationRoleType.INFRASTRUCTURE, "Infrastructure Lead", "Platform"),
            "documentation": (OrganizationRoleType.DOCUMENTATION, "Technical Writer", "Documentation"),
            "reviewer": (OrganizationRoleType.REVIEWER, "Code Reviewer", "Engineering"),
            "research": (OrganizationRoleType.RESEARCH, "Research Engineer", "Research"),
            "ai": (OrganizationRoleType.AI, "AI Engineer", "Engineering"),
            "mobile": (OrganizationRoleType.MOBILE, "Mobile Engineer", "Engineering"),
            "analytics": (OrganizationRoleType.CUSTOM, "Analytics Engineer", "Operations"),
            "automation": (OrganizationRoleType.CUSTOM, "Automation Specialist", "Operations"),
        }

        # 2. Assemble Roles and Members per domain
        member_by_domain: dict[str, OrganizationMember] = {}

        for domain, caps in domain_caps.items():
            role_enum, default_title, dept_name = role_type_map.get(
                domain, (OrganizationRoleType.CUSTOM, f"{domain.capitalize()} Specialist", "Engineering")
            )
            role_id = f"role-{domain}-lead"

            # Aggregate required skills, knowledge, packages, workflows from capabilities & registry
            all_skills: set[str] = set()
            all_know: set[str] = set()
            all_pkgs: set[str] = set()
            all_wfs: set[str] = set()
            cap_ids: list[str] = []
            resps: list[str] = []

            for cap in caps:
                cap_ids.append(cap.capability_id)
                resps.append(cap.name)
                all_skills.update(cap.required_skills)
                all_know.update(cap.required_knowledge)
                all_pkgs.update(cap.required_packages)
                all_wfs.update(cap.required_workflows)

            # Query registry for additional matching skills if list is small
            if len(all_skills) < 2:
                reg_matches = resolver.search(domain)
                all_skills.update(m.id for m in reg_matches[:3])

            role = OrganizationRole(
                role_id=role_id,
                role_type=role_enum if isinstance(role_enum, OrganizationRoleType) else domain,
                title=default_title,
                description=f"Responsible for engineering tasks in domain '{domain}'",
                primary_responsibility=f"Lead engineering deliverables for {domain}",
                inputs=[c.capability_id for c in caps],
                outputs=[f"artifact_{domain}_output"],
                boundaries=[f"Strictly bounded to {domain} domain"],
                allowed_capabilities=cap_ids,
            )
            roles.append(role)

            member_id = f"mem-{domain}-01"
            member_evidence = OrganizationEvidence(
                evidence_id=f"ev-mem-{member_id}",
                source_stage="member_allocation",
                asserted_by="OrganizationAssembler",
                decision_summary=f"Allocated member {member_id} for role {role_id}",
                evidence_payload={"domain": domain, "capability_count": len(cap_ids)},
            )
            org_evidence.append(member_evidence)

            member = OrganizationMember(
                member_id=member_id,
                role=role,
                responsibilities=resps,
                capability_ids=cap_ids,
                required_capabilities=cap_ids,
                required_skills=sorted(list(all_skills))[:5],
                knowledge_references=sorted(list(all_know))[:5],
                package_references=sorted(list(all_pkgs))[:5],
                workflow_references=sorted(list(all_wfs))[:5],
                status=MemberStatus.ALLOCATED,
                evidence=[member_evidence],
            )
            members.append(member)
            member_by_domain[domain] = member
            departments.setdefault(dept_name, []).append(member.member_id)

            # Reporting link to Executive
            reporting_pairs.append({"subordinate_id": member_id, "supervisor_id": exec_member.member_id})

        # 3. Construct Inter-Member Dependencies
        dep_counter = 1
        for cap in capability_report.capabilities:
            t_domain = cap.domain.lower()
            if t_domain in member_by_domain:
                target_mem = member_by_domain[t_domain]
                for dep_cap_id in cap.dependencies:
                    # Find source capability & member
                    source_cap = next((c for c in capability_report.capabilities if c.capability_id == dep_cap_id), None)
                    if source_cap and source_cap.domain.lower() in member_by_domain:
                        source_mem = member_by_domain[source_cap.domain.lower()]
                        if source_mem.member_id != target_mem.member_id:
                            dep_obj = OrganizationDependency(
                                dependency_id=f"dep-{dep_counter:03d}",
                                source_member_id=source_mem.member_id,
                                target_member_id=target_mem.member_id,
                                dependency_type=DependencyType.BLOCKING,
                                description=f"{target_mem.role.title} depends on {source_mem.role.title} ({source_cap.name})",
                            )
                            dependencies.append(dep_obj)
                            dep_counter += 1

        # 4. Construct Hierarchy & Graph
        hierarchy = OrganizationHierarchy(
            executive_department="Executive",
            engineering_department="Engineering",
            platform_department="Platform",
            reporting_relationships=reporting_pairs,
        )

        graph = OrganizationGraph(
            nodes=members,
            edges=dependencies,
            reporting_links=reporting_pairs,
        )

        org_unvalidated = Organization(
            organization_id=org_id,
            name=f"Engineering Swarm Organization ({msn_id})",
            mission_id=msn_id,
            departments=departments,
            roles=roles,
            members=members,
            hierarchy=hierarchy,
            dependencies=dependencies,
            graph=graph,
            evidence=org_evidence,
        )

        # 5. Organization Validation
        validator = OrganizationValidator()
        report = validator.validate_organization(org_unvalidated)

        readiness_summary: dict[str, Any] = {
            "is_ready": report.structural_integrity_verified,
            "total_members": len(members),
            "total_roles": len(roles),
            "total_departments": len(departments),
            "total_dependencies": len(dependencies),
            "structural_integrity_passed": report.structural_integrity_verified,
        }

        org_unvalidated.report = report
        org_unvalidated.readiness = readiness_summary

        return org_unvalidated
