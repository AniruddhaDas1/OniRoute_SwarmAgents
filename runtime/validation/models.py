"""Validation & Acceptance Data Contracts (Phase P5.E4)."""

from __future__ import annotations

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class VerificationResult(BaseModel):
    """Immutable Verification Result contract produced by VerificationEngine."""

    model_config = ConfigDict(frozen=True)

    verification_id: str = Field(..., description="Unique verification identifier (vrf-xxxxxx)")
    engineering_result_id: str = Field(..., description="Associated UpdatedEngineeringResult or EngineeringResult identifier")
    executed_checks: List[str] = Field(default_factory=list, description="List of executed verification checks")
    build_status: str = Field(..., description="Build status (PASSED, FAILED, SKIPPED)")
    test_status: str = Field(..., description="Test status (PASSED, FAILED, SKIPPED)")
    coverage_percentage: float = Field(..., ge=0.0, le=100.0, description="Test code coverage percentage")
    lint_status: str = Field(..., description="Lint status (PASSED, FAILED, SKIPPED)")
    security_status: str = Field(..., description="Security gates status (PASSED, FAILED, SKIPPED)")
    performance_status: str = Field(..., description="Performance gates status (PASSED, FAILED, SKIPPED)")
    artifact_status: str = Field(..., description="Artifact validity status (PASSED, FAILED, SKIPPED)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Verification evidence and detailed audit log")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    verification_hash: str = Field(..., description="SHA-256 hash of verification result payload")


class AcceptanceReport(BaseModel):
    """Immutable Acceptance Report contract produced by AcceptanceEngine."""

    model_config = ConfigDict(frozen=True)

    acceptance_id: str = Field(..., description="Unique acceptance report identifier (acpt-xxxxxx)")
    verification_id: str = Field(..., description="Associated VerificationResult identifier")
    mission_status: str = Field(..., description="Overall mission execution status (SUCCESS, PARTIAL, FAILED)")
    production_ready: bool = Field(..., description="True if implementation satisfies all production readiness gates")
    acceptance_verdict: str = Field(..., description="Final acceptance verdict (ACCEPTED, REJECTED, PROVISIONAL)")
    rejected_criteria: List[str] = Field(default_factory=list, description="List of failed acceptance criteria")
    accepted_criteria: List[str] = Field(default_factory=list, description="List of satisfied acceptance criteria")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Acceptance evidence and audit log")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    acceptance_hash: str = Field(..., description="SHA-256 hash of acceptance report payload")
