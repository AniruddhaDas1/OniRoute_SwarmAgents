from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class SkillPriority(str, Enum):
    """Priority levels for ranked skills."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    OPTIONAL = "OPTIONAL"
    SUPPORT = "SUPPORT"


class DiscoveredSkill(BaseModel):
    """Metadata representation of a discovered skill."""

    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(description="Unique identifier of the skill record")
    name: str = Field(description="Skill canonical name")
    display_name: str = Field(description="Human-readable display name")
    category: str = Field(description="Skill category")
    tags: List[str] = Field(default_factory=list, description="Skill tags")
    discovery_reason: str = Field(description="Reason for discovering this skill")
    required_knowledge: List[str] = Field(default_factory=list, description="Knowledge requirements")
    required_packages: List[str] = Field(default_factory=list, description="Package requirements")
    required_mcp_tools: List[str] = Field(default_factory=list, description="MCP tool requirements")
    path: str = Field(default="", description="Path to skill definition")


class RankedSkill(BaseModel):
    """Immutable metadata representation of a ranked skill."""

    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(description="Unique identifier of the skill record")
    name: str = Field(description="Skill canonical name")
    display_name: str = Field(description="Human-readable display name")
    category: str = Field(description="Skill category")
    rank: int = Field(description="1-indexed rank position")
    priority: SkillPriority = Field(description="Assigned priority level")
    score: float = Field(description="Deterministic weighted score (0.0 to 100.0)")
    ranking_reason: str = Field(description="Reason for score and priority assignment")
    score_breakdown: Dict[str, float] = Field(default_factory=dict, description="Breakdown of individual scoring factors")
    dependencies: List[str] = Field(default_factory=list, description="Prerequisite skill identifiers")
    knowledge_references: List[str] = Field(default_factory=list, description="Knowledge source references")
    package_references: List[str] = Field(default_factory=list, description="Package references")
    workflow_references: List[str] = Field(default_factory=list, description="Workflow references")
    path: str = Field(default="", description="Path to skill definition")
    is_official: bool = Field(default=False, description="Whether skill is an official registry skill")


class DependencyChain(BaseModel):
    """Dependency relationships and chain structure for a ranked skill."""

    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(description="Target skill identifier")
    prerequisites: List[str] = Field(default_factory=list, description="Skills that must execute prior to target")
    blocking: List[str] = Field(default_factory=list, description="Skills dependent on target")
    is_blocking: bool = Field(default=False, description="True if target skill blocks other skills")
    is_independent: bool = Field(default=False, description="True if target skill has no prerequisites or dependent skills")


class SkillCoverage(BaseModel):
    """Metrics measuring skill discovery coverage against plan requirements."""

    model_config = ConfigDict(frozen=True)

    required_skills: List[str] = Field(default_factory=list, description="List of required skill capability domains")
    discovered_skills: List[str] = Field(default_factory=list, description="List of discovered skill identifiers")
    missing_skills: List[str] = Field(default_factory=list, description="Expected skill capability domains missing from registry")
    coverage_percent: float = Field(description="Percentage of required skill capabilities covered (0.0 to 100.0)")
    registry_hits: int = Field(description="Total count of skills matched in registry")


class SkillSelectionReport(BaseModel):
    """Immutable report containing discovered skills for an EngineeringExecutionPlan."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(description="Unique report identifier")
    execution_plan_id: str = Field(description="Associated EngineeringExecutionPlan identifier")
    discovered_skills: List[DiscoveredSkill] = Field(default_factory=list, description="All discovered skill records")
    discovery_reasons: Dict[str, List[str]] = Field(default_factory=dict, description="Reasons for discovery mapped by skill ID")
    skill_categories: Dict[str, List[str]] = Field(default_factory=dict, description="Skill IDs grouped by category")
    required_knowledge: List[str] = Field(default_factory=list, description="Consolidated required knowledge sources")
    required_packages: List[str] = Field(default_factory=list, description="Consolidated required packages")
    required_mcp_tools: List[str] = Field(default_factory=list, description="Consolidated required MCP tools")
    coverage: SkillCoverage = Field(description="Coverage metrics")
    confidence: float = Field(description="Overall skill selection confidence score")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Discovery evidence and metadata")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")


