"""E4.3 Review Release Readiness Integration Tests.

Tests verify:
1. Progression Status Determination (E4.3.1)
2. Readiness Level Determination (E4.3.2)
3. Artifact Readiness Calculation (E4.3.3)
4. Blocker Summary (E4.3.4)
5. Release Readiness Assessment (E4.3.5)
6. Evidence Preservation (E4.3.6)
7. Idempotency (E4.3.7)
8. Failure Handling (E4.3.8)
9. Frozen Architecture Guards (E4.3.9)
10. End-to-End Tests (E4.3.10)
"""

from __future__ import annotations

import tempfile
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from runtime.contracts.e4_models import (
    ReviewFinding,
    ReviewReport,
    ReviewRequest,
    ReviewSeverity,
    ReviewVerdict,
)
from runtime.contracts.e42_models import (
    ArtifactLevelDecision,
    FindingAggregation,
    GroupedByArtifact,
    GroupedByCategory,
    GroupedByFile,
    GroupedByRule,
    ProjectLevelDecision,
    QualityGateDecision,
    QualityGateResult,
    SeverityCounts,
    BlockingCounts,
    CategoryCounts,
)
from runtime.contracts.e42_engine import QualityGateDecisionEngine
from runtime.contracts.e43_models import (
    ArtifactReadiness,
    BlockerSummary,
    determine_blockers,
    determine_readiness_level,
    ProgressionStatus,
    ReleaseReadinessLevel,
    ReleaseReadinessResult,
    ReleaseReadinessError,
    compute_readiness_hash,
)
from runtime.contracts.e43_engine import (
    ReleaseReadinessEngine,
    ReleaseReadinessHistoryEntry,
    verify_frozen_architecture_compliance,
    FROZEN_ARCHITECTURE_GUARDS,
)
from runtime.contracts.e34_models import ArtifactFileResult


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def create_sample_finding(
    finding_id: str = "f-001",
    severity: ReviewSeverity = ReviewSeverity.ERROR,
    file_path: str = "src/main.py",
    artifact_id: str = "art-001",
    rule_id: str = "R001",
    check_type: str = "syntax_check",
    is_blocking: bool = True,
) -> ReviewFinding:
    """Create a sample ReviewFinding for testing."""
    return ReviewFinding(
        finding_id=finding_id,
        check_id=f"check-{check_type}",
        check_type=check_type,
        mission_id="msn-test",
        workspace_id="ws-test",
        plan_id="plan-test",
        artifact_execution_id=f"aeu-{artifact_id}",
        artifact_id=artifact_id,
        file_path=file_path,
        absolute_path=f"/workspace/{file_path}",
        severity=severity,
        message=f"Test finding {finding_id}",
        evidence=(f"Evidence for {finding_id}",),
        is_blocking=is_blocking,
        rule_id=rule_id,
        rule_name=f"Rule {rule_id}",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def create_sample_report(
    findings: List[ReviewFinding],
    verdict: ReviewVerdict = ReviewVerdict.PASS,
) -> ReviewReport:
    """Create a sample ReviewReport for testing."""
    critical = sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL)
    error = sum(1 for f in findings if f.severity == ReviewSeverity.ERROR)
    warning = sum(1 for f in findings if f.severity == ReviewSeverity.WARNING)
    info = sum(1 for f in findings if f.severity == ReviewSeverity.INFO)

    return ReviewReport(
        report_id="rpt-test-001",
        review_id="rev-test-001",
        mission_id="msn-test",
        workspace_id="ws-test",
        plan_id="plan-test",
        workspace_root="/workspace",
        repository_scope="src/",
        total_checks=5,
        checks_passed=4,
        checks_failed=1 if findings else 0,
        check_results=(),
        total_findings=len(findings),
        critical_findings=critical,
        error_findings=error,
        warning_findings=warning,
        info_findings=info,
        findings=tuple(findings),
        verdict=verdict,
        verdict_reasons=(f"{verdict.value}",),
        review_started=datetime.now(timezone.utc).isoformat(),
        review_completed=datetime.now(timezone.utc).isoformat(),
    )


def create_sample_gate_result(
    report: ReviewReport,
    decision: QualityGateDecision = QualityGateDecision.PASS,
    can_proceed: bool = True,
) -> QualityGateResult:
    """Create a sample QualityGateResult for testing."""
    gate_engine = QualityGateDecisionEngine()
    return gate_engine.analyze(report)


