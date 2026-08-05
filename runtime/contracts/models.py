"""Engineering Contracts Data Contracts (Phase P4.G4)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class EngineeringContract(BaseModel):
    """Immutable record defining a single execution-ready engineering contract."""

    model_config = ConfigDict(frozen=True)

    contract_id: str = Field(..., description="Unique engineering contract identifier (ctr-xxxxxx)")
    target_path: str = Field(..., description="Target file or directory relative path")
    target_type: str = Field(..., description="Target type (file, directory, module, component, config, doc, test, asset, shared)")
    assigned_profile_id: str = Field(..., description="Assigned Agent Profile ID")
    assigned_profile_role: str = Field(..., description="Assigned Agent Profile Role Title")
    engineering_discipline: str = Field(..., description="Owning engineering discipline")
    input_dependencies: List[str] = Field(default_factory=list, description="Input contract dependencies and prerequisite target IDs")
    output_artifacts: List[str] = Field(default_factory=list, description="Expected output artifact paths")
    interface_constraints: Dict[str, Any] = Field(default_factory=dict, description="Interface & API contract constraints")
    architecture_constraints: List[str] = Field(default_factory=list, description="Architectural rules & boundaries")
    coding_standards: List[str] = Field(default_factory=list, description="Coding standards and formatting rules")
    naming_rules: List[str] = Field(default_factory=list, description="Symbol and file naming conventions")
    security_requirements: List[str] = Field(default_factory=list, description="Security and privacy rules")
    performance_expectations: Dict[str, Any] = Field(default_factory=dict, description="Performance latency/memory bounds")
    testing_requirements: List[str] = Field(default_factory=list, description="Unit and integration test requirements")
    documentation_requirements: List[str] = Field(default_factory=list, description="Inline and Markdown documentation requirements")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Concrete validation acceptance criteria")
    review_requirements: List[str] = Field(default_factory=list, description="Code review and approval gate requirements")
    generation_priority: str = Field(default="P1_HIGH", description="Priority level (P0_CRITICAL, P1_HIGH, P2_MEDIUM, P3_LOW)")
    execution_wave: int = Field(default=1, ge=1, le=6, description="Execution wave number (1-6)")
    contract_hash: str = Field(..., description="SHA-256 hash of single contract spec")


class EngineeringContractReport(BaseModel):
    """Immutable Engineering Contract Report contract produced by EngineeringContractEngine."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique engineering contract report identifier (ctrr-xxxxxx)")
    allocation_id: str = Field(..., description="Associated ImplementationAllocationReport identifier")
    workspace_id: str = Field(..., description="Target workspace identifier")
    workspace_root: str = Field(..., description="Absolute workspace root path string")
    technology_stack: str = Field(..., description="Target technology stack")
    contracts: List[EngineeringContract] = Field(default_factory=list, description="List of all generated engineering contracts")
    agent_contracts: Dict[str, List[str]] = Field(default_factory=dict, description="Mapping of Profile ID to assigned contract IDs")
    discipline_contracts: Dict[str, List[str]] = Field(default_factory=dict, description="Mapping of Engineering Discipline to assigned contract IDs")
    expected_outputs: List[str] = Field(default_factory=list, description="All expected output artifacts across contracts")
    execution_waves: Dict[int, List[str]] = Field(default_factory=dict, description="Execution wave mapping (wave_number -> contract_ids)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence, performance metrics, and audit log")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of contract generation completion")
    report_hash: str = Field(..., description="SHA-256 hash of report payload")
