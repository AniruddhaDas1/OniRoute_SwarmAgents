"""E4.2 Review Finding Analysis & Quality Gate Decision Engine Models.

Phase E4.2 — Review Finding Analysis & Quality Gate Decision Engine.

Provides immutable models for:
- Quality gate decision types
- Finding classification categories
- Remediation category types
- Finding aggregation structures
- Artifact-level decisions
- Project-level decisions
- Quality gate evidence chain

Architecture:
    ReviewReport (E4.1)
        ↓
    FindingClassificationEngine
        ↓
    FindingAggregator
        ↓
    QualityGateDecisionEngine
        ↓
    QualityGateResult
        ↓
    Future remediation phase (E5)

Does NOT:
- Regenerate source code
- Modify generated files
- Perform self-healing
- Call LLM for gate decision
- Modify frozen E1 contracts

Self-contained: depends only on Python stdlib + pydantic + E4.1 models.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from runtime.contracts.e4_models import (
    ReviewFinding,
    ReviewReport,
    ReviewSeverity,
    ReviewVerdict,
)


# ---------------------------------------------------------------------------
# E4.2.1 - Quality Gate Decision
# ---------------------------------------------------------------------------

class QualityGateDecision(str, Enum):
    """Quality gate decision for project progression.

    Deterministically derived from ReviewReport findings.

    PASS: No findings or only INFO findings - can proceed
    PASS_WITH_WARNINGS: Only WARNING/INFO findings - can proceed with warnings
    FAIL: ERROR findings found - cannot proceed
    BLOCKED: CRITICAL findings found - cannot proceed
    """

    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"

    @classmethod
    def from_review_verdict(cls, verdict: ReviewVerdict) -> QualityGateDecision:
        """Convert E4.1 ReviewVerdict to QualityGateDecision.

        Args:
            verdict: E4.1 ReviewVerdict

        Returns:
            Corresponding QualityGateDecision
        """
        mapping = {
            ReviewVerdict.PASS: cls.PASS,
            ReviewVerdict.PASS_WITH_WARNINGS: cls.PASS_WITH_WARNINGS,
            ReviewVerdict.FAIL: cls.FAIL,
            ReviewVerdict.BLOCKED: cls.BLOCKED,
            ReviewVerdict.SKIPPED: cls.FAIL,  # SKIPPED treated as FAIL for safety
        }
        return mapping.get(verdict, cls.FAIL)


# ---------------------------------------------------------------------------
# E4.2.2 - Finding Classification Categories
# ---------------------------------------------------------------------------

class FindingCategory(str, Enum):
    """Categories for classifying review findings.

    These categories help determine what kind of remediation is needed.
    """

    SECURITY = "SECURITY"           # Security vulnerabilities
    SYNTAX = "SYNTAX"               # Syntax errors
    STRUCTURE = "STRUCTURE"         # Structural issues (empty files, missing dirs)
    CONTENT = "CONTENT"             # Content quality issues
    PLACEHOLDER = "PLACEHOLDER"     # Placeholder/todo content
    DEPENDENCY = "DEPENDENCY"       # Dependency issues
    FILESYSTEM = "FILESYSTEM"       # Filesystem boundary violations
    CONTRACT = "CONTRACT"           # Contract compliance issues
    QUALITY = "QUALITY"             # Code quality issues
    CONFIGURATION = "CONFIGURATION" # Configuration issues
    OTHER = "OTHER"                 # Uncategorized


# ---------------------------------------------------------------------------
# E4.2.3 - Remediation Category
# ---------------------------------------------------------------------------

class RemediationCategory(str, Enum):
    """Categories for required remediation actions.

    E4.2 determines WHAT remediation category is needed,
    but does NOT perform the remediation itself.
    """

    NO_ACTION = "NO_ACTION"                    # No remediation needed
    MANUAL_REVIEW = "MANUAL_REVIEW"            # Human review required
    REGENERATE_ARTIFACT = "REGENERATE_ARTIFACT"  # Full regeneration needed
    FIX_GENERATED_CODE = "FIX_GENERATED_CODE"  # Fix existing code
    FIX_CONFIGURATION = "FIX_CONFIGURATION"    # Fix configuration
    FIX_DEPENDENCY = "FIX_DEPENDENCY"          # Fix dependencies
    FIX_STRUCTURE = "FIX_STRUCTURE"            # Fix project structure
    SECURITY_REVIEW = "SECURITY_REVIEW"       # Security specialist needed
    BLOCK_RELEASE = "BLOCK_RELEASE"            # Block release entirely


# ---------------------------------------------------------------------------
# E4.2.4 - Finding Classification
# ---------------------------------------------------------------------------

class FindingClassification(BaseModel):
    """Classification of a single review finding.

    Extends ReviewFinding with classification metadata.
    """

    model_config = ConfigDict(frozen=True)

    # Original finding reference
    finding_id: str = Field(description="Original finding ID")
    severity: ReviewSeverity = Field(description="Finding severity")
    message: str = Field(description="Finding message")
    file_path: str = Field(description="Affected file path")
    artifact_id: str = Field(description="Affected artifact ID")
    rule_id: str = Field(description="Rule that was violated")
    is_blocking: bool = Field(description="Whether finding blocks progression")

    # Classification
    category: FindingCategory = Field(description="Finding category")
    remediation: RemediationCategory = Field(description="Required remediation")

    # Evidence
    evidence: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Evidence lines"
    )


# ---------------------------------------------------------------------------
# E4.2.5 - Finding Aggregation
# ---------------------------------------------------------------------------

class SeverityCounts(BaseModel):
    """Counts of findings by severity."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(default=0, description="Total findings")
    critical: int = Field(default=0, description="CRITICAL findings")
    error: int = Field(default=0, description="ERROR findings")
    warning: int = Field(default=0, description="WARNING findings")
    info: int = Field(default=0, description="INFO findings")