# ---------------------------------------------------------------------------
# E4.3.1 - Progression Status Tests
# ---------------------------------------------------------------------------

class TestProgressionStatus:
    """Test progression status determination."""

    def test_progression_from_pass(self):
        """Test progression from PASS gate decision."""
        status = ProgressionStatus.from_quality_gate_decision(
            QualityGateDecision.PASS, True
        )
        assert status == ProgressionStatus.READY

    def test_progression_from_pass_with_warnings(self):
        """Test progression from PASS_WITH_WARNINGS."""
        status = ProgressionStatus.from_quality_gate_decision(
            QualityGateDecision.PASS_WITH_WARNINGS, True
        )
        assert status == ProgressionStatus.READY_WITH_WARNINGS

    def test_progression_from_fail(self):
        """Test progression from FAIL."""
        status = ProgressionStatus.from_quality_gate_decision(
            QualityGateDecision.FAIL, False
        )
        assert status == ProgressionStatus.NOT_READY

    def test_progression_from_blocked(self):
        """Test progression from BLOCKED."""
        status = ProgressionStatus.from_quality_gate_decision(
            QualityGateDecision.BLOCKED, False
        )
        assert status == ProgressionStatus.BLOCKED

    def test_progression_cannot_proceed_overrides(self):
        """Test that can_proceed=False overrides decision."""
        status = ProgressionStatus.from_quality_gate_decision(
            QualityGateDecision.PASS, False  # PASS but can't proceed
        )
        assert status == ProgressionStatus.NOT_READY


# ---------------------------------------------------------------------------
# E4.3.2 - Readiness Level Tests
# ---------------------------------------------------------------------------

class TestReadinessLevel:
    """Test readiness level determination."""

    def test_ready_production(self):
        """Test PRODUCTION level for READY status."""
        level = determine_readiness_level(
            ProgressionStatus.READY, 0, 0, 0
        )
        assert level == ReleaseReadinessLevel.PRODUCTION

    def test_ready_with_warnings_staging(self):
        """Test STAGING level for many warnings."""
        level = determine_readiness_level(
            ProgressionStatus.READY_WITH_WARNINGS, 0, 0, 15
        )
        assert level == ReleaseReadinessLevel.STAGING

    def test_ready_with_warnings_production(self):
        """Test PRODUCTION level for few warnings."""
        level = determine_readiness_level(
            ProgressionStatus.READY_WITH_WARNINGS, 0, 0, 5
        )
        assert level == ReleaseReadinessLevel.PRODUCTION

    def test_not_ready_development(self):
        """Test DEVELOPMENT level for NOT_READY with errors."""
        level = determine_readiness_level(
            ProgressionStatus.NOT_READY, 0, 5, 0
        )
        assert level == ReleaseReadinessLevel.DEVELOPMENT

    def test_not_ready_unreleasable(self):
        """Test UNRELEASABLE for NOT_READY with criticals."""
        level = determine_readiness_level(
            ProgressionStatus.NOT_READY, 1, 0, 0
        )
        assert level == ReleaseReadinessLevel.UNRELEASABLE

    def test_blocked_unreleasable(self):
        """Test UNRELEASABLE for BLOCKED status."""
        level = determine_readiness_level(
            ProgressionStatus.BLOCKED, 0, 0, 0
        )
        assert level == ReleaseReadinessLevel.UNRELEASABLE


# ---------------------------------------------------------------------------
# E4.3.3 - Blocker Determination Tests
# ---------------------------------------------------------------------------

