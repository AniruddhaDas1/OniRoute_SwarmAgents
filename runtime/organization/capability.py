"""Immutable capability models for OniRoute Organization Builder (ACR-005 Phase S1).

Provides declarative schemas for analyzing, grouping, and constraining mission capabilities
without implementing capability resolution algorithms or runtime AI execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityPriority(str, Enum):
    """Priority level for capability requirements."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class Capability(BaseModel):
    """Discrete engineering domain or technical capability."""

    capability_id: str = Field(..., description="Unique capability identifier (e.g. cap-backend-fastapi)")
    name: str = Field(..., description="Human-readable capability name")
    domain: str = Field(..., description="Engineering domain category (e.g. backend, database, security)")
    description: str = Field(..., description="Detailed capability description")
    version: str = Field(default="1.0.0", description="Capability definition version")
    priority: CapabilityPriority = Field(default=CapabilityPriority.HIGH, description="Capability priority ranking")
    confidence: float = Field(default=1.0, description="Confidence score of resolution (0.0 to 1.0)")
    dependencies: list[str] = Field(default_factory=list, description="IDs of capabilities this capability depends on")
    required_skills: list[str] = Field(default_factory=list, description="Declarative required skill references")
    required_knowledge: list[str] = Field(default_factory=list, description="Declarative required knowledge references")
    required_packages: list[str] = Field(default_factory=list, description="Declarative required package references")
    required_workflows: list[str] = Field(default_factory=list, description="Declarative required workflow references")
    constraints: list[CapabilityConstraint] = Field(default_factory=list, description="Capability-level operational constraints")
    evidence: list[CapabilityEvidence] = Field(default_factory=list, description="Evidence records attached to this capability")
    is_optional: bool = Field(default=False, description="Flag indicating if capability is optional")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible capability metadata")


class CapabilityGroup(BaseModel):
    """Logical grouping of related engineering capabilities."""

    group_id: str = Field(..., description="Unique capability group identifier (e.g. capgrp-web-fullstack)")
    name: str = Field(..., description="Capability group name")
    domain: str = Field(..., description="Target domain area")
    description: str = Field(..., description="Group purpose and coverage")
    capabilities: list[Capability] = Field(default_factory=list, description="List of contained capabilities")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extensible metadata")


class CapabilityConstraint(BaseModel):
    """Operational and policy bounds restricting capability fulfillment."""

    constraint_id: str = Field(..., description="Unique constraint identifier")
    capability_id: str = Field(..., description="Target capability ID constrained by this rule")
    local_only: bool = Field(default=False, description="Flag requiring strictly local execution resources")
    allowed_providers: list[str] = Field(default_factory=list, description="Permitted model or execution providers")
    max_memory_mb: int | None = Field(default=None, description="Memory consumption boundary")
    max_duration_seconds: int | None = Field(default=None, description="Time boundary in seconds")
    security_clearance_level: str = Field(default="standard", description="Required security authorization tier")
    custom_rules: dict[str, Any] = Field(default_factory=dict, description="Additional custom constraint parameters")


class CapabilityRequirement(BaseModel):
    """Formal capability requirement derived from an ExecutionRequest."""

    requirement_id: str = Field(..., description="Unique capability requirement identifier")
    mission_id: str = Field(..., description="Source mission identifier")
    capability_id: str = Field(..., description="Target capability ID required")
    priority: CapabilityPriority = Field(default=CapabilityPriority.HIGH, description="Requirement priority level")
    source_requirement: str = Field(..., description="Description of mission requirement prompting this capability")
    constraints: list[CapabilityConstraint] = Field(default_factory=list, description="Associated capability constraints")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CapabilityEvidence(BaseModel):
    """Immutable audit record of capability analysis and provenance."""

    evidence_id: str = Field(..., description="Unique evidence record identifier")
    capability_id: str = Field(..., description="Target capability ID")
    source_stage: str = Field(default="capability_resolution", description="Analysis pipeline stage")
    asserted_by: str = Field(..., description="Component asserting capability (e.g. CapabilityResolver)")
    provenance_details: dict[str, Any] = Field(default_factory=dict, description="Provenance and reasoning metadata")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of assertion",
    )


class CapabilityReport(BaseModel):
    """Consolidated audit summary report of all assessed mission capabilities."""

    report_id: str = Field(..., description="Unique report identifier")
    mission_id: str = Field(..., description="Associated mission identifier")
    total_capabilities_analyzed: int = Field(default=0, description="Total count of analyzed capabilities")
    capabilities: list[Capability] = Field(default_factory=list, description="List of identified capabilities")
    groups: list[CapabilityGroup] = Field(default_factory=list, description="List of capability groups")
    requirements: list[CapabilityRequirement] = Field(default_factory=list, description="Required capability specifications")
    evidence: list[CapabilityEvidence] = Field(default_factory=list, description="Collected capability evidence records")
    capability_priorities: dict[str, str] = Field(default_factory=dict, description="Mapping of capability_id to priority string")
    capability_constraints: list[CapabilityConstraint] = Field(default_factory=list, description="Consolidated capability constraints")
    dependency_summary: dict[str, list[str]] = Field(default_factory=dict, description="Directed dependency mapping between capabilities")
    coverage_summary: dict[str, Any] = Field(default_factory=dict, description="Summary of domain coverage and requirement mappings")
    readiness: dict[str, Any] = Field(default_factory=dict, description="Readiness assessment and validation status")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Report generation timestamp",
    )