class BlockingCounts(BaseModel):
    """Counts of findings by blocking status."""

    model_config = ConfigDict(frozen=True)

    total_blocking: int = Field(default=0, description="Total blocking findings")
    non_blocking: int = Field(default=0, description="Non-blocking findings")


class CategoryCounts(BaseModel):
    """Counts of findings by category."""

    model_config = ConfigDict(frozen=True)

    by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of findings per category"
    )


class FindingAggregation(BaseModel):
    """Aggregated statistics about findings.

    Provides deterministic aggregation of all findings in a ReviewReport.
    """

    model_config = ConfigDict(frozen=True)

    # Severity counts
    severity_counts: SeverityCounts = Field(
        default_factory=SeverityCounts,
        description="Counts by severity"
    )

    # Blocking counts
    blocking_counts: BlockingCounts = Field(
        default_factory=BlockingCounts,
        description="Counts by blocking status"
    )

    # Category counts
    category_counts: CategoryCounts = Field(
        default_factory=CategoryCounts,
        description="Counts by category"
    )

    # Unique counts
    unique_artifact_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Unique artifact IDs with findings"
    )
    unique_file_paths: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Unique file paths with findings"
    )
    unique_rule_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Unique rule IDs violated"
    )
    unique_check_types: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Unique check types that produced findings"
    )

    # Affected counts
    affected_artifact_count: int = Field(
        default=0,
        description="Number of artifacts with findings"
    )
    affected_file_count: int = Field(
        default=0,
        description="Number of files with findings"
    )


# ---------------------------------------------------------------------------
# E4.2.6 - Grouped Findings
# ---------------------------------------------------------------------------

class GroupedByArtifact(BaseModel):
    """Findings grouped by artifact ID."""

    model_config = ConfigDict(frozen=True)

    artifact_id: str = Field(description="Artifact identifier")
    findings: Tuple[FindingClassification, ...] = Field(
        default_factory=tuple,
        description="Findings for this artifact"
    )
    severity_counts: SeverityCounts = Field(
        default_factory=SeverityCounts,
        description="Severity counts for this artifact"
    )
    blocking_count: int = Field(default=0, description="Blocking findings count")


