"""E4.1 Review Pipeline Models.

Phase E4.1 — Real Artifact Review & Quality Gates.

Provides immutable models for:
- Review requests and findings
- Quality gates and checks
- Review verdicts
- Review reports

Architecture:
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionOrchestrator
        ↓
    RealCodeGenerationEngine
        ↓
    RepositoryWriter
        ↓
    REAL FILES
        ↓
    ReviewEngine
        ↓
    ReviewReport
        ↓
    ReviewVerdict
        ↓
    ProjectExecutionResult

Self-contained: depends only on Python stdlib + pydantic + existing E2/E3 models.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# E4.1.1 - Review Severity
# ---------------------------------------------------------------------------

class ReviewSeverity(str, Enum):
    """Severity levels for review findings.

    CRITICAL: Must be fixed before mission can succeed
    ERROR: Should be fixed, but mission can proceed with warning
    WARNING: Advisory, mission can proceed
    INFO: Informational only
    """

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


# ---------------------------------------------------------------------------
# E4.1.2 - Review Verdict
# ---------------------------------------------------------------------------

class ReviewVerdict(str, Enum):
    """Final verdict for a review.

    BLOCKED: CRITICAL finding(s) found - mission cannot proceed
    FAIL: ERROR finding(s) found - mission fails
    PASS_WITH_WARNINGS: Only WARNING/INFO findings - mission succeeds with warnings
    PASS: No findings - mission succeeds
    SKIPPED: Review was not executed
    """

    BLOCKED = "BLOCKED"
    FAIL = "FAIL"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    PASS = "PASS"
    SKIPPED = "SKIPPED"


# ---------------------------------------------------------------------------
# E4.1.3 - Review Finding
# ---------------------------------------------------------------------------

class ReviewFinding(BaseModel):
    """Immutable finding from a review check.

    Contains enough information to identify:
    - mission
    - workspace
    - artifact
    - file path
    - rule/check
    - severity
    - message
    - evidence
    - blocking/non-blocking status
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    finding_id: str = Field(
        description="Unique finding identifier"
    )
    check_id: str = Field(
        description="ID of the check that produced this finding"
    )
    check_type: str = Field(
        description="Type of check (e.g., 'file_exists', 'syntax_check')"
    )

    # Context
    mission_id: str = Field(
        description="Mission identifier"
    )
    workspace_id: str = Field(
        description="Workspace identifier"
    )
    plan_id: str = Field(
        description="ArtifactExecutionPlan ID"
    )

    # Artifact context
    artifact_execution_id: str = Field(
        description="Artifact execution unit ID"
    )
    artifact_id: str = Field(
        description="Artifact identifier"
    )

    # File context
    file_path: str = Field(
        description="Repository-relative file path"
    )
    absolute_path: str = Field(
        description="Absolute filesystem path"
    )

    # Finding details
    severity: ReviewSeverity = Field(
        description="Severity level"
    )
    message: str = Field(
        description="Human-readable finding message"
    )
    evidence: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Evidence lines or snippets"
    )

    # Blocking status
    is_blocking: bool = Field(
        description="True if this finding blocks mission success"
    )

    # Rule reference
    rule_id: str = Field(
        default="",
        description="Rule ID that was violated"
    )
    rule_name: str = Field(
        default="",
        description="Human-readable rule name"
    )

    # Timestamp
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp when finding was recorded"
    )


# ---------------------------------------------------------------------------
# E4.1.4 - Review Check Result
# ---------------------------------------------------------------------------

