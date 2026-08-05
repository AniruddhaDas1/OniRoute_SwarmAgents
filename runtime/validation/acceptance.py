"""Acceptance Engine (Phase P5.E4).

Consumes VerificationResult and evaluates Acceptance Criteria, Contract Completion, Quality Thresholds,
Mission Success, and Release Readiness to produce an immutable AcceptanceReport.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from runtime.contracts.models import EngineeringContractReport
from runtime.validation.exceptions import AcceptanceEvaluationError
from runtime.validation.models import AcceptanceReport, VerificationResult


class AcceptanceEngine:
    """Acceptance Engine for Phase P5.E4."""

    def evaluate_all_acceptances(
        self,
        verifications: List[VerificationResult],
        contract_report: Optional[EngineeringContractReport] = None,
    ) -> List[AcceptanceReport]:
        """Evaluate acceptance for a list of VerificationResults.

        Args:
            verifications: List of VerificationResult contracts.
            contract_report: Optional EngineeringContractReport specification.

        Returns:
            List[AcceptanceReport]: Immutable acceptance reports per verification.
        """
        if not isinstance(verifications, list):
            raise AcceptanceEvaluationError(
                f"AcceptanceEngine expects a list of VerificationResult items. "
                f"Received: {type(verifications).__name__}"
            )

        reports: List[AcceptanceReport] = []
        for v in verifications:
            report = self.evaluate_acceptance(v, contract_report)
            reports.append(report)

        return reports

    def evaluate_acceptance(
        self,
        verification_result: VerificationResult,
        contract_report: Optional[EngineeringContractReport] = None,
    ) -> AcceptanceReport:
        """Evaluate acceptance criteria for a single VerificationResult.

        Args:
            verification_result: Immutable VerificationResult contract.
            contract_report: Optional EngineeringContractReport specification.

        Returns:
            AcceptanceReport: Immutable acceptance report contract.
        """
        start_time = time.perf_counter()

        if not isinstance(verification_result, VerificationResult):
            raise AcceptanceEvaluationError(
                f"AcceptanceEngine consumes ONLY VerificationResult. "
                f"Received invalid type: {type(verification_result).__name__}"
            )

        vrf_id = verification_result.verification_id

        accepted_criteria: List[str] = []
        rejected_criteria: List[str] = []

        # 1. Build Verification Criteria
        if verification_result.build_status == "PASSED":
            accepted_criteria.append("Build Verification: Code compiled cleanly with zero build errors.")
        else:
            rejected_criteria.append("Build Verification: Code failed compilation check.")

        # 2. Test Execution Criteria
        if verification_result.test_status == "PASSED":
            accepted_criteria.append("Test Execution: Unit and integration test suite passed 100%.")
        else:
            rejected_criteria.append("Test Execution: Unit/integration tests failed.")

        # 3. Coverage Threshold Criteria
        if verification_result.coverage_percentage >= 80.0:
            accepted_criteria.append(f"Coverage Threshold: Code coverage ({verification_result.coverage_percentage:.1f}%) meets 80.0% benchmark.")
        else:
            rejected_criteria.append(f"Coverage Threshold: Code coverage ({verification_result.coverage_percentage:.1f}%) below 80.0% threshold.")

        # 4. Lint & Formatting Criteria
        if verification_result.lint_status == "PASSED":
            accepted_criteria.append("Lint & Formatting: Zero lint or code style violations detected.")
        else:
            rejected_criteria.append("Lint & Formatting: Code formatting or lint check failed.")

        # 5. Security Gate Criteria
        if verification_result.security_status == "PASSED":
            accepted_criteria.append("Security Gate: Sandboxing, secret scanning, and path bounds verified.")
        else:
            rejected_criteria.append("Security Gate: Security check failed.")

        # 6. Performance Gate Criteria
        if verification_result.performance_status == "PASSED":
            accepted_criteria.append("Performance Gate: Execution latency within system benchmarks.")
        else:
            rejected_criteria.append("Performance Gate: Performance benchmark failed.")

        # 7. Artifact Validity Criteria
        if verification_result.artifact_status == "PASSED":
            accepted_criteria.append("Artifact Validity: All required contract output artifacts generated.")
        else:
            rejected_criteria.append("Artifact Validity: Missing contract output artifacts.")

        # 8. Determine Final Verdict and Production Readiness
        production_ready = len(rejected_criteria) == 0
        mission_status = "SUCCESS" if production_ready else "FAILED"
        acceptance_verdict = "ACCEPTED" if production_ready else "REJECTED"

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        acpt_id = f"acpt-{abs(hash(f'{vrf_id}-{timestamp_iso}')) % 1000000:06d}"

        evidence: Dict[str, Any] = {
            "verification_id": vrf_id,
            "accepted_criteria_count": len(accepted_criteria),
            "rejected_criteria_count": len(rejected_criteria),
            "production_ready": production_ready,
            "latency_ms": round(elapsed_ms, 3),
            "zero_workspace_write": True,
            "timestamp": timestamp_iso,
        }

        # Compute SHA-256 acceptance hash
        acpt_hash = self._compute_acceptance_hash(
            acceptance_id=acpt_id,
            verification_id=vrf_id,
            mission_status=mission_status,
            acceptance_verdict=acceptance_verdict,
            accepted_criteria=accepted_criteria,
        )

        return AcceptanceReport(
            acceptance_id=acpt_id,
            verification_id=vrf_id,
            mission_status=mission_status,
            production_ready=production_ready,
            acceptance_verdict=acceptance_verdict,
            rejected_criteria=rejected_criteria,
            accepted_criteria=accepted_criteria,
            evidence=evidence,
            timestamp=timestamp_iso,
            acceptance_hash=acpt_hash,
        )

    def _compute_acceptance_hash(
        self,
        acceptance_id: str,
        verification_id: str,
        mission_status: str,
        acceptance_verdict: str,
        accepted_criteria: List[str],
    ) -> str:
        """Compute SHA-256 hash of acceptance report payload."""
        payload = f"{acceptance_id}:{verification_id}:{mission_status}:{acceptance_verdict}:{len(accepted_criteria)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
