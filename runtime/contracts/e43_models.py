"""E4.3 Review Release Readiness Integration Models.

Phase E4.3 — Review Release Readiness Integration.

Provides models for determining whether a generated project is ready
for release/progression based on E4.1 review and E4.2 quality gate results.

Architecture:
    ReviewReport (E4.1)
        ↓
    QualityGateResult (E4.2)
        ↓
    ReleaseReadinessEngine (E4.3)
        ↓
    ReleaseReadinessResult
        ↓
    Future remediation phase (E5)

Does NOT:
- Regenerate source code
- Modify generated files
- Perform self-healing
- Call LLM for readiness decision
- Modify frozen E1 contracts

Self-contained: depends only on Python stdlib + pydantic + E4.1/E4.2 models.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from runtime.contracts.e42_models import (
    QualityGateDecision,
    QualityGateResult,
)
from runtime.contracts.e4_models import (
    ReviewFinding,
    ReviewReport,
    ReviewSeverity,
    ReviewVerdict,
)


# ---------------------------------------------------------------------------
# E4.3.1 - Progression Status
# ---------------------------------------------------------------------------

class ProgressionStatus(str, Enum):
    """Status of project for progression/release.

    Deterministically derived from QualityGateResult.

    READY: Project can proceed to next phase
    READY_WITH_WARNINGS: Project can proceed with warnings acknowledged
    NOT_READY: Project cannot proceed, remediation required
    BLOCKED: Project blocked due to critical issues
    SKIPPED: Release readiness check was not executed
    """

    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"

    @classmethod
    def from_quality_gate_decision(
        cls, decision: QualityGateDecision, can_proceed: bool
    ) -> ProgressionStatus:
        """Convert QualityGateDecision to ProgressionStatus.

        Args:
            decision: QualityGateDecision from E4.2
            can_proceed: can_proceed flag from E4.2

        Returns:
            Corresponding ProgressionStatus
        """
        if not can_proceed:
            if decision == QualityGateDecision.BLOCKED:
                return cls.BLOCKED
            return cls.NOT_READY

        if decision == QualityGateDecision.PASS:
            return cls.READY
        elif decision == QualityGateDecision.PASS_WITH_WARNINGS:
            return cls.READY_WITH_WARNINGS

        return cls.NOT_READY


# ---------------------------------------------------------------------------
# E4.3.2 - Release Readiness Level
# ---------------------------------------------------------------------------

class ReleaseReadinessLevel(str, Enum):
    """Level of release readiness assessment.

    PRODUCTION: Ready for production deployment
    STAGING: Ready for staging/pre-production testing
    DEVELOPMENT: Ready for development/testing only
    UNRELEASABLE: Cannot be released
    """

    PRODUCTION = "PRODUCTION"
    STAGING = "STAGING"
    DEVELOPMENT = "DEVELOPMENT"
    UNRELEASABLE = "UNRELEASABLE"


# ---------------------------------------------------------------------------
# E4.3.3 - Artifact Readiness
# ---------------------------------------------------------------------------

class ArtifactReadiness(BaseModel):
    """Readiness status for a single artifact.

    Provides per-artifact release readiness based on E4.2 artifact-level decision.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    artifact_id: str = Field(description="Artifact identifier")
    artifact_execution_id: str = Field(
        default="",
        description="Artifact execution unit ID"
    )

    # Status
    progression_status: ProgressionStatus = Field(
        description="Progression status for this artifact"
    )

    # Readiness level
    readiness_level: ReleaseReadinessLevel = Field(
        description="Release readiness level"
    )

    # Details
    total_findings: int = Field(
        default=0,
        description="Total findings for this artifact"
    )
    blocking_findings: int = Field(
        default=0,
        description="Blocking findings for this artifact"
    )
    critical_findings: int = Field(
        default=0,
        description="CRITICAL findings for this artifact"
    )
    error_findings: int = Field(
        default=0,
        description="ERROR findings for this artifact"
    )
    warning_findings: int = Field(
        default=0,
        description="WARNING findings for this artifact"
    )

    # Files
    affected_files: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Files with findings"
    )

    # Evidence
    top_severity: str = Field(
        default="",
        description="Highest severity finding"
    )


# ---------------------------------------------------------------------------
# E4.3.4 - Blocker Summary
# ---------------------------------------------------------------------------

class BlockerSummary(BaseModel):
    """Summary of blocking issues preventing release.

    Identifies what is blocking progression and why.
    """

    model_config = ConfigDict(frozen=True)

    # Blocking artifacts
    blocking_artifacts: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact IDs that are blocking"
    )

    # Blocking rules
    blocking_rules: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Rule IDs that are blocking"
    )

    # Blocking categories
    blocking_categories: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Finding categories that are blocking"
    )

    # Summary
    total_blocking_findings: int = Field(
        default=0,
        description="Total blocking findings"
    )
    blocking_severities: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Severities of blocking findings"
    )

    # Recommended action
    recommended_action: str = Field(
        default="",
        description="High-level recommended action"
    )