class GroupedByFile(BaseModel):
    """Findings grouped by file path."""

    model_config = ConfigDict(frozen=True)

    file_path: str = Field(description="File path")
    artifact_id: str = Field(default="", description="Associated artifact ID")
    findings: Tuple[FindingClassification, ...] = Field(
        default_factory=tuple,
        description="Findings for this file"
    )
    severity_counts: SeverityCounts = Field(
        default_factory=SeverityCounts,
        description="Severity counts for this file"
    )


class GroupedByRule(BaseModel):
    """Findings grouped by rule ID."""

    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(description="Rule identifier")
    findings: Tuple[FindingClassification, ...] = Field(
        default_factory=tuple,
        description="Findings for this rule"
    )
    affected_artifacts: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact IDs affected by this rule"
    )
    affected_files: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="File paths affected by this rule"
    )


class GroupedByCategory(BaseModel):
    """Findings grouped by finding category."""

    model_config = ConfigDict(frozen=True)

    category: FindingCategory = Field(description="Finding category")
    findings: Tuple[FindingClassification, ...] = Field(
        default_factory=tuple,
        description="Findings in this category"
    )
    severity_counts: SeverityCounts = Field(
        default_factory=SeverityCounts,
        description="Severity counts for this category"
    )
    remediation: RemediationCategory = Field(
        description="Required remediation for this category"
    )


# ---------------------------------------------------------------------------
# E4.2.7 - Multi-Level Decisions
# ---------------------------------------------------------------------------

