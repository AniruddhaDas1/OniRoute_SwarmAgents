"""Quality Gate (Cross-Agent Review) Data Contracts (Phase P5.E2)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class ReviewSeverity(str, Enum):
    """Severity levels for quality gate findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class QualityFinding(BaseModel):
    """Immutable record defining an independent reviewer finding."""

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(..., description="Unique finding identifier (fnd-xxxxxx)")
    category: str = Field(..., description="Review category (Architecture, Security, Contract Compliance, Coding Standards, Performance, Documentation, Testing, Interface, Dependency, Artifact)")
    severity: str = Field(..., description="Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)")
    reviewer_profile_id: str = Field(..., description="Reviewer agent profile ID (e.g. prf-sec-auditor)")
    reviewer_role: str = Field(..., description="Reviewer role title (e.g. Security Auditor)")
    description: str = Field(..., description="Detailed description of the review finding")
    target_path: str = Field(..., description="Target file or directory relative path")
    recommended_fix: str = Field(..., description="Recommended fix or remediation strategy for Self-Healing (P5.E3)")


class QualityReport(BaseModel):
    """Immutable Quality Report contract produced by QualityGateEngine."""

    model_config = ConfigDict(frozen=True)

    report_id: str = Field(..., description="Unique quality report identifier (qltr-xxxxxx)")
    engineering_result_id: str = Field(..., description="Associated EngineeringResult identifier")
    contract_id: str = Field(..., description="Associated EngineeringContract identifier")
    reviewer_profiles: List[str] = Field(default_factory=list, description="List of assigned reviewer profile IDs")
    findings: List[QualityFinding] = Field(default_factory=list, description="List of all quality findings")
    architecture_score: float = Field(..., ge=0.0, le=1.0, description="Architecture score (0.0 to 1.0)")
    security_score: float = Field(..., ge=0.0, le=1.0, description="Security score (0.0 to 1.0)")
    performance_score: float = Field(..., ge=0.0, le=1.0, description="Performance score (0.0 to 1.0)")
    testing_score: float = Field(..., ge=0.0, le=1.0, description="Testing score (0.0 to 1.0)")
    documentation_score: float = Field(..., ge=0.0, le=1.0, description="Documentation score (0.0 to 1.0)")
    contract_compliance: bool = Field(..., description="True if contract compliance checks pass 100%")
    approval_status: str = Field(..., description="Overall approval status (APPROVED, CONDITIONALLY_APPROVED, REJECTED)")
    required_fixes: List[str] = Field(default_factory=list, description="List of mandatory required fixes for Self-Healing (P5.E3)")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Validation evidence, performance metrics, and audit log")
    timestamp: str = Field(..., description="ISO-8601 UTC completion timestamp")
    report_hash: str = Field(..., description="SHA-256 hash of quality report payload")