class TestBlockerDetermination:
    """Test blocker determination from quality gate result."""

    def test_blockers_from_critical(self):
        """Test blockers from CRITICAL findings."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.CRITICAL, "a.py", "art-1", "R003", "path_boundary"
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.BLOCKED)
        gate_result = create_sample_gate_result(report)

        blockers, recommendations = determine_blockers(gate_result)

        assert blockers.total_blocking_findings > 0
        assert len(blockers.blocking_artifacts) > 0
        assert "SECURITY" in blockers.blocking_categories or "FILESYSTEM" in blockers.blocking_categories

    def test_blockers_from_error(self):
        """Test blockers from ERROR findings."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)

        blockers, recommendations = determine_blockers(gate_result)

        assert len(blockers.blocking_artifacts) > 0

    def test_no_blockers_pass(self):
        """Test no blockers for clean project."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        blockers, recommendations = determine_blockers(gate_result)

        assert blockers.total_blocking_findings == 0
        assert len(blockers.blocking_artifacts) == 0
        assert "NO_BLOCKERS" in blockers.recommended_action


# ---------------------------------------------------------------------------
# E4.3.4 - Release Readiness Engine Tests
# ---------------------------------------------------------------------------

class TestReleaseReadinessEngine:
    """Test release readiness engine."""

    def test_assess_ready(self, temp_workspace):
        """Test assessment for READY project."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        assert result.progression_status == ProgressionStatus.READY
        assert result.readiness_level == ReleaseReadinessLevel.PRODUCTION
        assert result.can_release is True

    def test_assess_ready_with_warnings(self):
        """Test assessment for READY_WITH_WARNINGS project."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.WARNING, "a.py", "art-1", "R007", "cross_references"
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.PASS_WITH_WARNINGS)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        assert result.progression_status == ProgressionStatus.READY_WITH_WARNINGS
        assert result.can_release is True

    def test_assess_not_ready(self):
        """Test assessment for NOT_READY project."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        assert result.progression_status == ProgressionStatus.NOT_READY
        assert result.can_release is False

    def test_assess_blocked(self):
        """Test assessment for BLOCKED project."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.CRITICAL, "a.py", "art-1", "R001", "file_exists"
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.BLOCKED)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        assert result.progression_status == ProgressionStatus.BLOCKED
        assert result.readiness_level == ReleaseReadinessLevel.UNRELEASABLE
        assert result.can_release is False

    def test_assess_invalid_gate_result(self):
        """Test handling of invalid gate result."""
        engine = ReleaseReadinessEngine()

        with pytest.raises(Exception):  # InvalidGateResultError
            engine.assess(None)


# ---------------------------------------------------------------------------
# E4.3.5 - Artifact Readiness Tests
# ---------------------------------------------------------------------------

class TestArtifactReadiness:
    """Test artifact-level readiness."""

    def test_artifact_readiness_multiple_artifacts(self):
        """Test readiness for multiple artifacts."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"
            ),
            create_sample_finding(
                "f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R007", "cross_references"
            ),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        assert len(result.artifact_readiness) == 2

        # Find art-1 readiness
        art1 = next(a for a in result.artifact_readiness if a.artifact_id == "art-1")
        assert art1.progression_status == ProgressionStatus.NOT_READY
        assert art1.error_findings == 1

        # Find art-2 readiness
        art2 = next(a for a in result.artifact_readiness if a.artifact_id == "art-2")
        assert art2.progression_status == ProgressionStatus.READY_WITH_WARNINGS
        assert art2.warning_findings == 1


# ---------------------------------------------------------------------------
# E4.3.6 - Evidence Preservation Tests
# ---------------------------------------------------------------------------

class TestEvidencePreservation:
    """Test evidence preservation."""

    def test_evidence_chain_complete(self):
        """Test evidence chain is complete."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        # Evidence should have review, gate, and readiness entries
        assert len(result.evidence.evidence_chain) >= 4

    def test_evidence_review_reference(self):
        """Test evidence contains review reference."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        review_ref = next(
            e for e in result.evidence.evidence_chain
            if e.type == "review_reference"
        )
        assert review_ref.content.get("review_id") == "rev-test-001"

    def test_evidence_gate_reference(self):
        """Test evidence contains gate reference."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        gate_ref = next(
            e for e in result.evidence.evidence_chain
            if e.type == "gate_reference"
        )
        assert gate_ref.content.get("gate_id") is not None

    def test_deterministic_hash_computed(self):
        """Test deterministic hash is computed."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        assert result.deterministic_hash != ""
        assert len(result.deterministic_hash) == 64  # SHA-256


# ---------------------------------------------------------------------------
# E4.3.7 - Idempotency Tests
# ---------------------------------------------------------------------------

