"""Implementation Allocation Data Contracts (Phase P4.G3)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class ImplementationPriority(str, Enum):
    """Implementation priority levels for allocated engineering targets."""

    P0_CRITICAL = "P0_CRITICAL"
    P1_HIGH = "P1_HIGH"
    P2_MEDIUM = "P2_MEDIUM"
    P3_LOW = "P3_LOW"


class AllocationTarget(BaseModel):
    """Immutable record defining an implementation target allocated to a discipline and agent profile."""

    model_config = ConfigDict(frozen=True)

    target_id: str = Field(..., description="Unique allocation target identifier (tgt-xxxxxx)")
    target_type: str = Field(..., description="Target type (file, directory, module, component, config, doc, test, asset, shared)")
    relative_path: str = Field(..., description="Relative workspace path of the target")
    owning_discipline: str = Field(..., description="Owning engineering discipline")
    owning_profile_id: str = Field(..., description="Owning agent profile ID (e.g. prf-fe-spec)")
    owning_profile_role: str = Field(..., description="Owning agent profile role title (e.g. Frontend Specialist)")
    expected_deliverable: str = Field(..., description="Expected deliverable description")
    priority: str = Field(default="P1_HIGH", description="Implementation priority (P0_CRITICAL, P1_HIGH, P2_MEDIUM, P3_LOW)")
    dependencies: List[str] = Field(default_factory=list, description="Target IDs this target depends on")


class ImplementationAllocationReport(BaseModel):
    """Immutable Implementation Allocation Report contract produced by ImplementationAllocationEngine."""

    model_config = ConfigDict(frozen=True)

    allocation_id: str = Field(..., description="Unique allocation report identifier (alloc-xxxxxx)")
    blueprint_id: str = Field(..., description="Associated ProjectBlueprintReport identifier")
    workspace_id: str = Field(..., description="Target workspace identifier")
    workspace_root: str = Field(..., description="Absolute workspace root path string")
    technology_stack: str = Field(..., description="Target technology stack")
    allocated_targets: List[AllocationTarget] = Field(default_factory=list, description="All allocated implementation targets")
    agent_ownership: Dict[str, List[str]] = Field(default_factory=dict, description="Mapping of agent profile ID to owned target IDs/paths")
    discipline_ownership: Dict[str, List[str]] = Field(default_factory=dict, description="Mapping of engineering discipline to owned target IDs/paths")
    expected_deliverables: List[str] = Field(default_factory=list, description="Consolidated list of expected engineering deliverables")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Target dependency DAG mapping target_id to dependency target_ids")
    execution_order: List[str] = Field(default_factory=list, description="Topologically sorted execution order of target IDs")
    coverage: Dict[str, Any] = Field(default_factory=dict, description="Target allocation coverage metrics")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence, performance metrics, and audit log")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of allocation completion")
    allocation_hash: str = Field(..., description="SHA-256 hash of allocation structure and manifest")
