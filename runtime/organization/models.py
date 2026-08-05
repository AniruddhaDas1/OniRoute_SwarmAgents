"""Immutable organization models for OniRoute Organization Builder (ACR-005 Phase S1).

Provides declarative Pydantic models representing the engineering organization structure,
members, roles, hierarchy, dependencies, and evidence without runtime execution logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .capability import CapabilityReport
from .roles import OrganizationRole


class MemberStatus(str, Enum):
    """Lifecycle status of an organization member assignment."""

    PROPOSED = "proposed"
    ALLOCATED = "allocated"
    READY = "ready"
    ACTIVE = "active"
    RELEASED = "released"


class DependencyType(str, Enum):
    """Types of inter-member or inter-role engineering dependencies."""

    DATA = "data"
    INTERFACE = "interface"
    BLOCKING = "blocking"
    REVIEW = "review"
    APPROVAL = "approval"
    INFORMATIONAL = "informational"


class OrganizationMember(BaseModel):
    """Individual member/agent slot assigned within a role."""

    member_id: str = Field(..., description="Unique member identifier (e.g. member-backend-01)")
    role: OrganizationRole = Field(..., description="Assigned engineering role definition")
    responsibilities: list[str] = Field(default_factory=list, description="Explicit responsibilities assigned to this member")
    capability_ids: list[str] = Field(default_factory=list, description="Capabilities assigned to this member")
    required_capabilities: list[str] = Field(default_factory=list, description="Required capabilities fulfilled by member")
    required_skills: list[str] = Field(default_factory=list, description="Resolved required skill references")
    knowledge_references: list[str] = Field(default_factory=list, description="Resolved knowledge references")
    package_references: list[str] = Field(default_factory=list, description="Resolved package references")
    workflow_references: list[str] = Field(default_factory=list, description="Resolved workflow references")
    status: MemberStatus = Field(default=MemberStatus.ALLOCATED, description="Member allocation status")
    evidence: list[OrganizationEvidence] = Field(default_factory=list, description="Evidence audit trail for member allocation")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible member metadata")


class OrganizationHierarchy(BaseModel):
    """Declarative reporting relationships and structural department hierarchy."""

    executive_department: str = Field(default="Executive", description="Top executive oversight entity")
    engineering_department: str = Field(default="Engineering", description="Core engineering coordination entity")
    platform_department: str = Field(default="Platform", description="Platform technology advisory entity")
    reporting_relationships: list[dict[str, str]] = Field(
        default_factory=list,
        description="Declarative reporting pairs mapping subordinate member_id to manager member_id",
    )
    discipline_departments: list[str] = Field(
        default_factory=lambda: [
            "Engineering",
            "Platform",
            "Architecture",
            "Security",
            "QA",
            "Documentation",
            "Operations",
            "Research",
            "Frontend",
            "Backend",
            "Database",
            "DevOps",
            "Infrastructure",
            "AI",
            "Mobile",
            "Analytics",
            "Automation",
        ],
        description="Canonical engineering discipline departments",
    )


class OrganizationDependency(BaseModel):
    """Directed dependency relationship between organization members or roles."""

    dependency_id: str = Field(..., description="Unique dependency identifier")
    source_member_id: str = Field(..., description="Member ID originating the dependency (upstream)")
    target_member_id: str = Field(..., description="Member ID depending on source (downstream)")
    dependency_type: DependencyType = Field(default=DependencyType.BLOCKING, description="Category of dependency")
    description: str = Field(..., description="Technical detail of dependency contract")
    constraint: str = Field(default="", description="Optional constraint or ordering requirement")


class OrganizationGraph(BaseModel):
    """Graph structure capturing members, roles, reporting links, and dependencies."""

    nodes: list[OrganizationMember] = Field(default_factory=list, description="Organization member nodes")
    edges: list[OrganizationDependency] = Field(default_factory=list, description="Dependency and relationship edges")
    reporting_links: list[dict[str, str]] = Field(
        default_factory=list, description="Directed reporting edges (subordinate -> supervisor)"
    )


class OrganizationEvidence(BaseModel):
    """Immutable audit record of organization synthesis decisions."""

    evidence_id: str = Field(..., description="Unique evidence record identifier")
    source_stage: str = Field(default="organization_assembly", description="Pipeline stage producing evidence")
    asserted_by: str = Field(default="OrganizationAssembler", description="Asserting component")
    decision_summary: str = Field(..., description="Summary of organizational structure decision")
    evidence_payload: dict[str, Any] = Field(default_factory=dict, description="Raw decision metadata snapshot")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of record creation",
    )


class OrganizationReport(BaseModel):
    """Audit summary report for the constructed engineering organization."""

    report_id: str = Field(..., description="Unique report identifier")
    organization_id: str = Field(..., description="Target organization identifier")
    total_members: int = Field(default=0, description="Total member count")
    total_roles: int = Field(default=0, description="Total role count")
    total_dependencies: int = Field(default=0, description="Total dependency count")
    total_departments: int = Field(default=0, description="Total department count")
    structural_integrity_verified: bool = Field(default=True, description="Organization validation status")
    summary: str = Field(..., description="Executive summary of organization topology")
    validation_details: dict[str, Any] = Field(default_factory=dict, description="Detailed validation check results")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp",
    )


class Organization(BaseModel):
    """Immutable top-level Organization model encapsulating complete swarm architecture."""

    organization_id: str = Field(..., description="Unique organization identifier (e.g. org-msn-1001)")
    name: str = Field(..., description="Organization display name")
    mission_id: str = Field(..., description="Associated mission identifier")
    departments: dict[str, list[str]] = Field(
        default_factory=dict, description="Departments mapping department name to list of member_ids"
    )
    roles: list[OrganizationRole] = Field(default_factory=list, description="Declared organization roles")
    members: list[OrganizationMember] = Field(default_factory=list, description="Allocated organization members")
    hierarchy: OrganizationHierarchy = Field(
        default_factory=OrganizationHierarchy, description="Department hierarchy & reporting lines"
    )
    dependencies: list[OrganizationDependency] = Field(
        default_factory=list, description="Inter-member engineering dependencies"
    )
    graph: OrganizationGraph = Field(default_factory=OrganizationGraph, description="Full organization graph")
    evidence: list[OrganizationEvidence] = Field(
        default_factory=list, description="Immutable organization audit evidence trail"
    )
    report: OrganizationReport | None = Field(default=None, description="Consolidated organization report")
    readiness: dict[str, Any] = Field(default_factory=dict, description="Readiness and structural integrity assessment")