class TestIdempotency:
    """Test idempotency of release readiness assessment."""

    def test_same_input_same_output(self):
        """Test same input produces same output."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result1 = engine.assess(gate_result)
        result2 = engine.assess(gate_result)

        assert result1.progression_status == result2.progression_status
        assert result1.readiness_level == result2.readiness_level
        assert result1.deterministic_hash == result2.deterministic_hash

    def test_idempotency_with_custom_id(self):
        """Test idempotency with custom readiness ID."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result1 = engine.assess(gate_result, readiness_id="custom-001")
        result2 = engine.assess(gate_result, readiness_id="custom-001")

        assert result1.readiness_id == "custom-001"
        assert result2.readiness_id == "custom-001"
        assert result1.deterministic_hash == result2.deterministic_hash


# ---------------------------------------------------------------------------
# E4.3.8 - Failure Handling Tests
# ---------------------------------------------------------------------------

class TestFailureHandling:
    """Test failure handling."""

    def test_multiple_artifacts_mixed_status(self):
        """Test handling of multiple artifacts with mixed status."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"
            ),
            create_sample_finding(
                "f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R007", "cross_references"
            ),
            create_sample_finding(
                "f-3", ReviewSeverity.ERROR, "c.py", "art-3", "R005", "syntax_python"
            ),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        # Project should be NOT_READY due to errors
        assert result.progression_status == ProgressionStatus.NOT_READY
        assert result.artifacts_not_ready == 2
        assert result.artifacts_ready_with_warnings == 1

    def test_blocking_artifacts_identified(self):
        """Test blocking artifacts are identified."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.CRITICAL, "a.py", "art-1", "R001", "file_exists"
            ),
            create_sample_finding(
                "f-2", ReviewSeverity.ERROR, "b.py", "art-2", "R005", "syntax_python"
            ),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        # Blocking artifacts should be identified
        assert len(result.blockers.blocking_artifacts) > 0


# ---------------------------------------------------------------------------
# E4.3.9 - Frozen Architecture Tests
# ---------------------------------------------------------------------------

