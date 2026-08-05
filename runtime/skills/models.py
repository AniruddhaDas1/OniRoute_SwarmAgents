"""Data models for Automatic Skill Discovery (Phase P2.S1)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


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
