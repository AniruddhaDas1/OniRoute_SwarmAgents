"""Autonomous Engineering Worker Data Contracts (Phase P5.E1 & Phase P5.E5)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class EngineeringResult(BaseModel):
    """Immutable Engineering Result contract produced by EngineeringWorkerEngine."""

    model_config = ConfigDict(frozen=True)

    result_id: str = Field(..., description="Unique engineering execution result ID (engres-xxxxxx)")
    contract_id: str = Field(..., description="Associated EngineeringContract ID (ctr-xxxxxx)")
    profile_id: str = Field(..., description="Assigned Agent Profile ID")
    modified_files: List[str] = Field(default_factory=list, description="List of relative paths of modified files")
    created_files: List[str] = Field(default_factory=list, description="List of relative paths of created files")
    artifacts: List[str] = Field(default_factory=list, description="List of generated implementation artifact paths")
    execution_time_ms: float = Field(..., description="Execution duration in milliseconds")
    provider: str = Field(default="oniroute-local-engine", description="AI/LLM provider used for generation")
    model: str = Field(default="gemini-2.5-pro", description="AI/LLM model used for generation")
    token_usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics (prompt, completion, total)")
    cost_usd: float = Field(default=0.0, description="Estimated execution cost in USD")
    trace_references: List[str] = Field(default_factory=list, description="Trace IDs recorded during execution")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence, performance metrics, and safety checks")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    result_hash: str = Field(..., description="SHA-256 hash of engineering result payload")


class EngineeringCertificationReport(BaseModel):
    """Immutable Engineering Certification Report contract produced by AutonomousEngineeringCertificationEngine."""

    model_config = ConfigDict(frozen=True)

    certification_id: str = Field(..., description="Unique certification identifier (cert-eng-xxxxxx)")
    mission_id: str = Field(..., description="Associated mission identifier")
    pipeline_version: str = Field(default="v1.2", description="Autonomous Engineering Pipeline version")
    contract_versions: Dict[str, str] = Field(default_factory=dict, description="Versions of upstream contract schemas")
    engineering_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of engineering worker execution")
    quality_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of quality gate cross-agent review")
    repair_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of self-healing repair execution")
    verification_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of verification engine checks")
    acceptance_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of acceptance criteria and verdict")
    coverage_summary: Dict[str, Any] = Field(default_factory=dict, description="Code coverage statistics")
    security_summary: Dict[str, Any] = Field(default_factory=dict, description="Security gate audit summary")
    performance_summary: Dict[str, Any] = Field(default_factory=dict, description="End-to-end performance and latency summary")
    production_readiness: bool = Field(..., description="True if complete pipeline is certified production-ready")
    regression_status: str = Field(default="PASSED", description="Regression test suite status")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Audit evidence log and verification hashes")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    certification_hash: str = Field(..., description="SHA-256 hash of certification report payload")
