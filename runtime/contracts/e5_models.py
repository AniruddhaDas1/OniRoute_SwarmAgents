"""E5 Self-Healing and Recovery Models for E4.x Pipeline.

Phase E5 — Self-Healing and Recovery Integration for Review Pipeline.

Provides models for:
- Recovery assessment (E5.1)
- Recovery planning (E5.2)
- Repair action determination
- Recovery attempt tracking
- Recovery result with evidence
- Retry limits and termination

Architecture:
    ReleaseReadinessResult (E4.3)
        ↓
    RecoveryAssessmentEngine (E5.1)
        ↓
    RecoveryAssessment (E5.1 output / E5.2 input)
        ↓
    RecoveryPlanBuilder (E5.2)
        ↓
    RecoveryPlan (E5.2 output)
        ↓
    RecoveryEngine (E5.3) - NOT YET IMPLEMENTED
        ↓
    RecoveryResult
        ↓
    E4.1 Re-review (loop)

Does NOT:
- Modify frozen E1 contracts
- Directly call providers (must use InvocationEngine)
- Perform unlimited retries
- Mark failed artifacts as successful
- Bypass E4 review pipeline
- Execute repairs (E5.2 is PLAN GENERATION ONLY)

Self-contained: depends only on Python stdlib + pydantic + E4 models.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from runtime.contracts.e42_models import (
    FindingCategory,
    FindingClassification,
    FindingAggregation,
    QualityGateDecision,
    QualityGateResult,
)
from runtime.contracts.e43_models import (
    ProgressionStatus,
    ReleaseReadinessLevel,
    ReleaseReadinessResult,
)


# ---------------------------------------------------------------------------
# E5.1 - Recovery Eligibility
# ---------------------------------------------------------------------------

class RecoveryEligibility(str, Enum):
    """Eligibility status for recovery.

    RECOVERABLE: Can be automatically recovered
    NOT_RECOVERABLE: Cannot be automatically recovered (requires human)
    NOT_NEEDED: No recovery needed (project is ready)
    TERMINAL_FAILURE: Recovery failed after max retries
    """

    RECOVERABLE = "RECOVERABLE"
    NOT_RECOVERABLE = "NOT_RECOVERABLE"
    NOT_NEEDED = "NOT_NEEDED"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"


# ---------------------------------------------------------------------------
# E5.2 - Repair Action Types
# ---------------------------------------------------------------------------

class RepairActionType(str, Enum):
    """Types of repair actions.

    REGENERATE: Full regeneration of artifact
    FIX_SYNTAX: Fix syntax errors in existing code
    FIX_STRUCTURE: Fix project structure issues
    FIX_CONFIGURATION: Fix configuration issues
    FIX_DEPENDENCY: Fix dependency issues
    REMOVE_PLACEHOLDER: Remove placeholder content
    ADD_FILE: Add missing required file
    FIX_CONTENT: Fix content quality issues
    MANUAL_REVIEW: Requires human review
    """

    REGENERATE = "REGENERATE"
    FIX_SYNTAX = "FIX_SYNTAX"
    FIX_STRUCTURE = "FIX_STRUCTURE"
    FIX_CONFIGURATION = "FIX_CONFIGURATION"
    FIX_DEPENDENCY = "FIX_DEPENDENCY"
    REMOVE_PLACEHOLDER = "REMOVE_PLACEHOLDER"
    ADD_FILE = "ADD_FILE"
    FIX_CONTENT = "FIX_CONTENT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


# ---------------------------------------------------------------------------
# E5.1 - Recovery Assessment (E5.1 output / E5.2 input)
# ---------------------------------------------------------------------------

class FindingReference(BaseModel):
    """Reference to a specific finding for traceability.

    Preserves the link between recovery actions and source findings.
    """

    model_config = ConfigDict(frozen=True)

    # Finding identity
    finding_id: str = Field(
        description="Original finding ID from E4.1"
    )
    check_id: str = Field(
        default="",
        description="Check that produced this finding"
    )
    check_type: str = Field(
        default="",
        description="Type of check"
    )

    # Finding context
    artifact_id: str = Field(
        description="Affected artifact ID"
    )
    file_path: str = Field(
        description="Affected file path"
    )

    # Finding classification
    category: FindingCategory = Field(
        description="Finding category from E4.2"
    )
    severity: str = Field(
        description="Finding severity"
    )
    message: str = Field(
        description="Finding message"
    )
    is_blocking: bool = Field(
        default=False,
        description="Whether finding blocks progression"
    )

    # Evidence
    evidence: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Finding evidence"
    )

    # Classification from E4.2
    rule_id: str = Field(
        default="",
        description="Rule that was violated"
    )


class GroupedFindings(BaseModel):
    """Grouped findings for a single repair target.

    When multiple findings affect the same artifact/file,
    they can be grouped into one coherent repair action.
    """

    model_config = ConfigDict(frozen=True)

    # Group identity
    group_id: str = Field(
        description="Unique group identifier"
    )

    # Target (all findings in this group affect the same target)
    artifact_id: str = Field(
        description="Target artifact ID"
    )
    file_path: str = Field(
        description="Target file path"
    )

    # All findings in this group
    findings: Tuple[FindingReference, ...] = Field(
        default_factory=tuple,
        description="Grouped findings"
    )

    # Aggregated severity (highest in group)
    max_severity: str = Field(
        description="Highest severity in group"
    )

    # Primary category (most common or highest priority)
    primary_category: FindingCategory = Field(
        description="Primary finding category"
    )

    # All categories represented
    categories: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="All finding categories in group"
    )

    # Counts
    total_findings: int = Field(
        default=0,
        description="Total findings in group"
    )
    blocking_findings: int = Field(
        default=0,
        description="Blocking findings in group"
    )


class RecoveryAssessment(BaseModel):
    """Assessment result from E5.1.

    This is the output of E5.1 (RecoveryAssessmentEngine) and the input
    to E5.2 (RecoveryPlanBuilder).

    Provides:
    - Recovery eligibility determination
    - Grouped findings for coherent repair
    - Deterministic evidence for plan generation
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    assessment_id: str = Field(
        description="Unique assessment identifier"
    )
    readiness_id: str = Field(
        description="Source ReleaseReadinessResult ID"
    )
    gate_id: str = Field(
        description="Source QualityGateResult ID"
    )

    # Assessment result
    eligibility: RecoveryEligibility = Field(
        description="Recovery eligibility status"
    )
    reason: str = Field(
        description="Reason for eligibility determination"
    )

    # Findings analysis
    total_findings: int = Field(
        default=0,
        description="Total findings analyzed"
    )
    grouped_findings: Tuple[GroupedFindings, ...] = Field(
        default_factory=tuple,
        description="Findings grouped by target artifact"
    )
    all_findings: Tuple[FindingReference, ...] = Field(
        default_factory=tuple,
        description="All individual findings"
    )

    # Severity summary
    critical_findings: int = Field(
        default=0,
        description="CRITICAL severity findings"
    )
    error_findings: int = Field(
        default=0,
        description="ERROR severity findings"
    )
    warning_findings: int = Field(
        default=0,
        description="WARNING severity findings"
    )

    # Category summary
    repairable_findings: int = Field(
        default=0,
        description="Findings that are auto-repairable"
    )
    manual_review_findings: int = Field(
        default=0,
        description="Findings requiring manual review"
    )

    # Affected artifacts
    affected_artifacts: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact IDs with findings"
    )
    affected_files: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="File paths with findings"
    )

    # Recovery constraints
    max_recovery_attempts: int = Field(
        default=3,
        description="Maximum recovery attempts"
    )

    # Evidence
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Assessment evidence"
    )

    # Determinism
    assessment_hash: str = Field(
        default="",
        description="SHA-256 hash of assessment"
    )


