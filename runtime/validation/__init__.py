"""Validation & Acceptance Subsystem Package (Phase P5.E4).

Consumes UpdatedEngineeringResult or EngineeringResult and produces VerificationResult & AcceptanceReport.
"""

from runtime.validation.acceptance import AcceptanceEngine
from runtime.validation.exceptions import AcceptanceEvaluationError, ValidationAcceptanceError, VerificationExecutionError
from runtime.validation.models import AcceptanceReport, VerificationResult
from runtime.validation.verification import VerificationEngine

__all__ = [
    "VerificationEngine",
    "AcceptanceEngine",
    "VerificationResult",
    "AcceptanceReport",
    "ValidationAcceptanceError",
    "VerificationExecutionError",
    "AcceptanceEvaluationError",
]
