"""Project Blueprint Data Contracts (Phase P4.G2)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class EngineeringDiscipline(str, Enum):
    """Supported engineering disciplines for project module ownership."""

    FRONTEND = "Frontend"
    BACKEND = "Backend"
    DATABASE = "Database"
    INFRASTRUCTURE = "Infrastructure"
    SECURITY = "Security"
    TESTING = "Testing"
    DOCUMENTATION = "Documentation"
    AUTOMATION = "Automation"
    ANALYTICS = "Analytics"
    AI = "AI"
    SHARED = "Shared"


class ProjectModule(BaseModel):
    """Immutable record defining a project module allocated to an engineering discipline."""

    model_config = ConfigDict(frozen=True)

    module_id: str = Field(..., description="Unique module identifier (mod-xxxxxx)")
    name: str = Field(..., description="Human-readable module name")
    discipline: str = Field(..., description="Assigned engineering discipline")
    relative_path: str = Field(..., description="Relative workspace path for the module")
    description: str = Field(..., description="Module purpose and architectural role")
    components: List[str] = Field(default_factory=list, description="Logical components contained in this module")
    dependencies: List[str] = Field(default_factory=list, description="Module IDs this module depends on")


class ProjectBlueprintReport(BaseModel):
    """Immutable Project Blueprint Report contract produced by ProjectBlueprintEngine."""

    model_config = ConfigDict(frozen=True)

    blueprint_id: str = Field(..., description="Unique blueprint report identifier (blu-xxxxxx)")
    workspace_id: str = Field(..., description="Target workspace identifier")
    workspace_root: str = Field(..., description="Absolute path string of the workspace root")
    technology_stack: str = Field(..., description="Target technology stack")
    project_modules: List[ProjectModule] = Field(default_factory=list, description="All allocated project modules")
    directory_ownership: Dict[str, str] = Field(default_factory=dict, description="Mapping of directory paths to engineering disciplines")
    logical_components: List[Dict[str, Any]] = Field(default_factory=list, description="Logical software components mapped across modules")
    engineering_discipline_ownership: Dict[str, List[str]] = Field(default_factory=dict, description="Mapping of engineering discipline to owned directories and modules")
    technology_stack_mapping: Dict[str, Any] = Field(default_factory=dict, description="Detailed technology stack mapping")
    expected_files: List[str] = Field(default_factory=list, description="List of expected project files to be allocated in Phase P4.G3")
    expected_deliverables: List[str] = Field(default_factory=list, description="Expected engineering deliverables by discipline")
    dependencies: Dict[str, List[str]] = Field(default_factory=dict, description="Module dependency DAG mapping module_id to dependency module_ids")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence, performance metrics, and coverage summary")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of blueprint generation")
    blueprint_hash: str = Field(..., description="SHA-256 hash of blueprint structure and metadata")
