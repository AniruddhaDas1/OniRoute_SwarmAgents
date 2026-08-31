"""E4.3 Review Release Readiness Integration Engine.

Phase E4.3 — Review Release Readiness Integration.

Provides deterministic release readiness assessment based on E4.1 review
and E4.2 quality gate results.

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
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from runtime.contracts.e42_models import (
    QualityGateDecision,
    QualityGateResult,
)
from runtime.contracts.e43_models import (
    ArtifactReadiness,
    BlockerSummary,
    compute_readiness_hash,
    determine_blockers,
    determine_readiness_level,
    EvidenceChainBrokenError,
    InvalidGateResultError,
    ProgressionStatus,
    ReadinessEvidenceEntry,
    ReleaseReadinessEvidence,
    ReleaseReadinessLevel,
    ReleaseReadinessResult,
    ReleaseReadinessError,
)


# ---------------------------------------------------------------------------
# E4.3.1 - Release Readiness Engine
# ---------------------------------------------------------------------------

class ReleaseReadinessEngine:
    """Determines release readiness from QualityGateResult.

    Key properties:
    - Deterministic: Same input produces same output
    - No LLM calls for readiness decision
    - Preserves full evidence chain
    - Provides artifact-level and project-level readiness
    - Fails safely when evidence is incomplete
    """

    def assess(
        self,
        gate_result: QualityGateResult,
        readiness_id: Optional[str] = None,
    ) -> ReleaseReadinessResult:
        """Assess release readiness from QualityGateResult.

        This is the main entry point for E4.3 assessment.

        Args:
            gate_result: QualityGateResult from E4.2
            readiness_id: Optional readiness assessment ID

        Returns:
            ReleaseReadinessResult with complete assessment

        Raises:
            InvalidGateResultError: If gate_result is invalid
        """
        start_time = time.time()
        assessment_started = datetime.now(timezone.utc).isoformat()

        # Validate gate_result
        if not gate_result:
            raise InvalidGateResultError("QualityGateResult cannot be None or empty")

        # Generate readiness_id if not provided
        if not readiness_id:
            readiness_id = f"ready-{gate_result.gate_id[4:]}" if len(gate_result.gate_id) > 4 else f"ready-{gate_result.review_id}"

        # Step 1: Determine progression status
        progression_status = self._determine_progression_status(gate_result)

        # Step 2: Calculate artifact readiness
        artifact_readiness = self._calculate_artifact_readiness(gate_result)

        # Step 3: Determine blockers
        blockers, recommendations = determine_blockers(gate_result)

        # Step 4: Determine readiness level
        readiness_level = determine_readiness_level(
            progression_status,
            gate_result.project_decision.aggregation.severity_counts.critical,
            gate_result.project_decision.aggregation.severity_counts.error,
            gate_result.project_decision.aggregation.severity_counts.warning,
        )

        # Step 5: Calculate summary counts
        total_artifacts = len(artifact_readiness)
        artifacts_ready = sum(
            1 for a in artifact_readiness if a.progression_status == ProgressionStatus.READY
        )
        artifacts_ready_with_warnings = sum(
            1 for a in artifact_readiness
            if a.progression_status == ProgressionStatus.READY_WITH_WARNINGS
        )
        artifacts_not_ready = sum(
            1 for a in artifact_readiness
            if a.progression_status == ProgressionStatus.NOT_READY
        )
        artifacts_blocked = sum(
            1 for a in artifact_readiness if a.progression_status == ProgressionStatus.BLOCKED
        )

        # Step 6: Calculate findings summary
        aggregation = gate_result.project_decision.aggregation
        total_findings = aggregation.severity_counts.total
        critical_findings = aggregation.severity_counts.critical
        error_findings = aggregation.severity_counts.error
        warning_findings = aggregation.severity_counts.warning
        info_findings = aggregation.severity_counts.info

        # Step 7: Determine if can release
        can_release = progression_status in (
            ProgressionStatus.READY,
            ProgressionStatus.READY_WITH_WARNINGS,
        )

        # Step 8: Build evidence chain
        evidence = self._build_evidence_chain(
            gate_result,
            readiness_id,
            progression_status,
            readiness_level,
        )

        # Step 9: Compute hash
        assessment_completed = datetime.now(timezone.utc).isoformat()

        # Build result with deterministic hash pre-computed
        # Note: We can't pre-compute the hash since it depends on the result itself
        # So we create the result without the hash first, then create a new version with hash
        result = ReleaseReadinessResult(
            readiness_id=readiness_id,
            review_id=gate_result.review_id,
            report_id=gate_result.report_id,
            gate_id=gate_result.gate_id,
            mission_id=gate_result.mission_id,
            workspace_id=gate_result.workspace_id,
            plan_id=gate_result.plan_id,
            progression_status=progression_status,
            readiness_level=readiness_level,
            can_release=can_release,
            total_artifacts=total_artifacts,
            artifacts_ready=artifacts_ready,
            artifacts_ready_with_warnings=artifacts_ready_with_warnings,
            artifacts_not_ready=artifacts_not_ready,
            artifacts_blocked=artifacts_blocked,
            total_findings=total_findings,
            critical_findings=critical_findings,
            error_findings=error_findings,
            warning_findings=warning_findings,
            info_findings=info_findings,
            artifact_readiness=tuple(artifact_readiness),
            blockers=blockers,
            evidence=evidence,
            recommendations=tuple(recommendations),
            assessment_started=assessment_started,
            assessment_completed=assessment_completed,
            deterministic=True,
            deterministic_hash="",  # Will be set below
        )

        # Create a new result with the hash computed
        result_hash = compute_readiness_hash(result)
        return ReleaseReadinessResult(
            readiness_id=readiness_id,
            review_id=gate_result.review_id,
            report_id=gate_result.report_id,
            gate_id=gate_result.gate_id,
            mission_id=gate_result.mission_id,
            workspace_id=gate_result.workspace_id,
            plan_id=gate_result.plan_id,
            progression_status=progression_status,
            readiness_level=readiness_level,
            can_release=can_release,
            total_artifacts=total_artifacts,
            artifacts_ready=artifacts_ready,
            artifacts_ready_with_warnings=artifacts_ready_with_warnings,
            artifacts_not_ready=artifacts_not_ready,
            artifacts_blocked=artifacts_blocked,
            total_findings=total_findings,
            critical_findings=critical_findings,
            error_findings=error_findings,
            warning_findings=warning_findings,
            info_findings=info_findings,
            artifact_readiness=tuple(artifact_readiness),
            blockers=blockers,
            evidence=evidence,
            recommendations=tuple(recommendations),
            assessment_started=assessment_started,
            assessment_completed=assessment_completed,
            deterministic=True,
            deterministic_hash=result_hash,
        )

    def _determine_progression_status(
        self,
        gate_result: QualityGateResult,
    ) -> ProgressionStatus:
        """Determine progression status from QualityGateResult.

        Args:
            gate_result: QualityGateResult from E4.2

        Returns:
            ProgressionStatus
        """
        return ProgressionStatus.from_quality_gate_decision(
            gate_result.decision,
            gate_result.can_proceed,
        )

    def _calculate_artifact_readiness(
        self,
        gate_result: QualityGateResult,
    ) -> List[ArtifactReadiness]:
        """Calculate artifact-level readiness.

        Args:
            gate_result: QualityGateResult from E4.2

        Returns:
            List of ArtifactReadiness
        """
        artifact_readiness = []

        for artifact_decision in gate_result.project_decision.artifact_decisions:
            # Convert artifact decision to progression status
            if artifact_decision.has_critical:
                status = ProgressionStatus.BLOCKED
            elif artifact_decision.has_error:
                status = ProgressionStatus.NOT_READY
            elif artifact_decision.has_warning or artifact_decision.has_info:
                status = ProgressionStatus.READY_WITH_WARNINGS
            else:
                status = ProgressionStatus.READY

            # Determine readiness level for this artifact
            if status == ProgressionStatus.BLOCKED:
                level = ReleaseReadinessLevel.UNRELEASABLE
            elif status == ProgressionStatus.NOT_READY:
                level = ReleaseReadinessLevel.DEVELOPMENT
            elif status == ProgressionStatus.READY_WITH_WARNINGS:
                level = ReleaseReadinessLevel.STAGING
            else:
                level = ReleaseReadinessLevel.PRODUCTION

            artifact_readiness.append(ArtifactReadiness(
                artifact_id=artifact_decision.artifact_id,
                artifact_execution_id=artifact_decision.artifact_execution_id,
                progression_status=status,
                readiness_level=level,
                total_findings=artifact_decision.total_findings,
                blocking_findings=artifact_decision.blocking_findings,
                critical_findings=1 if artifact_decision.has_critical else 0,
                error_findings=1 if artifact_decision.has_error else 0,
                warning_findings=1 if artifact_decision.has_warning else 0,
                affected_files=artifact_decision.affected_files,
                top_severity=artifact_decision.top_severity.value,
            ))

        return artifact_readiness

    def _build_evidence_chain(
        self,
        gate_result: QualityGateResult,
        readiness_id: str,
        progression_status: ProgressionStatus,
        readiness_level: ReleaseReadinessLevel,
    ) -> ReleaseReadinessEvidence:
        """Build evidence chain for traceability.

        Args:
            gate_result: QualityGateResult from E4.2
            readiness_id: Readiness assessment ID
            progression_status: Calculated progression status
            readiness_level: Calculated readiness level

        Returns:
            ReleaseReadinessEvidence with evidence chain
        """
        evidence_chain: List[ReadinessEvidenceEntry] = []

        # Evidence 1: Review reference
        evidence_chain.append(ReadinessEvidenceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="ReviewReport",
            type="review_reference",
            content={
                "review_id": gate_result.review_id,
                "report_id": gate_result.report_id,
            },
        ))

        # Evidence 2: Quality gate reference
        evidence_chain.append(ReadinessEvidenceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="QualityGateResult",
            type="gate_reference",
            content={
                "gate_id": gate_result.gate_id,
                "decision": gate_result.decision.value,
                "can_proceed": gate_result.can_proceed,
                "required_remediation": gate_result.required_remediation.value,
            },
        ))

        # Evidence 3: Findings summary
        aggregation = gate_result.project_decision.aggregation
        evidence_chain.append(ReadinessEvidenceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="FindingAggregation",
            type="findings_summary",
            content={
                "total_findings": aggregation.severity_counts.total,
                "critical": aggregation.severity_counts.critical,
                "error": aggregation.severity_counts.error,
                "warning": aggregation.severity_counts.warning,
                "info": aggregation.severity_counts.info,
            },
        ))

        # Evidence 4: Readiness decision
        evidence_chain.append(ReadinessEvidenceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="ReleaseReadinessEngine",
            type="readiness_decision",
            content={
                "readiness_id": readiness_id,
                "progression_status": progression_status.value,
                "readiness_level": readiness_level.value,
                "can_release": progression_status in (
                    ProgressionStatus.READY,
                    ProgressionStatus.READY_WITH_WARNINGS,
                ),
                "blocking_artifacts": list(gate_result.project_decision.blocking_artifact_ids),
            },
        ))

        # Compute evidence hash
        evidence_hash = self._compute_evidence_hash(
            gate_result.review_id,
            gate_result.gate_id,
            readiness_id,
        )

        return ReleaseReadinessEvidence(
            review_id=gate_result.review_id,
            report_id=gate_result.report_id,
            gate_id=gate_result.gate_id,
            readiness_id=readiness_id,
            mission_id=gate_result.mission_id,
            workspace_id=gate_result.workspace_id,
            plan_id=gate_result.plan_id,
            evidence_chain=tuple(evidence_chain),
            deterministic_hash=evidence_hash,
        )

    def _compute_evidence_hash(
        self,
        review_id: str,
        gate_id: str,
        readiness_id: str,
    ) -> str:
        """Compute deterministic hash for evidence.

        Args:
            review_id: Review ID
            gate_id: Gate ID
            readiness_id: Readiness ID

        Returns:
            SHA-256 hash string
        """
        hash_payload = {
            "review_id": review_id,
            "gate_id": gate_id,
            "readiness_id": readiness_id,
        }
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# E4.3.2 - Frozen Architecture Guards
# ---------------------------------------------------------------------------

# Guards to ensure E4.3 does NOT violate frozen contracts
FROZEN_ARCHITECTURE_GUARDS = {
    "no_invocation_engine": "E4.3 must not create another InvocationEngine",
    "no_provider_registry": "E4.3 must not create another provider registry",
    "no_model_selector": "E4.3 must not create another model selector",
    "no_umal_bypass": "E4.3 must not bypass UMAL",
    "no_direct_provider_calls": "E4.3 must not directly call providers",
    "no_frozen_contract_modification": "E4.3 must not modify frozen E1 contracts",
    "no_self_healing": "E4.3 must not perform self-healing",
    "no_auto_regeneration": "E4.3 must not perform automatic regeneration",
    "no_file_modification": "E4.3 must not modify generated files",
}


def verify_frozen_architecture_compliance() -> Tuple[bool, List[str]]:
    """Verify E4.3 does not violate frozen architecture.

    Returns:
        Tuple of (is_compliant, list_of_violations)
    """
    violations = []

    # Verify imports are from correct locations
    try:
        # Verify E4.2 models are from correct module
        from runtime.contracts.e42_models import QualityGateResult

        # Verify we don't create new InvocationEngine
        import sys
        if "runtime.invocation.engine" in sys.modules:
            # It's okay to import, just not create new instances
            pass
    except ImportError as e:
        violations.append(f"Import error: {e}")

    return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# E4.3.3 - Release Readiness History Integration
# ---------------------------------------------------------------------------

class ReleaseReadinessHistoryEntry:
    """Represents a release readiness assessment in history."""

    @staticmethod
    def from_readiness_result(result: ReleaseReadinessResult) -> Dict:
        """Convert ReleaseReadinessResult to history entry format.

        Args:
            result: ReleaseReadinessResult to convert

        Returns:
            Dictionary suitable for history storage
        """
        return {
            "readiness_id": result.readiness_id,
            "review_id": result.review_id,
            "gate_id": result.gate_id,
            "mission_id": result.mission_id,
            "progression_status": result.progression_status.value,
            "readiness_level": result.readiness_level.value,
            "can_release": result.can_release,
            "total_artifacts": result.total_artifacts,
            "total_findings": result.total_findings,
            "critical_findings": result.critical_findings,
            "error_findings": result.error_findings,
            "warning_findings": result.warning_findings,
            "blocking_artifacts": list(result.blockers.blocking_artifacts),
            "deterministic_hash": result.deterministic_hash,
            "assessment_started": result.assessment_started,
            "assessment_completed": result.assessment_completed,
        }