class TestFrozenArchitecture:
    """Test frozen architecture compliance."""

    def test_guards_exist(self):
        """Test frozen architecture guards are defined."""
        assert "no_self_healing" in FROZEN_ARCHITECTURE_GUARDS
        assert "no_auto_regeneration" in FROZEN_ARCHITECTURE_GUARDS
        assert "no_file_modification" in FROZEN_ARCHITECTURE_GUARDS
        assert "no_direct_provider_calls" in FROZEN_ARCHITECTURE_GUARDS

    def test_compliance_verification(self):
        """Test compliance verification runs."""
        is_compliant, violations = verify_frozen_architecture_compliance()

        assert is_compliant is True
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# E4.3.10 - End-to-End Tests
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """End-to-end tests with real ReviewReport through pipeline."""

    def test_e2e_success_pipeline(self, temp_workspace):
        """Test complete success pipeline."""
        # Create sample files
        py_file = Path(temp_workspace) / "src" / "main.py"
        py_file.parent.mkdir(parents=True, exist_ok=True)
        py_file.write_text("def main():\n    print('Hello')\n")

        json_file = Path(temp_workspace) / "config.json"
        json_file.write_text('{"name": "test"}')

        # Create file results
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-001",
                target_path="src/main.py",
                absolute_path=str(py_file),
                file_written=True,
                content_hash="hash001",
            ),
            ArtifactFileResult(
                artifact_execution_id="aeu-002",
                target_path="config.json",
                absolute_path=str(json_file),
                file_written=True,
                content_hash="hash002",
            ),
        ]

        # Create review request and execute E4.1
        from runtime.contracts.review import ReviewEngine
        engine = ReviewEngine(temp_workspace)
        request = ReviewRequest(
            review_id="rev-e2e-001",
            mission_id="msn-e2e-001",
            workspace_id="ws-e2e-001",
            plan_id="plan-e2e-001",
            workspace_root=temp_workspace,
            repository_scope="src/",
        )

        # E4.1: Review
        report = engine.review(request, file_results)

        # E4.2: Quality Gate
        gate_engine = QualityGateDecisionEngine()
        gate_result = gate_engine.analyze(report)

        # E4.3: Release Readiness
        readiness_engine = ReleaseReadinessEngine()
        result = readiness_engine.assess(gate_result)

        # Verify final outcome
        assert result.review_id == "rev-e2e-001"
        assert result.gate_id == gate_result.gate_id
        assert result.progression_status in [
            ProgressionStatus.READY,
            ProgressionStatus.READY_WITH_WARNINGS,
        ]
        assert result.can_release is True

    def test_e2e_failure_pipeline(self, temp_workspace):
        """Test complete failure pipeline."""
        # Create broken files - empty file will trigger ERROR
        empty_py = Path(temp_workspace) / "empty.py"
        empty_py.write_text("")  # Empty file triggers file_not_empty check ERROR

        # Create file results
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-001",
                target_path="empty.py",
                absolute_path=str(empty_py),
                file_written=True,
                content_hash="hash001",
            ),
        ]

        # Create review request and execute E4.1
        from runtime.contracts.review import ReviewEngine
        engine = ReviewEngine(temp_workspace)
        request = ReviewRequest(
            review_id="rev-e2e-fail-001",
            mission_id="msn-e2e-fail-001",
            workspace_id="ws-e2e-fail-001",
            plan_id="plan-e2e-fail-001",
            workspace_root=temp_workspace,
            repository_scope=".",
        )

        # E4.1: Review
        report = engine.review(request, file_results)

        # E4.2: Quality Gate
        gate_engine = QualityGateDecisionEngine()
        gate_result = gate_engine.analyze(report)

        # E4.3: Release Readiness
        readiness_engine = ReleaseReadinessEngine()
        result = readiness_engine.assess(gate_result)

        # Verify failure outcome
        assert result.progression_status in [
            ProgressionStatus.NOT_READY,
            ProgressionStatus.BLOCKED,
        ]
        assert result.can_release is False

    def test_e2e_missing_files_pipeline(self, temp_workspace):
        """Test pipeline with missing files."""
        # Don't create any files
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-001",
                target_path="missing.py",
                absolute_path=str(Path(temp_workspace) / "missing.py"),
                file_written=True,  # Claimed to be written
                content_hash="hash001",
            ),
        ]

        # E4.1: Review
        from runtime.contracts.review import ReviewEngine
        engine = ReviewEngine(temp_workspace)
        request = ReviewRequest(
            review_id="rev-e2e-missing-001",
            mission_id="msn-e2e-missing-001",
            workspace_id="ws-e2e-missing-001",
            plan_id="plan-e2e-missing-001",
            workspace_root=temp_workspace,
            repository_scope=".",
        )

        report = engine.review(request, file_results)

        # E4.2: Quality Gate
        gate_engine = QualityGateDecisionEngine()
        gate_result = gate_engine.analyze(report)

        # E4.3: Release Readiness
        readiness_engine = ReleaseReadinessEngine()
        result = readiness_engine.assess(gate_result)

        # Verify BLOCKED outcome
        assert result.progression_status == ProgressionStatus.BLOCKED
        assert result.readiness_level == ReleaseReadinessLevel.UNRELEASABLE
        assert result.can_release is False
        assert len(result.blockers.blocking_artifacts) > 0


# ---------------------------------------------------------------------------
# E4.3.11 - History Integration Tests
# ---------------------------------------------------------------------------

class TestHistoryIntegration:
    """Test history integration."""

    def test_history_entry_from_result(self):
        """Test creating history entry from result."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        entry = ReleaseReadinessHistoryEntry.from_readiness_result(result)

        assert entry["readiness_id"] == result.readiness_id
        assert entry["review_id"] == result.review_id
        assert entry["gate_id"] == result.gate_id
        assert entry["progression_status"] == result.progression_status.value
        assert entry["readiness_level"] == result.readiness_level.value
        assert entry["can_release"] == result.can_release
        assert entry["deterministic_hash"] == result.deterministic_hash


# ---------------------------------------------------------------------------
# E4.3.12 - Recommendations Tests
# ---------------------------------------------------------------------------

class TestRecommendations:
    """Test recommendations generation."""

    def test_recommendations_for_blocked(self):
        """Test recommendations for BLOCKED project."""
        findings = [
            create_sample_finding(
                "f-1", ReviewSeverity.CRITICAL, "a.py", "art-1", "R003", "path_boundary"
            ),
        ]
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        assert len(result.recommendations) > 0
        assert result.blockers.recommended_action != ""

    def test_recommendations_for_clean(self):
        """Test recommendations for clean project."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)

        engine = ReleaseReadinessEngine()
        result = engine.assess(gate_result)

        # Clean projects should have no blocking recommendations
        assert "NO_BLOCKERS" in result.blockers.recommended_action
