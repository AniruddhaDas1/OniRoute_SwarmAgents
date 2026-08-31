"""E5 Self-Healing and Recovery Models for E4.x Pipeline.

Phase E5 — Self-Healing and Recovery Integration for Review Pipeline.

Provides models for:
- Recovery assessment and planning
- Repair action determination
- Recovery attempt tracking
- Recovery result with evidence
- Retry limits and termination

Architecture:
    ReleaseReadinessResult (E4.3)
        ↓
    RecoveryAssessmentEngine (E5.1)
        ↓
    RecoveryPlan (E5.2)
        ↓
    RecoveryEngine (E5.3)
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
# E5.3 - Repair Action
# ---------------------------------------------------------------------------

class RepairAction(BaseModel):
    """Single repair action for a finding.

    Maps a finding to a specific repair action.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    action_id: str = Field(
        description="Unique repair action identifier"
    )
    finding_id: str = Field(
        description="Associated finding identifier"
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

    # Repair
    action_type: RepairActionType = Field(
        description="Type of repair action"
    )
    priority: int = Field(
        description="Priority (0=highest)"
    )
    description: str = Field(
        description="Human-readable repair description"
    )
    repair_prompt: str = Field(
        description="Prompt for LLM-based repair"
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


# ---------------------------------------------------------------------------
# E5.4 - Recovery Plan
# ---------------------------------------------------------------------------

class RecoveryPlan(BaseModel):
    """Recovery plan for a release readiness failure.

    Defines the repair actions needed and their ordering.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    plan_id: str = Field(
        description="Unique recovery plan identifier"
    )
    readiness_id: str = Field(
        description="Associated ReleaseReadinessResult ID"
    )
    gate_id: str = Field(
        description="Associated QualityGateResult ID"
    )

    # Eligibility
    eligibility: RecoveryEligibility = Field(
        description="Recovery eligibility"
    )
    reason: str = Field(
        description="Reason for eligibility status"
    )

    # Actions
    actions: Tuple[RepairAction, ...] = Field(
        default_factory=tuple,
        description="Ordered repair actions"
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

    # Bounds
    max_recovery_attempts: int = Field(
        default=3,
        description="Maximum overall recovery attempts"
    )

    # Evidence
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recovery plan evidence"
    )

    # Determinism
    plan_hash: str = Field(
        default="",
        description="SHA-256 hash of plan"
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

def compute_recovery_plan_hash(plan: RecoveryPlan) -> str:
    """Compute deterministic SHA-256 hash for recovery plan.

    Args:
        plan: RecoveryPlan to hash

    Returns:
        SHA-256 hash string
    """
    hash_payload = {
        "plan_id": plan.plan_id,
        "readiness_id": plan.readiness_id,
        "eligibility": plan.eligibility.value,
        "total_actions": plan.total_actions,
        "action_ids": [a.action_id for a in plan.actions],
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
        "resolved_findings": list(result.resolved_findings),
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