class ReviewCheckResult(BaseModel):
    """Result of a single review check.

    A check can:
    - PASS: No issues found
    - SKIP: Check could not be executed (tool unavailable, etc.)
    - FAIL: Issues found
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    check_id: str = Field(
        description="Unique check identifier"
    )
    check_type: str = Field(
        description="Type of check (e.g., 'file_exists', 'syntax_python')"
    )

    # Execution
    executed: bool = Field(
        description="True if check was actually executed"
    )
    skipped: bool = Field(
        description="True if check was skipped (not executable)"
    )
    skip_reason: str = Field(
        default="",
        description="Reason why check was skipped"
    )

    # Result
    passed: bool = Field(
        description="True if check passed"
    )

    # Findings from this check
    findings: Tuple[ReviewFinding, ...] = Field(
        default_factory=tuple,
        description="Findings from this check"
    )

    # Timing
    started_at: str = Field(
        default="",
        description="ISO-8601 UTC timestamp when check started"
    )
    completed_at: str = Field(
        default="",
        description="ISO-8601 UTC timestamp when check completed"
    )
    duration_ms: float = Field(
        default=0.0,
        description="Check duration in milliseconds"
    )

    # Evidence
    evidence: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Check execution evidence"
    )


# ---------------------------------------------------------------------------
# E4.1.5 - Review Report
# ---------------------------------------------------------------------------

class ReviewReport(BaseModel):
    """Complete review report for a project execution.

    Contains:
    - Identity information
    - All check results
    - All findings
    - Calculated verdict
    - Timing information
    """

    model_config = ConfigDict(frozen=False)  # Allow hash update after creation

    # Identity
    report_id: str = Field(
        description="Unique report identifier"
    )
    review_id: str = Field(
        description="Review session identifier"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )
    workspace_id: str = Field(
        description="Workspace identifier"
    )
    plan_id: str = Field(
        description="ArtifactExecutionPlan ID"
    )

    # Scope
    workspace_root: str = Field(
        description="Absolute workspace root path"
    )
    repository_scope: str = Field(
        description="Primary repository scope"
    )

    # Check summary
    total_checks: int = Field(
        default=0,
        description="Total checks executed"
    )
    checks_passed: int = Field(
        default=0,
        description="Checks that passed"
    )
    checks_failed: int = Field(
        default=0,
        description="Checks that found issues"
    )
    checks_skipped: int = Field(
        default=0,
        description="Checks that were skipped"
    )

    # Check results
    check_results: Tuple[ReviewCheckResult, ...] = Field(
        default_factory=tuple,
        description="Per-check results"
    )

    # Finding summary
    total_findings: int = Field(
        default=0,
        description="Total findings"
    )
    critical_findings: int = Field(
        default=0,
        description="Critical severity findings"
    )
    error_findings: int = Field(
        default=0,
        description="Error severity findings"
    )
    warning_findings: int = Field(
        default=0,
        description="Warning severity findings"
    )
    info_findings: int = Field(
        default=0,
        description="Info severity findings"
    )

    # All findings
    findings: Tuple[ReviewFinding, ...] = Field(
        default_factory=tuple,
        description="All findings from all checks"
    )

    # Verdict
    verdict: ReviewVerdict = Field(
        default=ReviewVerdict.SKIPPED,
        description="Final review verdict"
    )
    verdict_reasons: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Reasons for the verdict"
    )

    # Timing
    review_started: str = Field(
        default="",
        description="ISO-8601 UTC timestamp when review started"
    )
    review_completed: str = Field(
        default="",
        description="ISO-8601 UTC timestamp when review completed"
    )
    total_duration_ms: float = Field(
        default=0.0,
        description="Total review duration in milliseconds"
    )

    # Files reviewed
    files_reviewed: int = Field(
        default=0,
        description="Number of files reviewed"
    )
    files_with_issues: int = Field(
        default=0,
        description="Number of files with issues"
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="True if review is deterministic"
    )
    deterministic_hash: str = Field(
        default="",
        description="SHA-256 hash for report integrity"
    )


# ---------------------------------------------------------------------------
# E4.1.6 - Review Request
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    """Request for reviewing generated artifacts.

    This is the input to the ReviewEngine.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    review_id: str = Field(
        description="Unique review session identifier"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )
    workspace_id: str = Field(
        description="Workspace identifier"
    )
    plan_id: str = Field(
        description="ArtifactExecutionPlan ID"
    )

    # Workspace info
    workspace_root: str = Field(
        description="Absolute workspace root path"
    )
    repository_scope: str = Field(
        description="Primary repository scope"
    )

    # Files to review
    file_paths: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Repository-relative paths of files to review"
    )

    # Artifact mapping (artifact_id -> file path)
    artifact_files: Tuple[Tuple[str, str], ...] = Field(
        default_factory=tuple,
        description="Pairs of (artifact_id, file_path)"
    )

    # Plan info for dependency checks
    artifact_execution_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact execution IDs to verify"
    )

    # Configuration
    strict_mode: bool = Field(
        default=False,
        description="If True, treat warnings as errors"
    )
    skip_syntax_checks: bool = Field(
        default=False,
        description="If True, skip syntax validation"
    )