# ---------------------------------------------------------------------------
# E5.2 - Repair Action
# ---------------------------------------------------------------------------

class RepairAction(BaseModel):
    """Single repair action for a finding.

    Maps a finding to a specific repair action.
    Maps findings to concrete RepairActionType values.
    Groups related findings into coherent repair actions.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    action_id: str = Field(
        description="Unique repair action identifier"
    )

    # Finding traceable reference
    finding_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Associated finding identifiers (can be multiple if grouped)"
    )
    group_id: Optional[str] = Field(
        default=None,
        description="Group ID if this action represents grouped findings"
    )

    # Target
    artifact_id: str = Field(
        description="Target artifact ID"
    )
    file_path: str = Field(
        description="Target file path"
    )

    # Classification from finding
    category: FindingCategory = Field(
        description="Finding category"
    )
    severity: str = Field(
        description="Finding severity"
    )
    message: str = Field(
        description="Finding message"
    )

    # Repair action type (from CATEGORY_TO_ACTION mapping)
    action_type: RepairActionType = Field(
        description="Type of repair action"
    )

    # Priority and ordering
    priority: int = Field(
        description="Priority (0=highest)"
    )
    order: int = Field(
        description="Execution order (1-based)"
    )

    # Description
    description: str = Field(
        description="Human-readable repair description"
    )
    repair_prompt: str = Field(
        description="Prompt for LLM-based repair"
    )

    # Dependencies
    depends_on: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Action IDs that must complete before this action"
    )

    # Constraints
    max_retries: int = Field(
        default=2,
        description="Maximum retry attempts"
    )
    is_repairable: bool = Field(
        default=True,
        description="Whether this action can be automatically repaired"
    )

    # Manual intervention
    requires_manual_review: bool = Field(
        default=False,
        description="Whether manual review is required"
    )

    # Evidence references
    evidence_refs: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Evidence references for traceability"
    )


# ---------------------------------------------------------------------------
# E5.2 - Recovery Plan
# ---------------------------------------------------------------------------

class RecoveryPlan(BaseModel):
    """Recovery plan for a release readiness failure.

    Defines the repair actions needed and their ordering.
    Produced by E5.2 (RecoveryPlanBuilder) from E5.1 (RecoveryAssessment).

    Key features:
    - Deterministic action ordering
    - Dependency-aware recovery
    - Finding traceability
    - Grouped repair actions
    - Evidence preservation
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    plan_id: str = Field(
        description="Unique recovery plan identifier"
    )
    assessment_id: str = Field(
        description="Source RecoveryAssessment ID (E5.1)"
    )
    readiness_id: str = Field(
        description="Associated ReleaseReadinessResult ID (E4.3)"
    )
    gate_id: str = Field(
        description="Associated QualityGateResult ID (E4.2)"
    )

    # Eligibility
    eligibility: RecoveryEligibility = Field(
        description="Recovery eligibility"
    )
    reason: str = Field(
        description="Reason for eligibility status"
    )

    # Actions (deterministically ordered)
    actions: Tuple[RepairAction, ...] = Field(
        default_factory=tuple,
        description="Ordered repair actions with dependencies"
    )

    # Summary
    total_actions: int = Field(
        default=0,
        description="Total repair actions"
    )
    repairable_actions: int = Field(
        default=0,
        description="Actions that can be auto-repaired"
    )
    manual_actions: int = Field(
        default=0,
        description="Actions requiring manual review"
    )

    # Grouping information
    total_groups: int = Field(
        default=0,
        description="Number of grouped finding clusters"
    )
    findings_addressed: int = Field(
        default=0,
        description="Total findings addressed by this plan"
    )

    # Bounds
    max_recovery_attempts: int = Field(
        default=3,
        description="Maximum overall recovery attempts"
    )

    # Affected scope
    affected_artifacts: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact IDs affected by this plan"
    )
    affected_files: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="File paths affected by this plan"
    )

    # Evidence
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recovery plan evidence"
    )

    # Determinism
    plan_hash: str = Field(
        default="",
        description="SHA-256 hash of plan for determinism verification"
    )
    version: str = Field(
        default="1.0",
        description="Plan version for compatibility tracking"
    )