class RankedSkillReport(BaseModel):
    """Immutable report containing deterministically ranked skills and execution ordering."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(description="Unique report identifier")
    selection_report_id: str = Field(description="Associated SkillSelectionReport identifier")
    execution_plan_id: str = Field(description="Associated EngineeringExecutionPlan identifier")
    ranked_skills: List[RankedSkill] = Field(default_factory=list, description="Deterministically ranked skill records")
    priority_groups: Dict[str, List[str]] = Field(default_factory=dict, description="Skill IDs grouped by SkillPriority")
    dependency_chains: List[DependencyChain] = Field(default_factory=list, description="Dependency chains for all ranked skills")
    recommended_execution_order: List[str] = Field(default_factory=list, description="Recommended topological execution order")
    blocking_skills: List[str] = Field(default_factory=list, description="Skill IDs that block other skills")
    independent_skills: List[str] = Field(default_factory=list, description="Skill IDs with no prerequisites or dependents")
    knowledge_references: List[str] = Field(default_factory=list, description="Consolidated knowledge references")
    package_references: List[str] = Field(default_factory=list, description="Consolidated package references")
    workflow_references: List[str] = Field(default_factory=list, description="Consolidated workflow references")
    coverage: SkillCoverage = Field(description="Preserved discovery coverage metrics")
    confidence: float = Field(description="Overall skill ranking confidence score")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Ranking evidence and metadata")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")


class ExecutionSkillBundle(BaseModel):
    """Immutable bundle grouping ranked skills by engineering discipline."""

    model_config = ConfigDict(frozen=True)

    bundle_id: str = Field(description="Unique bundle identifier")
    name: str = Field(description="Human-readable bundle name")
    engineering_discipline: str = Field(description="Associated engineering discipline")
    ranked_skills: List[RankedSkill] = Field(default_factory=list, description="Ranked skills assigned to this bundle")
    knowledge_references: List[str] = Field(default_factory=list, description="Consolidated knowledge references")
    package_references: List[str] = Field(default_factory=list, description="Consolidated package references")
    workflow_references: List[str] = Field(default_factory=list, description="Consolidated workflow references")
    registry_references: List[str] = Field(default_factory=list, description="Skill registry IDs in bundle")
    execution_constraints: List[str] = Field(default_factory=list, description="Disciplined execution constraints")
    expected_deliverables: List[str] = Field(default_factory=list, description="Expected deliverables for this bundle")
    dependency_bundles: List[str] = Field(default_factory=list, description="Prerequisite bundle IDs")
    priority: SkillPriority = Field(description="Highest priority level among bundled skills")
    coverage: float = Field(description="Discipline coverage percentage (0.0 to 100.0)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Bundle evidence and metadata")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")


class ExecutionSkillBundleReport(BaseModel):
    """Immutable report containing grouped execution skill bundles and bundle ordering."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(description="Unique bundle report identifier")
    execution_plan_id: str = Field(description="Associated EngineeringExecutionPlan identifier")
    ranked_report_id: str = Field(description="Associated RankedSkillReport identifier")
    selection_report_id: str = Field(description="Associated SkillSelectionReport identifier")
    bundles: List[ExecutionSkillBundle] = Field(default_factory=list, description="All execution skill bundles")
    bundle_ordering: List[str] = Field(default_factory=list, description="Recommended topological bundle execution order")
    bundle_dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Bundle dependency mapping")
    coverage: SkillCoverage = Field(description="Preserved skill coverage metrics")
    confidence: float = Field(description="Overall bundling confidence score")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Bundling evidence and validation results")
    timestamp: str = Field(description="ISO 8601 UTC timestamp")