# ---------------------------------------------------------------------------
# E4.1.7 - Quality Gate Result
# ---------------------------------------------------------------------------

class QualityGateResult(BaseModel):
    """Result of applying a quality gate.

    A quality gate is a collection of checks that must pass
    for a specific purpose (e.g., 'critical', 'recommended').
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    gate_id: str = Field(
        description="Unique gate identifier"
    )
    gate_name: str = Field(
        description="Human-readable gate name"
    )

    # Result
    passed: bool = Field(
        description="True if gate passed"
    )
    blocking: bool = Field(
        description="True if gate failure blocks mission"
    )

    # Check summary
    total_checks: int = Field(
        default=0,
        description="Total checks in this gate"
    )
    passed_checks: int = Field(
        default=0,
        description="Checks that passed"
    )
    failed_checks: int = Field(
        default=0,
        description="Checks that failed"
    )
    skipped_checks: int = Field(
        default=0,
        description="Checks that were skipped"
    )

    # Findings
    findings: Tuple[ReviewFinding, ...] = Field(
        default_factory=tuple,
        description="Findings from this gate"
    )

    # Message
    message: str = Field(
        default="",
        description="Gate result message"
    )


# ---------------------------------------------------------------------------
# E4.1.8 - Review History Entry
# ---------------------------------------------------------------------------

class ReviewHistoryEntry(BaseModel):
    """Entry in the review history log.

    Integrates with existing runtime history/evidence mechanisms.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    entry_id: str = Field(
        description="Unique entry identifier"
    )
    review_id: str = Field(
        description="Review session ID"
    )

    # Context
    mission_id: str = Field(
        description="Mission identifier"
    )
    workspace_id: str = Field(
        description="Workspace identifier"
    )
    plan_id: str = Field(
        description="ArtifactExecutionPlan ID"
    )

    # Review result
    verdict: ReviewVerdict = Field(
        description="Review verdict"
    )

    # Counts
    total_findings: int = Field(
        default=0,
        description="Total findings"
    )
    critical_count: int = Field(
        default=0,
        description="Critical findings"
    )
    error_count: int = Field(
        default=0,
        description="Error findings"
    )
    warning_count: int = Field(
        default=0,
        description="Warning findings"
    )

    # Timing
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp"
    )
    duration_ms: float = Field(
        default=0.0,
        description="Review duration in milliseconds"
    )

    # Files
    files_reviewed: int = Field(
        default=0,
        description="Files reviewed"
    )
    files_with_issues: int = Field(
        default=0,
        description="Files with issues"
    )

    # Evidence reference
    report_id: str = Field(
        default="",
        description="Associated ReviewReport ID"
    )


# ---------------------------------------------------------------------------
# E4.1.9 - Exception Classes
# ---------------------------------------------------------------------------

class ReviewError(Exception):
    """Base exception for review failures."""
    pass


class ReviewExecutionError(ReviewError):
    """Raised when review execution fails."""
    pass


class ReviewConfigurationError(ReviewError):
    """Raised when review configuration is invalid."""
    pass


class WorkspaceBoundaryViolation(ReviewError):
    """Raised when a file path escapes workspace boundaries."""
    pass


# ---------------------------------------------------------------------------
# E4.1.10 - Deterministic Hash Computation
# ---------------------------------------------------------------------------