# ---------------------------------------------------------------------------
# E4.3.5 - Release Readiness Evidence
# ---------------------------------------------------------------------------

class ReadinessEvidenceEntry(BaseModel):
    """Single evidence entry in the readiness decision chain."""

    model_config = ConfigDict(frozen=True)

    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    source: str = Field(description="Evidence source")
    type: str = Field(description="Evidence type")
    content: Dict[str, Any] = Field(
        default_factory=dict,
        description="Evidence content"
    )


class ReleaseReadinessEvidence(BaseModel):
    """Complete evidence chain for release readiness decision.

    Preserves traceability from generation through review and quality gate.
    """

    model_config = ConfigDict(frozen=True)

    # References
    review_id: str = Field(description="Source review ID")
    report_id: str = Field(description="Source report ID")
    gate_id: str = Field(description="Source gate ID")
    readiness_id: str = Field(description="This readiness assessment ID")

    # Context
    mission_id: str = Field(description="Mission ID")
    workspace_id: str = Field(description="Workspace ID")
    plan_id: str = Field(description="Plan ID")

    # Evidence chain (from E4.1 → E4.2 → E4.3)
    evidence_chain: Tuple[ReadinessEvidenceEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered evidence entries"
    )

    # Determinism
    deterministic_hash: str = Field(
        default="",
        description="SHA-256 hash for determinism verification"
    )


# ---------------------------------------------------------------------------
# E4.3.6 - Release Readiness Result
# ---------------------------------------------------------------------------