# ---------------------------------------------------------------------------
# E5.5 - Recovery Attempt
# ---------------------------------------------------------------------------

class RecoveryAttempt(BaseModel):
    """Single recovery attempt.

    Tracks what was attempted and its outcome.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    attempt_id: str = Field(
        description="Unique attempt identifier"
    )
    plan_id: str = Field(
        description="Associated recovery plan ID"
    )
    action_id: str = Field(
        description="Associated repair action ID"
    )

    # State
    attempt_number: int = Field(
        description="Attempt number (1-based)"
    )
    status: str = Field(
        description="Attempt status (PENDING, IN_PROGRESS, SUCCESS, FAILED, SKIPPED)"
    )

    # Outcome
    success: bool = Field(
        default=False,
        description="Whether attempt succeeded"
    )
    finding_resolved: bool = Field(
        default=False,
        description="Whether original finding was resolved"
    )

    # Details
    action_taken: str = Field(
        default="",
        description="Description of action taken"
    )
    result_message: str = Field(
        default="",
        description="Result message"
    )

    # Evidence
    before_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="State before recovery attempt"
    )
    after_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="State after recovery attempt"
    )

    # Timing
    started_at: str = Field(
        default="",
        description="ISO-8601 UTC start time"
    )
    completed_at: str = Field(
        default="",
        description="ISO-8601 UTC completion time"
    )
    duration_ms: float = Field(
        default=0.0,
        description="Attempt duration in milliseconds"
    )


# ---------------------------------------------------------------------------
# E5.6 - Recovery Result
# ---------------------------------------------------------------------------

class RecoveryResult(BaseModel):
    """Result of recovery attempt.

    Complete outcome of recovery with all attempts.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    recovery_id: str = Field(
        description="Unique recovery result identifier"
    )
    plan_id: str = Field(
        description="Associated recovery plan ID"
    )
    readiness_id: str = Field(
        description="Associated ReleaseReadinessResult ID"
    )

    # Overall outcome
    success: bool = Field(
        description="Whether recovery succeeded"
    )
    can_proceed: bool = Field(
        description="Whether project can now proceed"
    )
    status: RecoveryEligibility = Field(
        description="Final recovery status"
    )

    # Counts
    total_attempts: int = Field(
        default=0,
        description="Total recovery attempts"
    )
    successful_attempts: int = Field(
        default=0,
        description="Successful attempts"
    )
    failed_attempts: int = Field(
        default=0,
        description="Failed attempts"
    )
    skipped_attempts: int = Field(
        default=0,
        description="Skipped attempts"
    )

    # Resolution
    resolved_findings: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Findings that were resolved"
    )
    remaining_findings: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Findings still remaining"
    )

    # Files
    modified_files: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Files that were modified"
    )
    new_files: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Files that were created"
    )

    # Attempts
    attempts: Tuple[RecoveryAttempt, ...] = Field(
        default_factory=tuple,
        description="All recovery attempts"
    )

    # Evidence
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recovery evidence"
    )

    # Timing
    recovery_started: str = Field(
        default="",
        description="ISO-8601 UTC start time"
    )
    recovery_completed: str = Field(
        default="",
        description="ISO-8601 UTC completion time"
    )
    total_duration_ms: float = Field(
        default=0.0,
        description="Total recovery duration"
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="Whether recovery is deterministic"
    )
    recovery_hash: str = Field(
        default="",
        description="SHA-256 hash of recovery result"
    )


