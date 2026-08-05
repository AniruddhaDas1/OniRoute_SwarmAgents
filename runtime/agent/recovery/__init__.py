"""OniRoute Agent Runtime — Recovery Engine (ACR-006 Phase R4).

Provides deterministic runtime recovery without modifying the frozen architecture.

Components
----------
FailureClassifier    — Classifies failures into canonical FailureCategory types.
RetryManager         — Manages retry eligibility, delay policy, and metrics.
RuntimeReviewEngine  — Pauses execution, emits REVIEW_REQUESTED, awaits decision.
RecoveryOrchestrator — Coordinates pause/resume/recovery lifecycle.
RecoveryReport       — Immutable report capturing the full recovery audit trail.
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
    # Engines
    "RetryManager",
    "RuntimeReviewEngine",
    "RecoveryOrchestrator",
]
