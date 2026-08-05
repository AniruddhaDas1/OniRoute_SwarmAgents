"""OniRoute Agent Runtime — Recovery Engine (ACR-006 Phase R4 & R5).

Provides deterministic runtime recovery without modifying the frozen architecture.

Components
----------
FailureClassifier     — Classifies failures into canonical FailureCategory types.
RetryManager          — Manages retry eligibility, delay policy, and metrics.
ReviewPolicy          — Declarative policy contract and implementations (Default, Strict, Permissive, RuleBased).
RuntimeReviewEngine   — Pauses execution, emits REVIEW_REQUESTED, awaits decision per policy.
RecoveryOrchestrator  — Coordinates pause/resume/recovery lifecycle.
RecoveryReport        — Immutable report capturing the full recovery audit trail.
"""

from .classifier import FailureCategory, FailureClassification, FailureClassifier
from .events import RecoveryEventType
from .models import (
    PauseRecord,
    RecoveryMetrics,
    RecoveryReport,
    RetryPolicy,
    RetryRecord,
    ReviewDecision,
    ReviewOutcome,
    ReviewRecord,
)
from .orchestrator import RecoveryOrchestrator
from .policy import (
    DEPLOYMENT_POLICY,
    INFRASTRUCTURE_POLICY,
    SECURITY_POLICY,
    DefaultReviewPolicy,
    PermissiveReviewPolicy,
    ReviewPolicy,
    ReviewRule,
    RuleBasedReviewPolicy,
    StrictReviewPolicy,
)
from .retry import RetryManager
from .review import RuntimeReviewEngine

__all__ = [
    # Failure classification
    "FailureCategory",
    "FailureClassification",
    "FailureClassifier",
    # Events
    "RecoveryEventType",
    # Models
    "PauseRecord",
    "RetryPolicy",
    "RetryRecord",
    "ReviewDecision",
    "ReviewOutcome",
    "ReviewRecord",
    "RecoveryMetrics",
    "RecoveryReport",
    # Policies (R5)
    "ReviewPolicy",
    "DefaultReviewPolicy",
    "StrictReviewPolicy",
    "PermissiveReviewPolicy",
    "RuleBasedReviewPolicy",
    "ReviewRule",
    "SECURITY_POLICY",
    "INFRASTRUCTURE_POLICY",
    "DEPLOYMENT_POLICY",
    # Engines
    "RetryManager",
    "RuntimeReviewEngine",
    "RecoveryOrchestrator",
]