# ---------------------------------------------------------------------------
# E5.7 - Exception Classes
# ---------------------------------------------------------------------------

class RecoveryError(Exception):
    """Base exception for recovery failures."""
    pass


class RecoveryNotEligibleError(RecoveryError):
    """Raised when recovery is not eligible."""
    pass


class RecoveryBoundaryViolation(RecoveryError):
    """Raised when recovery violates safety boundaries."""
    pass


class RecoveryRetryLimitError(RecoveryError):
    """Raised when retry limit is exceeded."""
    pass


# ---------------------------------------------------------------------------
# E5.8 - Recovery Mapping Functions
# ---------------------------------------------------------------------------

# Mapping from FindingCategory to RepairActionType
CATEGORY_TO_ACTION: Dict[FindingCategory, RepairActionType] = {
    FindingCategory.SECURITY: RepairActionType.MANUAL_REVIEW,
    FindingCategory.SYNTAX: RepairActionType.FIX_SYNTAX,
    FindingCategory.STRUCTURE: RepairActionType.FIX_STRUCTURE,
    FindingCategory.CONTENT: RepairActionType.FIX_CONTENT,
    FindingCategory.PLACEHOLDER: RepairActionType.REMOVE_PLACEHOLDER,
    FindingCategory.DEPENDENCY: RepairActionType.FIX_DEPENDENCY,
    FindingCategory.FILESYSTEM: RepairActionType.MANUAL_REVIEW,
    FindingCategory.CONTRACT: RepairActionType.MANUAL_REVIEW,
    FindingCategory.QUALITY: RepairActionType.MANUAL_REVIEW,
    FindingCategory.CONFIGURATION: RepairActionType.FIX_CONFIGURATION,
    FindingCategory.OTHER: RepairActionType.MANUAL_REVIEW,
}

# Actions that are auto-repairable
AUTO_REPAIRABLE_ACTIONS: Tuple[RepairActionType, ...] = (
    RepairActionType.FIX_SYNTAX,
    RepairActionType.FIX_STRUCTURE,
    RepairActionType.FIX_CONFIGURATION,
    RepairActionType.FIX_DEPENDENCY,
    RepairActionType.REMOVE_PLACEHOLDER,
    RepairActionType.ADD_FILE,
    RepairActionType.FIX_CONTENT,
)

# Actions requiring manual review
MANUAL_REVIEW_ACTIONS: Tuple[RepairActionType, ...] = (
    RepairActionType.MANUAL_REVIEW,
    RepairActionType.REGENERATE,
)


def determine_repair_action_type(category: FindingCategory) -> RepairActionType:
    """Determine repair action type from finding category.

    Args:
        category: Finding category

    Returns:
        RepairActionType
    """
    return CATEGORY_TO_ACTION.get(category, RepairActionType.MANUAL_REVIEW)


def is_auto_repairable(action_type: RepairActionType) -> bool:
    """Check if action type is auto-repairable.

    Args:
        action_type: Repair action type

    Returns:
        True if auto-repairable
    """
    return action_type in AUTO_REPAIRABLE_ACTIONS


