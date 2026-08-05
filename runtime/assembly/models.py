"""Project Assembly Certification Data Contracts (Phase P4.G5)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class ProjectAssemblyCertificationReport(BaseModel):
    """Immutable Project Assembly Certification Report contract produced by ProjectAssemblyCertificationEngine."""

    model_config = ConfigDict(frozen=True)

    certification_id: str = Field(..., description="Unique certification identifier (cert-p4-xxxxxx)")
    certified: bool = Field(..., description="True if complete Project Assembly pipeline passes all audits")
    scaffold_latency_ms: float = Field(..., description="Latency of WorkspaceScaffoldEngine in ms")
    blueprint_latency_ms: float = Field(..., description="Latency of ProjectBlueprintEngine in ms")
    allocation_latency_ms: float = Field(..., description="Latency of ImplementationAllocationEngine in ms")
    contracts_latency_ms: float = Field(..., description="Latency of EngineeringContractEngine in ms")
    total_assembly_latency_ms: float = Field(..., description="End-to-end Project Assembly pipeline latency in ms")
    memory_peak_kb: float = Field(..., description="Peak memory overhead in KB during assembly")
    determinism_verified: bool = Field(..., description="True if SHA-256 hashes are 100% reproducible across repeated runs")
    serialization_verified: bool = Field(..., description="True if JSON serialization/deserialization roundtrips pass 100%")
    pipeline_integrity_verified: bool = Field(..., description="True if reference integrity across scaffold, blueprint, allocation, and contracts is valid")
    zero_llm_invocations: bool = Field(default=True, description="True if 0 LLM calls occurred during assembly")
    zero_code_generation: bool = Field(default=True, description="True if 0 source code generation occurred during assembly")
    audited_contracts_count: int = Field(..., description="Total number of contracts audited in certification suite")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Detailed validation breakdown per technology stack")
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp of certification completion")
    certification_hash: str = Field(..., description="SHA-256 hash of certification report payload")