class ReleaseReadinessResult(BaseModel):
    """Complete result of release readiness assessment.

    This is the primary output of E4.3, providing:
    - Deterministic progression status
    - Release readiness level
    - Artifact-level readiness
    - Blocker summary
    - Complete evidence chain
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    readiness_id: str = Field(
        description="Unique release readiness assessment ID"
    )
    review_id: str = Field(
        description="Source review ID (E4.1)"
    )
    report_id: str = Field(
        description="Source report ID (E4.1)"
    )
    gate_id: str = Field(
        description="Source gate ID (E4.2)"
    )
    mission_id: str = Field(
        description="Mission ID"
    )
    workspace_id: str = Field(
        description="Workspace ID"
    )
    plan_id: str = Field(
        description="Plan ID"
    )

    # Primary decision
    progression_status: ProgressionStatus = Field(
        description="Project progression status"
    )
    readiness_level: ReleaseReadinessLevel = Field(
        description="Release readiness level"
    )
    can_release: bool = Field(
        description="Whether project can be released"
    )

    # Summary
    total_artifacts: int = Field(
        default=0,
        description="Total artifacts assessed"
    )
    artifacts_ready: int = Field(
        default=0,
        description="Artifacts that are READY"
    )
    artifacts_ready_with_warnings: int = Field(
        default=0,
        description="Artifacts ready with warnings"
    )
    artifacts_not_ready: int = Field(
        default=0,
        description="Artifacts not ready"
    )
    artifacts_blocked: int = Field(
        default=0,
        description="Artifacts blocked"
    )

    # Findings summary
    total_findings: int = Field(
        default=0,
        description="Total findings across all artifacts"
    )
    critical_findings: int = Field(
        default=0,
        description="CRITICAL findings"
    )
    error_findings: int = Field(
        default=0,
        description="ERROR findings"
    )
    warning_findings: int = Field(
        default=0,
        description="WARNING findings"
    )
    info_findings: int = Field(
        default=0,
        description="INFO findings"
    )

    # Artifact readiness
    artifact_readiness: Tuple[ArtifactReadiness, ...] = Field(
        default_factory=tuple,
        description="Per-artifact readiness status"
    )

    # Blocker summary
    blockers: BlockerSummary = Field(
        description="Summary of blocking issues"
    )

    # Evidence
    evidence: ReleaseReadinessEvidence = Field(
        description="Decision evidence chain"
    )

    # Recommendations
    recommendations: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Recommendations for progression"
    )

    # Timestamps
    assessment_started: str = Field(
        default="",
        description="ISO-8601 UTC when assessment started"
    )
    assessment_completed: str = Field(
        default="",
        description="ISO-8601 UTC when assessment completed"
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="True if assessment is deterministic"
    )
    deterministic_hash: str = Field(
        default="",
        description="SHA-256 hash of complete result"
    )


# ---------------------------------------------------------------------------
# E4.3.7 - Exception Classes
# ---------------------------------------------------------------------------

class ReleaseReadinessError(Exception):
    """Base exception for release readiness failures."""
    pass


class InvalidGateResultError(ReleaseReadinessError):
    """Raised when QualityGateResult is invalid."""
    pass


class EvidenceChainBrokenError(ReleaseReadinessError):
    """Raised when evidence chain is incomplete."""
    pass


# ---------------------------------------------------------------------------
# E4.3.8 - Deterministic Hash Computation
# ---------------------------------------------------------------------------

def compute_readiness_hash(result: ReleaseReadinessResult) -> str:
    """Compute deterministic SHA-256 hash for release readiness result.

    Args:
        result: ReleaseReadinessResult to hash

    Returns:
        SHA-256 hash string
    """
    hash_payload = {
        "readiness_id": result.readiness_id,
        "review_id": result.review_id,
        "gate_id": result.gate_id,
        "progression_status": result.progression_status.value,
        "readiness_level": result.readiness_level.value,
        "can_release": result.can_release,
        "total_artifacts": result.total_artifacts,
        "total_findings": result.total_findings,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# E4.3.9 - Readiness Level Determination
# ---------------------------------------------------------------------------

def determine_readiness_level(
    progression_status: ProgressionStatus,
    critical_count: int,
    error_count: int,
    warning_count: int,
) -> ReleaseReadinessLevel:
    """Determine release readiness level.

    Args:
        progression_status: Project progression status
        critical_count: Number of CRITICAL findings
        error_count: Number of ERROR findings
        warning_count: Number of WARNING findings

    Returns:
        ReleaseReadinessLevel
    """
    if progression_status == ProgressionStatus.BLOCKED:
        return ReleaseReadinessLevel.UNRELEASABLE

    if progression_status == ProgressionStatus.NOT_READY:
        if critical_count > 0:
            return ReleaseReadinessLevel.UNRELEASABLE
        if error_count > 0:
            return ReleaseReadinessLevel.DEVELOPMENT
        return ReleaseReadinessLevel.STAGING

    if progression_status == ProgressionStatus.READY_WITH_WARNINGS:
        if warning_count > 10:
            return ReleaseReadinessLevel.STAGING
        return ReleaseReadinessLevel.PRODUCTION

    if progression_status == ProgressionStatus.READY:
        return ReleaseReadinessLevel.PRODUCTION

    return ReleaseReadinessLevel.UNRELEASABLE


# ---------------------------------------------------------------------------
# E4.3.10 - Blocker Determination
# ---------------------------------------------------------------------------

def determine_blockers(
    quality_gate_result: QualityGateResult,
) -> Tuple[BlockerSummary, List[str]]:
    """Determine blockers from quality gate result.

    Args:
        quality_gate_result: QualityGateResult from E4.2

    Returns:
        Tuple of (BlockerSummary, recommendations)
    """
    project_decision = quality_gate_result.project_decision
    aggregation = project_decision.aggregation

    # Collect blockers
    blocking_artifacts = list(project_decision.blocking_artifact_ids)
    blocking_rules = list(project_decision.blocking_rule_ids)

    # Collect blocking categories
    blocking_categories_set = set()
    for group in project_decision.by_category:
        if group.category.value in ("SECURITY", "FILESYSTEM"):
            blocking_categories_set.add(group.category.value)
        # Add categories with CRITICAL findings
        if group.severity_counts.critical > 0:
            blocking_categories_set.add(group.category.value)

    # Determine blocking severities
    blocking_severities = []
    if aggregation.severity_counts.critical > 0:
        blocking_severities.append("CRITICAL")
    if aggregation.severity_counts.error > 0:
        blocking_severities.append("ERROR")

    # Build recommendations
    recommendations = []

    if blocking_artifacts:
        recommendations.append(
            f"Fix {len(blocking_artifacts)} blocking artifact(s): {', '.join(sorted(blocking_artifacts))}"
        )

    if blocking_categories_set:
        recommendations.append(
            f"Address {len(blocking_categories_set)} critical category issue(s): {', '.join(sorted(blocking_categories_set))}"
        )

    # Determine recommended action
    if "SECURITY" in blocking_categories_set or "FILESYSTEM" in blocking_categories_set:
        recommendations.append("Security review required before release")
        recommended_action = "SECURITY_REVIEW_REQUIRED"
    elif aggregation.severity_counts.critical > 0:
        recommendations.append("Critical issues must be resolved")
        recommended_action = "CRITICAL_ISSUES_MUST_BE_RESOLVED"
    elif aggregation.severity_counts.error > 0:
        recommendations.append("Quality issues should be addressed")
        recommended_action = "QUALITY_ISSUES_SHOULD_BE_ADDRESSED"
    else:
        recommended_action = "NO_BLOCKERS"

    # Build blocker summary with recommended_action
    blockers = BlockerSummary(
        blocking_artifacts=tuple(sorted(blocking_artifacts)),
        blocking_rules=tuple(sorted(blocking_rules)),
        blocking_categories=tuple(sorted(blocking_categories_set)),
        total_blocking_findings=aggregation.blocking_counts.total_blocking,
        blocking_severities=tuple(blocking_severities),
        recommended_action=recommended_action,
    )

    return blockers, recommendations