class ArtifactLevelDecision(BaseModel):
    """Decision for a single artifact.

    Provides per-artifact quality gate decision.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    artifact_id: str = Field(description="Artifact identifier")
    artifact_execution_id: str = Field(
        default="",
        description="Artifact execution unit ID"
    )

    # Decision
    decision: QualityGateDecision = Field(
        description="Quality gate decision for this artifact"
    )
    can_proceed: bool = Field(
        description="Whether artifact can proceed"
    )

    # Counts
    total_findings: int = Field(default=0, description="Total findings")
    blocking_findings: int = Field(default=0, description="Blocking findings")

    # Severity
    has_critical: bool = Field(default=False, description="Has CRITICAL findings")
    has_error: bool = Field(default=False, description="Has ERROR findings")
    has_warning: bool = Field(default=False, description="Has WARNING findings")
    has_info: bool = Field(default=False, description="Has INFO findings")

    # Affected files
    affected_files: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Files with findings for this artifact"
    )

    # Evidence
    top_severity: ReviewSeverity = Field(
        description="Highest severity finding"
    )


class ProjectLevelDecision(BaseModel):
    """Project-level quality gate decision.

    Aggregates all artifact decisions into an overall project decision.
    """

    model_config = ConfigDict(frozen=True)

    # Overall decision
    decision: QualityGateDecision = Field(
        description="Overall project quality gate decision"
    )
    can_proceed: bool = Field(
        description="Whether project can proceed to next phase"
    )

    # Summary counts
    total_artifacts: int = Field(default=0, description="Total artifacts reviewed")
    artifacts_passing: int = Field(default=0, description="Artifacts with PASS")
    artifacts_with_warnings: int = Field(default=0, description="Artifacts with PASS_WITH_WARNINGS")
    artifacts_failing: int = Field(default=0, description="Artifacts with FAIL")
    artifacts_blocked: int = Field(default=0, description="Artifacts with BLOCKED")

    # Findings summary
    aggregation: FindingAggregation = Field(
        description="Aggregated findings"
    )

    # Artifact decisions
    artifact_decisions: Tuple[ArtifactLevelDecision, ...] = Field(
        default_factory=tuple,
        description="Per-artifact decisions"
    )

    # Grouped findings
    by_artifact: Tuple[GroupedByArtifact, ...] = Field(
        default_factory=tuple,
        description="Findings grouped by artifact"
    )
    by_file: Tuple[GroupedByFile, ...] = Field(
        default_factory=tuple,
        description="Findings grouped by file"
    )
    by_rule: Tuple[GroupedByRule, ...] = Field(
        default_factory=tuple,
        description="Findings grouped by rule"
    )
    by_category: Tuple[GroupedByCategory, ...] = Field(
        default_factory=tuple,
        description="Findings grouped by category"
    )

    # Blocking evidence
    blocking_artifact_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifacts causing project failure"
    )
    blocking_rule_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Rules causing project failure"
    )


# ---------------------------------------------------------------------------
# E4.2.8 - Quality Gate Evidence
# ---------------------------------------------------------------------------

class EvidenceEntry(BaseModel):
    """Single evidence entry in the decision evidence chain."""

    model_config = ConfigDict(frozen=True)

    timestamp: str = Field(description="ISO-8601 UTC timestamp")
    source: str = Field(description="Evidence source (e.g., 'ReviewReport', 'FindingAnalysis')")
    type: str = Field(description="Evidence type")
    content: Dict[str, Any] = Field(
        default_factory=dict,
        description="Evidence content"
    )


class QualityGateEvidence(BaseModel):
    """Evidence chain for quality gate decision.

    Preserves full traceability from ReviewReport to decision.
    """

    model_config = ConfigDict(frozen=True)

    # Review reference
    review_id: str = Field(description="Source review ID")
    report_id: str = Field(description="Source report ID")
    mission_id: str = Field(description="Mission ID")
    workspace_id: str = Field(description="Workspace ID")
    plan_id: str = Field(description="Plan ID")

    # Evidence chain
    evidence_chain: Tuple[EvidenceEntry, ...] = Field(
        default_factory=tuple,
        description="Ordered evidence entries"
    )

    # Determinism
    deterministic_hash: str = Field(
        default="",
        description="SHA-256 hash of decision inputs"
    )
    decision_hash: str = Field(
        default="",
        description="SHA-256 hash of decision output"
    )

    # Timestamps
    analysis_started: str = Field(
        default="",
        description="ISO-8601 UTC when analysis started"
    )
    analysis_completed: str = Field(
        default="",
        description="ISO-8601 UTC when analysis completed"
    )


# ---------------------------------------------------------------------------
# E4.2.9 - Quality Gate Result
# ---------------------------------------------------------------------------

class QualityGateResult(BaseModel):
    """Complete result of quality gate analysis.

    This is the primary output of E4.2, providing:
    - Deterministic gate decision
    - Multi-level decisions (artifact and project)
    - Finding classification and aggregation
    - Evidence preservation
    - Remediation classification
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    gate_id: str = Field(description="Unique gate analysis ID")
    review_id: str = Field(description="Source review ID")
    report_id: str = Field(description="Source report ID")
    mission_id: str = Field(description="Mission ID")
    workspace_id: str = Field(description="Workspace ID")
    plan_id: str = Field(description="Plan ID")

    # Primary decision
    decision: QualityGateDecision = Field(
        description="Overall quality gate decision"
    )
    can_proceed: bool = Field(
        description="Whether project can proceed to next phase"
    )

    # Reasons
    decision_reasons: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Human-readable reasons for decision"
    )

    # Remediation
    required_remediation: RemediationCategory = Field(
        description="Required remediation category"
    )
    remediation_summary: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Summary of required remediation"
    )

    # Multi-level decisions
    project_decision: ProjectLevelDecision = Field(
        description="Project-level decision"
    )

    # Evidence
    evidence: QualityGateEvidence = Field(
        description="Decision evidence chain"
    )

    # Timestamps
    analysis_started: str = Field(
        default="",
        description="ISO-8601 UTC when analysis started"
    )
    analysis_completed: str = Field(
        default="",
        description="ISO-8601 UTC when analysis completed"
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="True if analysis is deterministic"
    )
    deterministic_hash: str = Field(
        default="",
        description="SHA-256 hash of complete result"
    )


# ---------------------------------------------------------------------------
# E4.2.10 - Exception Classes
# ---------------------------------------------------------------------------

class QualityGateError(Exception):
    """Base exception for quality gate failures."""
    pass


class AnalysisError(QualityGateError):
    """Raised when analysis fails."""
    pass