def determine_priority(severity: str) -> int:
    """Determine priority from severity.

    Args:
        severity: Finding severity

    Returns:
        Priority (0=highest)
    """
    priority_map = {
        "CRITICAL": 0,
        "ERROR": 1,
        "WARNING": 2,
        "INFO": 3,
    }
    return priority_map.get(severity, 3)


# ---------------------------------------------------------------------------
# E5.9 - Hash Computation
# ---------------------------------------------------------------------------

def compute_recovery_assessment_hash(assessment: RecoveryAssessment) -> str:
    """Compute deterministic SHA-256 hash for recovery assessment.

    Args:
        assessment: RecoveryAssessment to hash

    Returns:
        SHA-256 hash string
    """
    hash_payload = {
        "assessment_id": assessment.assessment_id,
        "readiness_id": assessment.readiness_id,
        "eligibility": assessment.eligibility.value,
        "total_findings": assessment.total_findings,
        "grouped_findings_count": len(assessment.grouped_findings),
        "finding_ids": sorted([f.finding_id for f in assessment.all_findings]),
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_recovery_plan_hash(plan: RecoveryPlan) -> str:
    """Compute deterministic SHA-256 hash for recovery plan.

    Uses only deterministic fields to ensure the same input always
    produces the same hash.

    Args:
        plan: RecoveryPlan to hash

    Returns:
        SHA-256 hash string
    """
    hash_payload = {
        "plan_id": plan.plan_id,
        "assessment_id": plan.assessment_id,
        "readiness_id": plan.readiness_id,
        "gate_id": plan.gate_id,
        "eligibility": plan.eligibility.value,
        "total_actions": plan.total_actions,
        "total_groups": plan.total_groups,
        "findings_addressed": plan.findings_addressed,
        # Use sorted action IDs for determinism
        "action_ids": sorted([a.action_id for a in plan.actions]),
        # Include ordering info
        "action_orders": sorted([a.order for a in plan.actions]),
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_recovery_result_hash(result: RecoveryResult) -> str:
    """Compute deterministic SHA-256 hash for recovery result.

    Args:
        result: RecoveryResult to hash

    Returns:
        SHA-256 hash string
    """
    hash_payload = {
        "recovery_id": result.recovery_id,
        "plan_id": result.plan_id,
        "success": result.success,
        "status": result.status.value,
        "total_attempts": result.total_attempts,
        "resolved_findings": sorted(list(result.resolved_findings)),
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# E5.10 - Ordering Constants
# ---------------------------------------------------------------------------

# Priority order for repair actions (lower number = higher priority)
ACTION_PRIORITY_ORDER = [
    RepairActionType.FIX_SYNTAX,
    RepairActionType.FIX_STRUCTURE,
    RepairActionType.FIX_CONFIGURATION,
    RepairActionType.FIX_DEPENDENCY,
    RepairActionType.REMOVE_PLACEHOLDER,
    RepairActionType.ADD_FILE,
    RepairActionType.FIX_CONTENT,
    RepairActionType.MANUAL_REVIEW,
    RepairActionType.REGENERATE,
]


def get_action_priority_rank(action_type: RepairActionType) -> int:
    """Get priority rank for an action type.

    Args:
        action_type: Repair action type

    Returns:
        Priority rank (lower = higher priority)
    """
    try:
        return ACTION_PRIORITY_ORDER.index(action_type)
    except ValueError:
        return len(ACTION_PRIORITY_ORDER)


# ---------------------------------------------------------------------------
# E5.11 - Dependency Constants
# ---------------------------------------------------------------------------

# Categories that indicate dependencies on other artifacts
DEPENDENCY_INDUCING_CATEGORIES = frozenset([
    FindingCategory.DEPENDENCY,
    FindingCategory.FILESYSTEM,
])

# Categories that are typically foundational (should be fixed first)
FOUNDATIONAL_CATEGORIES = frozenset([
    FindingCategory.CONFIGURATION,
    FindingCategory.STRUCTURE,
    FindingCategory.SYNTAX,
])


def is_foundational_category(category: FindingCategory) -> bool:
    """Check if a category is foundational (should be fixed first).

    Args:
        category: Finding category

    Returns:
        True if foundational
    """
    return category in FOUNDATIONAL_CATEGORIES


def indicates_dependency(category: FindingCategory) -> bool:
    """Check if a category indicates dependencies on other artifacts.

    Args:
        category: Finding category

    Returns:
        True if indicates dependency
    """
    return category in DEPENDENCY_INDUCING_CATEGORIES