def compute_finding_hash(finding: ReviewFinding) -> str:
    """Compute deterministic hash for a finding."""
    hash_payload = {
        "finding_id": finding.finding_id,
        "check_type": finding.check_type,
        "severity": finding.severity.value,
        "message": finding.message,
        "file_path": finding.file_path,
        "artifact_execution_id": finding.artifact_execution_id,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_check_result_hash(result: ReviewCheckResult) -> str:
    """Compute deterministic hash for a check result."""
    hash_payload = {
        "check_id": result.check_id,
        "check_type": result.check_type,
        "executed": result.executed,
        "skipped": result.skipped,
        "passed": result.passed,
        "findings_count": len(result.findings),
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_review_report_hash(report: ReviewReport) -> str:
    """Compute deterministic hash for a review report."""
    hash_payload = {
        "report_id": report.report_id,
        "review_id": report.review_id,
        "mission_id": report.mission_id,
        "total_findings": report.total_findings,
        "critical_findings": report.critical_findings,
        "error_findings": report.error_findings,
        "verdict": report.verdict.value,
        "files_reviewed": report.files_reviewed,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# E4.1.11 - Verdict Calculation
# ---------------------------------------------------------------------------

def calculate_verdict(findings: List[ReviewFinding]) -> Tuple[ReviewVerdict, List[str]]:
    """Calculate the review verdict from findings.

    Rules:
    - CRITICAL finding -> BLOCKED
    - ERROR finding -> FAIL
    - WARNING only -> PASS_WITH_WARNINGS
    - No findings -> PASS

    Args:
        findings: List of review findings

    Returns:
        Tuple of (verdict, reasons)
    """
    if not findings:
        return ReviewVerdict.PASS, ["No findings - review passed"]

    reasons = []

    # Check for blocking findings
    critical_findings = [f for f in findings if f.severity == ReviewSeverity.CRITICAL]
    error_findings = [f for f in findings if f.severity == ReviewSeverity.ERROR]
    warning_findings = [f for f in findings if f.severity == ReviewSeverity.WARNING]

    if critical_findings:
        reasons.append(f"{len(critical_findings)} CRITICAL finding(s) found")
        return ReviewVerdict.BLOCKED, reasons

    if error_findings:
        reasons.append(f"{len(error_findings)} ERROR finding(s) found")
        return ReviewVerdict.FAIL, reasons

    if warning_findings:
        reasons.append(f"{len(warning_findings)} WARNING finding(s) found")
        return ReviewVerdict.PASS_WITH_WARNINGS, reasons

    # Only INFO findings remain
    info_findings = [f for f in findings if f.severity == ReviewSeverity.INFO]
    reasons.append(f"{len(info_findings)} INFO finding(s) found")
    return ReviewVerdict.PASS_WITH_WARNINGS, reasons


# ---------------------------------------------------------------------------
# E4.1.12 - Path Validation Helpers
# ---------------------------------------------------------------------------

def validate_path_within_workspace(
    file_path: str,
    workspace_root: str,
    artifact_id: str = "",
) -> Tuple[bool, str, str]:
    """Validate that a file path is within workspace boundaries.

    Args:
        file_path: Repository-relative file path
        workspace_root: Absolute workspace root path
        artifact_id: Optional artifact ID for error messages

    Returns:
        Tuple of (is_valid, error_message, absolute_path)
    """
    if not file_path:
        return False, "Empty file path", ""

    # Check for absolute paths
    if file_path.startswith("/"):
        return False, f"Absolute paths not allowed: {file_path}", ""

    # Check for path traversal
    if ".." in file_path:
        return False, f"Path traversal not allowed: {file_path}", ""

    # Normalize path
    normalized = str(PurePosixPath(file_path))

    # Build absolute path
    absolute_path = os.path.join(workspace_root, normalized)

    # Resolve to real path for boundary check
    try:
        real_root = os.path.realpath(workspace_root)
        real_path = os.path.realpath(absolute_path)
    except (OSError, ValueError):
        return False, f"Cannot resolve path: {file_path}", absolute_path

    if not real_path.startswith(real_root):
        return False, f"Path escapes workspace: {file_path}", absolute_path

    return True, "", absolute_path


# ---------------------------------------------------------------------------
# E4.1.13 - Check ID Generators
# ---------------------------------------------------------------------------

def generate_check_id(check_type: str, index: int = 0) -> str:
    """Generate a deterministic check ID."""
    return f"check-{check_type}-{index:04d}"


def generate_finding_id(check_type: str, index: int = 0, sub_index: int = 0) -> str:
    """Generate a deterministic finding ID."""
    return f"finding-{check_type}-{index:04d}-{sub_index:04d}"


def generate_report_id(review_id: str) -> str:
    """Generate a report ID from review ID."""
    return f"rpt-{review_id[4:]}"


def generate_review_id(mission_id: str) -> str:
    """Generate a review ID from mission ID."""
    return f"rev-{mission_id[4:]}"