class InvalidReportError(QualityGateError):
    """Raised when ReviewReport is invalid for analysis."""
    pass


# ---------------------------------------------------------------------------
# E4.2.11 - Deterministic Hash Computation
# ---------------------------------------------------------------------------

def compute_quality_gate_hash(result: QualityGateResult) -> str:
    """Compute deterministic SHA-256 hash for quality gate result.

    Args:
        result: QualityGateResult to hash

    Returns:
        SHA-256 hash string
    """
    hash_payload = {
        "gate_id": result.gate_id,
        "review_id": result.review_id,
        "decision": result.decision.value,
        "can_proceed": result.can_proceed,
        "required_remediation": result.required_remediation.value,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_evidence_hash(
    review_id: str,
    report_id: str,
    findings: Tuple[ReviewFinding, ...],
) -> str:
    """Compute deterministic hash for evidence chain.

    Args:
        review_id: Review identifier
        report_id: Report identifier
        findings: Findings tuple

    Returns:
        SHA-256 hash string
    """
    finding_hashes = []
    for f in sorted(findings, key=lambda x: x.finding_id):
        finding_hashes.append(f.finding_id)

    hash_payload = {
        "review_id": review_id,
        "report_id": report_id,
        "finding_count": len(findings),
        "finding_ids": finding_hashes,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# E4.2.12 - Remediation Determination
# ---------------------------------------------------------------------------

def determine_remediation_category(
    decision: QualityGateDecision,
    aggregation: FindingAggregation,
) -> Tuple[RemediationCategory, List[str]]:
    """Determine remediation category from decision and aggregation.

    Args:
        decision: Quality gate decision
        aggregation: Finding aggregation

    Returns:
        Tuple of (remediation category, summary reasons)
    """
    if decision == QualityGateDecision.PASS:
        return RemediationCategory.NO_ACTION, ["No remediation needed"]

    if decision == QualityGateDecision.PASS_WITH_WARNINGS:
        return RemediationCategory.MANUAL_REVIEW, [
            "Manual review recommended for warnings",
            f"{aggregation.severity_counts.warning} warning(s)",
        ]

    if decision == QualityGateDecision.BLOCKED:
        reasons = ["CRITICAL findings require immediate attention"]

        if "FILESYSTEM" in aggregation.category_counts.by_category:
            reasons.append("Security boundary violation detected")

        if "SYNTAX" in aggregation.category_counts.by_category:
            reasons.append("Syntax errors must be fixed")

        if aggregation.severity_counts.critical > 0:
            reasons.append(f"{aggregation.severity_counts.critical} CRITICAL issue(s)")

        return RemediationCategory.BLOCK_RELEASE, reasons

    # FAIL case
    reasons = [f"{aggregation.severity_counts.error} error(s) require fixing"]

    if "DEPENDENCY" in aggregation.category_counts.by_category:
        return RemediationCategory.FIX_DEPENDENCY, [
            "Dependency issues detected",
            "Package configuration needs review",
        ]

    if "CONFIGURATION" in aggregation.category_counts.by_category:
        return RemediationCategory.FIX_CONFIGURATION, [
            "Configuration issues detected",
            "Settings need correction",
        ]

    if "STRUCTURE" in aggregation.category_counts.by_category:
        return RemediationCategory.FIX_STRUCTURE, [
            "Project structure issues detected",
            "File organization needs review",
        ]

    if "PLACEHOLDER" in aggregation.category_counts.by_category:
        return RemediationCategory.REGENERATE_ARTIFACT, [
            "Placeholder content detected",
            "Artifacts need regeneration",
        ]

    return RemediationCategory.FIX_GENERATED_CODE, reasons


# ---------------------------------------------------------------------------
# E4.2.13 - Finding Classification Rules
# ---------------------------------------------------------------------------

# Map check_type to FindingCategory
CHECK_TYPE_TO_CATEGORY: Dict[str, FindingCategory] = {
    "file_exists": FindingCategory.FILESYSTEM,
    "file_not_empty": FindingCategory.STRUCTURE,
    "path_boundary": FindingCategory.SECURITY,
    "no_placeholders": FindingCategory.PLACEHOLDER,
    "syntax_python": FindingCategory.SYNTAX,
    "syntax_json": FindingCategory.SYNTAX,
    "syntax_yaml": FindingCategory.SYNTAX,
    "syntax_typescript": FindingCategory.SYNTAX,
    "syntax_javascript": FindingCategory.SYNTAX,
    "syntax_html": FindingCategory.SYNTAX,
    "syntax_css": FindingCategory.SYNTAX,
    "cross_references": FindingCategory.DEPENDENCY,
    "project_structure": FindingCategory.QUALITY,
    "required_artifacts": FindingCategory.CONTRACT,
}

# Map FindingCategory to default RemediationCategory
CATEGORY_TO_REMEDIATION: Dict[FindingCategory, RemediationCategory] = {
    FindingCategory.SECURITY: RemediationCategory.SECURITY_REVIEW,
    FindingCategory.SYNTAX: RemediationCategory.FIX_GENERATED_CODE,
    FindingCategory.STRUCTURE: RemediationCategory.FIX_STRUCTURE,
    FindingCategory.CONTENT: RemediationCategory.FIX_GENERATED_CODE,
    FindingCategory.PLACEHOLDER: RemediationCategory.REGENERATE_ARTIFACT,
    FindingCategory.DEPENDENCY: RemediationCategory.FIX_DEPENDENCY,
    FindingCategory.FILESYSTEM: RemediationCategory.BLOCK_RELEASE,
    FindingCategory.CONTRACT: RemediationCategory.MANUAL_REVIEW,
    FindingCategory.QUALITY: RemediationCategory.MANUAL_REVIEW,
    FindingCategory.CONFIGURATION: RemediationCategory.FIX_CONFIGURATION,
    FindingCategory.OTHER: RemediationCategory.MANUAL_REVIEW,
}

# Map severity to remediation override (higher severity overrides category)
SEVERITY_TO_REMEDIATION: Dict[ReviewSeverity, RemediationCategory] = {
    ReviewSeverity.CRITICAL: RemediationCategory.BLOCK_RELEASE,
    ReviewSeverity.ERROR: RemediationCategory.FIX_GENERATED_CODE,
    ReviewSeverity.WARNING: RemediationCategory.MANUAL_REVIEW,
    ReviewSeverity.INFO: RemediationCategory.NO_ACTION,
}


def classify_finding(finding: ReviewFinding) -> FindingClassification:
    """Classify a single review finding.

    Args:
        finding: ReviewFinding to classify

    Returns:
        FindingClassification with category and remediation
    """
    # Determine category from check_type
    category = CHECK_TYPE_TO_CATEGORY.get(
        finding.check_type, FindingCategory.OTHER
    )

    # Determine remediation from severity (overrides category)
    remediation = SEVERITY_TO_REMEDIATION.get(
        finding.severity, RemediationCategory.MANUAL_REVIEW
    )

    # Severity overrides category remediation for CRITICAL
    if finding.severity == ReviewSeverity.CRITICAL:
        remediation = RemediationCategory.BLOCK_RELEASE
    elif finding.severity == ReviewSeverity.ERROR:
        if category == FindingCategory.PLACEHOLDER:
            remediation = RemediationCategory.REGENERATE_ARTIFACT
        elif category == FindingCategory.SYNTAX:
            remediation = RemediationCategory.FIX_GENERATED_CODE
        elif category == FindingCategory.DEPENDENCY:
            remediation = RemediationCategory.FIX_DEPENDENCY
        elif category == FindingCategory.CONFIGURATION:
            remediation = RemediationCategory.FIX_CONFIGURATION
        else:
            remediation = RemediationCategory.FIX_GENERATED_CODE

    return FindingClassification(
        finding_id=finding.finding_id,
        severity=finding.severity,
        message=finding.message,
        file_path=finding.file_path,
        artifact_id=finding.artifact_id,
        rule_id=finding.rule_id,
        is_blocking=finding.is_blocking,
        category=category,
        remediation=remediation,
        evidence=finding.evidence,
    )
