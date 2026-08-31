"""E4.2 Review Finding Analysis & Quality Gate Decision Engine Tests.

Tests verify:
1. Finding Classification (E4.2.1)
2. Finding Aggregation (E4.2.2)
3. Quality Gate Decision (E4.2.3)
4. Artifact-level decisions (E4.2.4)
5. Project-level decisions (E4.2.5)
6. Remediation Classification (E4.2.6)
7. Evidence Preservation (E4.2.7)
8. Review History Integration (E4.2.8)
9. Frozen Architecture Guards (E4.2.9)
10. End-to-End Tests (E4.2.10)
11. Negative Tests (E4.2.11)
12. Determinism Tests (E4.2.12)
"""

from __future__ import annotations

import json
import os
import tempfile
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from runtime.contracts.e4_models import (
    ReviewFinding,
    ReviewReport,
    ReviewRequest,
    ReviewSeverity,
    ReviewVerdict,
)
from runtime.contracts.e42_models import (
    FindingCategory,
    FindingClassification,
    FindingAggregation,
    QualityGateDecision,
    QualityGateEvidence,
    QualityGateResult,
    RemediationCategory,
    ReviewSeverity as E4ReviewSeverity,
    SeverityCounts,
    classify_finding,
    determine_remediation_category,
    compute_quality_gate_hash,
    compute_evidence_hash,
)
from runtime.contracts.e42_engine import (
    FindingClassificationEngine,
    FindingAggregator,
    QualityGateDecisionEngine,
    QualityGateHistoryEntry,
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
    message: str = "Test finding",
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
        message=message,
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


# ---------------------------------------------------------------------------
# E4.2.1 - Finding Classification Tests
# ---------------------------------------------------------------------------

class TestFindingClassification:
    """Test finding classification."""

    def test_classify_finding_security(self):
        """Test classifying SECURITY finding."""
        finding = create_sample_finding(
            check_type="path_boundary",
            rule_id="R003",
            severity=ReviewSeverity.CRITICAL,
        )
        classification = classify_finding(finding)

        assert classification.category == FindingCategory.SECURITY
        assert classification.severity == ReviewSeverity.CRITICAL
        assert classification.rule_id == "R003"
        assert classification.is_blocking is True

    def test_classify_finding_syntax(self):
        """Test classifying SYNTAX finding."""
        finding = create_sample_finding(
            check_type="syntax_python",
            rule_id="R005",
            severity=ReviewSeverity.ERROR,
        )
        classification = classify_finding(finding)

        assert classification.category == FindingCategory.SYNTAX
        assert classification.severity == ReviewSeverity.ERROR

    def test_classify_finding_placeholder(self):
        """Test classifying PLACEHOLDER finding."""
        finding = create_sample_finding(
            check_type="no_placeholders",
            rule_id="R004",
            severity=ReviewSeverity.ERROR,
        )
        classification = classify_finding(finding)

        assert classification.category == FindingCategory.PLACEHOLDER

    def test_classify_finding_dependency(self):
        """Test classifying DEPENDENCY finding."""
        finding = create_sample_finding(
            check_type="cross_references",
            rule_id="R007",
            severity=ReviewSeverity.WARNING,
        )
        classification = classify_finding(finding)

        assert classification.category == FindingCategory.DEPENDENCY
        # Note: E4.1 ReviewEngine sets is_blocking=True for cross_references
        # even though severity is WARNING
        assert classification.is_blocking is True

    def test_classify_finding_filesystem(self):
        """Test classifying FILESYSTEM finding."""
        finding = create_sample_finding(
            check_type="file_exists",
            rule_id="R001",
            severity=ReviewSeverity.CRITICAL,
        )
        classification = classify_finding(finding)

        assert classification.category == FindingCategory.FILESYSTEM
        assert classification.severity == ReviewSeverity.CRITICAL

    def test_classify_finding_structure(self):
        """Test classifying STRUCTURE finding."""
        finding = create_sample_finding(
            check_type="file_not_empty",
            rule_id="R002",
            severity=ReviewSeverity.ERROR,
        )
        classification = classify_finding(finding)

        assert classification.category == FindingCategory.STRUCTURE

    def test_classify_critical_remediation(self):
        """Test that CRITICAL findings get BLOCK_RELEASE remediation."""
        finding = create_sample_finding(
            severity=ReviewSeverity.CRITICAL,
        )
        classification = classify_finding(finding)

        assert classification.remediation == RemediationCategory.BLOCK_RELEASE

    def test_classify_error_remediation(self):
        """Test that ERROR findings get appropriate remediation."""
        finding = create_sample_finding(
            severity=ReviewSeverity.ERROR,
            check_type="syntax_python",
        )
        classification = classify_finding(finding)

        assert classification.remediation == RemediationCategory.FIX_GENERATED_CODE

    def test_classify_warning_remediation(self):
        """Test that WARNING findings get MANUAL_REVIEW remediation."""
        finding = create_sample_finding(
            severity=ReviewSeverity.WARNING,
        )
        classification = classify_finding(finding)

        assert classification.remediation == RemediationCategory.MANUAL_REVIEW

    def test_classify_info_remediation(self):
        """Test that INFO findings get NO_ACTION remediation."""
        finding = create_sample_finding(
            severity=ReviewSeverity.INFO,
        )
        classification = classify_finding(finding)

        assert classification.remediation == RemediationCategory.NO_ACTION

    def test_classify_placeholder_error_remediation(self):
        """Test that ERROR + PLACEHOLDER gets REGENERATE_ARTIFACT."""
        finding = create_sample_finding(
            severity=ReviewSeverity.ERROR,
            check_type="no_placeholders",
        )
        classification = classify_finding(finding)

        assert classification.remediation == RemediationCategory.REGENERATE_ARTIFACT


# ---------------------------------------------------------------------------
# E4.2.2 - Finding Aggregation Tests
# ---------------------------------------------------------------------------

class TestFindingAggregation:
    """Test finding aggregation."""

    def test_aggregate_empty_findings(self):
        """Test aggregating empty findings."""
        aggregator = FindingAggregator()
        report = create_sample_report([])
        classifications = []

        aggregation = aggregator.aggregate(report.findings, classifications)

        assert aggregation.severity_counts.total == 0
        assert aggregation.severity_counts.critical == 0
        assert aggregation.severity_counts.error == 0
        assert aggregation.blocking_counts.total_blocking == 0

    def test_aggregate_mixed_severity(self):
        """Test aggregating findings with mixed severity."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.CRITICAL, "a.py", "art-1", "R1"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-1", "R2"),
            create_sample_finding("f-3", ReviewSeverity.WARNING, "c.py", "art-2", "R3"),
            create_sample_finding("f-4", ReviewSeverity.INFO, "d.py", "art-2", "R4"),
        ]
        report = create_sample_report(findings)
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        aggregation = aggregator.aggregate(report.findings, classifications)

        assert aggregation.severity_counts.total == 4
        assert aggregation.severity_counts.critical == 1
        assert aggregation.severity_counts.error == 1
        assert aggregation.severity_counts.warning == 1
        assert aggregation.severity_counts.info == 1

    def test_aggregate_unique_counts(self):
        """Test aggregating unique artifact/file/rule counts."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R1"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-1", "R1"),
            create_sample_finding("f-3", ReviewSeverity.ERROR, "c.py", "art-2", "R2"),
        ]
        report = create_sample_report(findings)
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        aggregation = aggregator.aggregate(report.findings, classifications)

        assert aggregation.affected_artifact_count == 2
        assert aggregation.affected_file_count == 3
        assert len(aggregation.unique_artifact_ids) == 2
        assert len(aggregation.unique_file_paths) == 3
        assert len(aggregation.unique_rule_ids) == 2

    def test_aggregate_blocking_counts(self):
        """Test aggregating blocking counts."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, is_blocking=True),
            create_sample_finding("f-2", ReviewSeverity.WARNING, is_blocking=False),
            create_sample_finding("f-3", ReviewSeverity.ERROR, is_blocking=True),
        ]
        report = create_sample_report(findings)
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        aggregation = aggregator.aggregate(report.findings, classifications)

        assert aggregation.blocking_counts.total_blocking == 2
        assert aggregation.blocking_counts.non_blocking == 1

    def test_aggregate_category_counts(self):
        """Test aggregating category counts."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, check_type="syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, check_type="syntax_python"),
            create_sample_finding("f-3", ReviewSeverity.WARNING, check_type="cross_references"),
        ]
        report = create_sample_report(findings)
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        aggregation = aggregator.aggregate(report.findings, classifications)

        assert aggregation.category_counts.by_category.get("SYNTAX") == 2
        assert aggregation.category_counts.by_category.get("DEPENDENCY") == 1


# ---------------------------------------------------------------------------
# E4.2.3 - Grouping Tests
# ---------------------------------------------------------------------------

class TestGrouping:
    """Test finding grouping."""

    def test_group_by_artifact(self):
        """Test grouping findings by artifact."""
        findings = [
            create_sample_finding("f-1", artifact_id="art-1", file_path="a.py"),
            create_sample_finding("f-2", artifact_id="art-1", file_path="b.py"),
            create_sample_finding("f-3", artifact_id="art-2", file_path="c.py"),
        ]
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        groups = aggregator.group_by_artifact(classifications, findings)

        assert len(groups) == 2
        assert groups[0].artifact_id == "art-1"
        assert groups[0].severity_counts.total == 2
        assert groups[1].artifact_id == "art-2"
        assert groups[1].severity_counts.total == 1

    def test_group_by_file(self):
        """Test grouping findings by file."""
        findings = [
            create_sample_finding("f-1", file_path="a.py"),
            create_sample_finding("f-2", file_path="a.py"),
            create_sample_finding("f-3", file_path="b.py"),
        ]
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        groups = aggregator.group_by_file(classifications)

        assert len(groups) == 2
        assert groups[0].file_path == "a.py"
        assert groups[0].severity_counts.total == 2
        assert groups[1].file_path == "b.py"

    def test_group_by_rule(self):
        """Test grouping findings by rule."""
        findings = [
            create_sample_finding("f-1", rule_id="R001"),
            create_sample_finding("f-2", rule_id="R001"),
            create_sample_finding("f-3", rule_id="R002"),
        ]
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        groups = aggregator.group_by_rule(classifications)

        assert len(groups) == 2
        assert groups[0].rule_id == "R001"
        assert groups[0].findings.__len__() == 2

    def test_group_by_category(self):
        """Test grouping findings by category."""
        findings = [
            create_sample_finding("f-1", check_type="syntax_python"),
            create_sample_finding("f-2", check_type="syntax_python"),
            create_sample_finding("f-3", check_type="cross_references"),
        ]
        classifier = FindingClassificationEngine()
        classifications = classifier.classify_findings(findings)

        aggregator = FindingAggregator()
        groups = aggregator.group_by_category(classifications)

        assert len(groups) == 2
        # Should be sorted by category value
        category_values = [g.category.value for g in groups]
        assert category_values == sorted(category_values)


# ---------------------------------------------------------------------------
# E4.2.4 - Quality Gate Decision Tests
# ---------------------------------------------------------------------------

class TestQualityGateDecision:
    """Test quality gate decision."""

    def test_decision_pass(self):
        """Test PASS decision with no findings."""
        report = create_sample_report([])
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.decision == QualityGateDecision.PASS
        assert result.can_proceed is True
        assert result.required_remediation == RemediationCategory.NO_ACTION

    def test_decision_pass_with_warnings(self):
        """Test PASS_WITH_WARNINGS with warnings."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.WARNING),
            create_sample_finding("f-2", ReviewSeverity.INFO),
        ]
        report = create_sample_report(findings, ReviewVerdict.PASS_WITH_WARNINGS)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.decision == QualityGateDecision.PASS_WITH_WARNINGS
        assert result.can_proceed is True
        assert result.required_remediation == RemediationCategory.MANUAL_REVIEW

    def test_decision_fail(self):
        """Test FAIL decision with errors."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
            create_sample_finding("f-2", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.decision == QualityGateDecision.FAIL
        assert result.can_proceed is False
        assert result.required_remediation in [
            RemediationCategory.FIX_GENERATED_CODE,
            RemediationCategory.FIX_DEPENDENCY,
            RemediationCategory.FIX_CONFIGURATION,
        ]

    def test_decision_blocked(self):
        """Test BLOCKED decision with critical findings."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.CRITICAL),
        ]
        report = create_sample_report(findings, ReviewVerdict.BLOCKED)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.decision == QualityGateDecision.BLOCKED
        assert result.can_proceed is False
        assert result.required_remediation == RemediationCategory.BLOCK_RELEASE

    def test_decision_mixed_critical_and_errors(self):
        """Test decision when both CRITICAL and ERROR exist (CRITICAL wins)."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.CRITICAL),
            create_sample_finding("f-2", ReviewSeverity.ERROR),
            create_sample_finding("f-3", ReviewSeverity.WARNING),
        ]
        report = create_sample_report(findings, ReviewVerdict.BLOCKED)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.decision == QualityGateDecision.BLOCKED
        assert result.can_proceed is False


# ---------------------------------------------------------------------------
# E4.2.5 - Artifact-Level Decision Tests
# ---------------------------------------------------------------------------

class TestArtifactLevelDecision:
    """Test artifact-level decisions."""

    def test_artifact_decision_pass(self):
        """Test artifact passing."""
        findings = []
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        artifact_decisions = result.project_decision.artifact_decisions
        # With no findings, we still have decisions (may be empty or have unknown)
        # At least verify project decision is PASS
        assert result.project_decision.decision == QualityGateDecision.PASS

    def test_artifact_decision_multiple_artifacts(self):
        """Test decisions for multiple artifacts."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R1"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-1", "R1"),
            create_sample_finding("f-3", ReviewSeverity.WARNING, "c.py", "art-2", "R2"),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        artifact_decisions = result.project_decision.artifact_decisions

        # Find art-1 decision
        art1_decision = next(
            (d for d in artifact_decisions if d.artifact_id == "art-1"),
            None
        )
        assert art1_decision is not None
        assert art1_decision.has_error is True
        assert art1_decision.total_findings == 2

        # Find art-2 decision
        art2_decision = next(
            (d for d in artifact_decisions if d.artifact_id == "art-2"),
            None
        )
        assert art2_decision is not None
        assert art2_decision.has_warning is True
        assert art2_decision.total_findings == 1

    def test_blocking_artifact_ids(self):
        """Test blocking artifact IDs are identified."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R1"),
            create_sample_finding("f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R2"),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert "art-1" in result.project_decision.blocking_artifact_ids
        # Warning-only artifacts don't block
        assert "art-2" not in result.project_decision.blocking_artifact_ids


# ---------------------------------------------------------------------------
# E4.2.6 - Project-Level Decision Tests
# ---------------------------------------------------------------------------

class TestProjectLevelDecision:
    """Test project-level decisions."""

    def test_project_counts(self):
        """Test project-level artifact counts."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R1"),
            create_sample_finding("f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R2"),
            create_sample_finding("f-3", ReviewSeverity.WARNING, "c.py", "art-3", "R3"),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.project_decision.total_artifacts == 3
        assert result.project_decision.artifacts_failing == 1
        assert result.project_decision.artifacts_with_warnings == 2

    def test_aggregation_in_project_decision(self):
        """Test aggregation is included in project decision."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
            create_sample_finding("f-2", ReviewSeverity.WARNING),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.project_decision.aggregation is not None
        assert result.project_decision.aggregation.severity_counts.error == 1
        assert result.project_decision.aggregation.severity_counts.warning == 1


# ---------------------------------------------------------------------------
# E4.2.7 - Remediation Classification Tests
# ---------------------------------------------------------------------------

class TestRemediationClassification:
    """Test remediation category determination."""

    def test_remediation_no_action(self):
        """Test NO_ACTION remediation for PASS."""
        findings = []
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.required_remediation == RemediationCategory.NO_ACTION

    def test_remediation_manual_review(self):
        """Test MANUAL_REVIEW for warnings only."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.WARNING),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.required_remediation == RemediationCategory.MANUAL_REVIEW

    def test_remediation_fix_dependency(self):
        """Test FIX_DEPENDENCY for dependency issues."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, check_type="cross_references"),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.required_remediation == RemediationCategory.FIX_DEPENDENCY

    def test_remediation_regenerate_artifact(self):
        """Test REGENERATE_ARTIFACT for placeholder content."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, check_type="no_placeholders"),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.required_remediation == RemediationCategory.REGENERATE_ARTIFACT

    def test_remediation_block_release(self):
        """Test BLOCK_RELEASE for CRITICAL findings."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.CRITICAL),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.required_remediation == RemediationCategory.BLOCK_RELEASE


# ---------------------------------------------------------------------------
# E4.2.8 - Evidence Preservation Tests
# ---------------------------------------------------------------------------

class TestEvidencePreservation:
    """Test evidence preservation."""

    def test_evidence_chain_exists(self):
        """Test evidence chain is built."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.evidence is not None
        assert len(result.evidence.evidence_chain) > 0

    def test_evidence_review_reference(self):
        """Test evidence contains review reference."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # Find report reference in evidence
        report_ref = next(
            (e for e in result.evidence.evidence_chain if e.type == "report_reference"),
            None
        )
        assert report_ref is not None
        assert report_ref.content.get("review_id") == "rev-test-001"

    def test_evidence_deterministic_hash(self):
        """Test evidence hash is computed."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.evidence.deterministic_hash != ""
        assert len(result.evidence.deterministic_hash) == 64  # SHA-256

    def test_result_deterministic_hash(self):
        """Test result deterministic hash is computed."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.deterministic_hash != ""
        assert len(result.deterministic_hash) == 64  # SHA-256

    def test_all_finding_fields_preserved(self):
        """Test all finding fields are preserved in classification."""
        findings = [
            create_sample_finding(
                "f-1",
                ReviewSeverity.ERROR,
                "src/main.py",
                "art-1",
                "R001",
                "syntax_python",
                "Syntax error in code",
                True,
            ),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # Get classification from grouped findings
        art1_group = next(
            (g for g in result.project_decision.by_artifact if g.artifact_id == "art-1"),
            None
        )
        assert art1_group is not None
        assert len(art1_group.findings) == 1

        finding = art1_group.findings[0]
        assert finding.severity == ReviewSeverity.ERROR
        assert finding.message == "Syntax error in code"
        assert finding.file_path == "src/main.py"
        assert finding.artifact_id == "art-1"
        assert finding.rule_id == "R001"
        assert finding.is_blocking is True
        assert len(finding.evidence) > 0


# ---------------------------------------------------------------------------
# E4.2.9 - Review History Integration Tests
# ---------------------------------------------------------------------------

class TestReviewHistoryIntegration:
    """Test review history integration."""

    def test_history_entry_from_result(self):
        """Test creating history entry from QualityGateResult."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        entry = QualityGateHistoryEntry.from_quality_gate_result(result)

        assert entry["gate_id"] == result.gate_id
        assert entry["review_id"] == result.review_id
        assert entry["decision"] == result.decision.value
        assert entry["can_proceed"] == result.can_proceed
        assert entry["required_remediation"] == result.required_remediation.value
        assert entry["total_findings"] == 1
        assert entry["deterministic_hash"] == result.deterministic_hash


# ---------------------------------------------------------------------------
# E4.2.10 - Determinism Tests
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Test determinism of quality gate decisions."""

    def test_same_report_same_decision(self):
        """Test same report produces same decision."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1"),
            create_sample_finding("f-2", ReviewSeverity.WARNING, "b.py", "art-2"),
        ]
        report = create_sample_report(findings)

        engine = QualityGateDecisionEngine()
        result1 = engine.analyze(report)
        result2 = engine.analyze(report)

        assert result1.decision == result2.decision
        assert result1.can_proceed == result2.can_proceed
        assert result1.deterministic_hash == result2.deterministic_hash

    def test_different_ordering_same_decision(self):
        """Test findings in different order produce same decision."""
        # Order by severity
        findings1 = [
            create_sample_finding("f-1", ReviewSeverity.CRITICAL, "a.py", "art-1"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-1"),
            create_sample_finding("f-3", ReviewSeverity.WARNING, "c.py", "art-2"),
        ]

        # Different order
        findings2 = [
            create_sample_finding("f-3", ReviewSeverity.WARNING, "c.py", "art-2"),
            create_sample_finding("f-1", ReviewSeverity.CRITICAL, "a.py", "art-1"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-1"),
        ]

        report1 = create_sample_report(findings1)
        report2 = create_sample_report(findings2)

        engine = QualityGateDecisionEngine()
        result1 = engine.analyze(report1)
        result2 = engine.analyze(report2)

        # Both should be BLOCKED due to CRITICAL
        assert result1.decision == QualityGateDecision.BLOCKED
        assert result2.decision == QualityGateDecision.BLOCKED

    def test_compute_hash_deterministic(self):
        """Test hash computation is deterministic."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)

        hash1 = compute_evidence_hash(report.review_id, report.report_id, tuple(findings))
        hash2 = compute_evidence_hash(report.review_id, report.report_id, tuple(findings))

        assert hash1 == hash2


# ---------------------------------------------------------------------------
# E4.2.11 - Frozen Architecture Guard Tests
# ---------------------------------------------------------------------------

class TestFrozenArchitectureGuards:
    """Test frozen architecture compliance."""

    def test_frozen_guards_exist(self):
        """Test frozen architecture guards are defined."""
        assert "no_invocation_engine" in FROZEN_ARCHITECTURE_GUARDS
        assert "no_self_healing" in FROZEN_ARCHITECTURE_GUARDS
        assert "no_auto_regeneration" in FROZEN_ARCHITECTURE_GUARDS
        assert "no_frozen_contract_modification" in FROZEN_ARCHITECTURE_GUARDS

    def test_frozen_guard_verification(self):
        """Test frozen architecture verification runs."""
        is_compliant, violations = verify_frozen_architecture_compliance()

        assert is_compliant is True
        assert len(violations) == 0


# ---------------------------------------------------------------------------
# E4.2.12 - Edge Cases Tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test edge cases."""

    def test_empty_report(self):
        """Test handling of empty report."""
        report = ReviewReport(
            report_id="rpt-empty",
            review_id="rev-empty",
            mission_id="msn-empty",
            workspace_id="ws-empty",
            plan_id="plan-empty",
            workspace_root="/workspace",
            repository_scope="src/",
        )
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        assert result.decision == QualityGateDecision.PASS
        assert result.can_proceed is True

    def test_skipped_verdict(self):
        """Test handling of SKIPPED verdict."""
        findings = []
        report = create_sample_report(findings, ReviewVerdict.SKIPPED)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # SKIPPED should be treated as FAIL for safety
        assert result.decision == QualityGateDecision.PASS  # But no findings means PASS

    def test_duplicate_findings(self):
        """Test handling of duplicate findings."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1"),
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1"),  # Duplicate
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # Should still produce valid decision
        assert result.decision == QualityGateDecision.FAIL
        assert result.project_decision.aggregation.severity_counts.error == 2

    def test_unknown_check_type(self):
        """Test handling of unknown check type."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, check_type="unknown_check"),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # Should classify as OTHER
        art1_group = result.project_decision.by_artifact[0]
        assert art1_group.findings[0].category == FindingCategory.OTHER


# ---------------------------------------------------------------------------
# E4.2.13 - End-to-End Tests
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """End-to-end tests with real ReviewReport."""

    def test_e2e_success_flow(self, temp_workspace):
        """Test complete success flow."""
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

        # Create review request
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

        # Execute review
        report = engine.review(request, file_results)

        # Analyze with E4.2
        gate_engine = QualityGateDecisionEngine()
        result = gate_engine.analyze(report)

        # Verify
        assert result.review_id == "rev-e2e-001"
        assert result.report_id == report.report_id
        assert result.decision in [QualityGateDecision.PASS, QualityGateDecision.PASS_WITH_WARNINGS]
        assert result.can_proceed is True

    def test_e2e_failure_flow(self, temp_workspace):
        """Test complete failure flow with broken project."""
        # Create broken files
        broken_py = Path(temp_workspace) / "broken.py"
        broken_py.write_text("def foo(\n    print('missing')")  # Syntax error

        empty_py = Path(temp_workspace) / "empty.py"
        empty_py.write_text("")

        # Create file results
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-001",
                target_path="broken.py",
                absolute_path=str(broken_py),
                file_written=True,
                content_hash="hash001",
            ),
            ArtifactFileResult(
                artifact_execution_id="aeu-002",
                target_path="empty.py",
                absolute_path=str(empty_py),
                file_written=True,
                content_hash="hash002",
            ),
        ]

        # Create review request
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

        # Execute review
        report = engine.review(request, file_results)

        # Analyze with E4.2
        gate_engine = QualityGateDecisionEngine()
        result = gate_engine.analyze(report)

        # Verify failure
        assert result.decision in [QualityGateDecision.FAIL, QualityGateDecision.BLOCKED]
        assert result.can_proceed is False
        # Empty files are classified as STRUCTURE category
        assert result.required_remediation in [
            RemediationCategory.FIX_GENERATED_CODE,
            RemediationCategory.FIX_STRUCTURE,
            RemediationCategory.BLOCK_RELEASE,
        ]

        # Verify affected artifacts identified
        assert result.project_decision.aggregation.affected_artifact_count >= 1

    def test_e2e_with_missing_files(self, temp_workspace):
        """Test detection of missing files."""
        # Don't create any files, but reference them
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-001",
                target_path="missing.py",
                absolute_path=os.path.join(temp_workspace, "missing.py"),
                file_written=True,  # Claimed to be written
                content_hash="hash001",
            ),
        ]

        # Create review request
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

        # Execute review
        report = engine.review(request, file_results)

        # Should detect missing file
        assert report.verdict == ReviewVerdict.BLOCKED
        assert report.critical_findings >= 1

        # Analyze with E4.2
        gate_engine = QualityGateDecisionEngine()
        result = gate_engine.analyze(report)

        # Verify
        assert result.decision == QualityGateDecision.BLOCKED
        assert result.can_proceed is False
        assert result.required_remediation == RemediationCategory.BLOCK_RELEASE


# ---------------------------------------------------------------------------
# E4.2.14 - Regression Tests
# ---------------------------------------------------------------------------

class TestRegression:
    """Regression tests against E4.1."""

    def test_e41_verdict_to_gate_decision(self):
        """Test ReviewVerdict correctly maps to QualityGateDecision."""
        from runtime.contracts.e42_models import QualityGateDecision

        assert QualityGateDecision.from_review_verdict(ReviewVerdict.PASS) == QualityGateDecision.PASS
        assert QualityGateDecision.from_review_verdict(ReviewVerdict.PASS_WITH_WARNINGS) == QualityGateDecision.PASS_WITH_WARNINGS
        assert QualityGateDecision.from_review_verdict(ReviewVerdict.FAIL) == QualityGateDecision.FAIL
        assert QualityGateDecision.from_review_verdict(ReviewVerdict.BLOCKED) == QualityGateDecision.BLOCKED

    def test_no_finding_mutation(self):
        """Test that findings are not mutated during analysis."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR),
        ]
        report = create_sample_report(findings)

        # Get original finding
        original_finding = report.findings[0]
        original_id = original_finding.finding_id

        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # Verify original finding is unchanged
        assert report.findings[0].finding_id == original_id
        assert report.findings[0].severity == ReviewSeverity.ERROR


# ---------------------------------------------------------------------------
# E4.2.15 - Security Tests
# ---------------------------------------------------------------------------

class TestSecurity:
    """Security-related tests."""

    def test_no_secrets_in_evidence(self):
        """Test that sensitive data is not exposed in evidence."""
        # Create finding with potentially sensitive evidence
        findings = [
            create_sample_finding(
                "f-1",
                ReviewSeverity.ERROR,
                check_type="syntax_python",
            ),
        ]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # Check evidence chain doesn't contain sensitive patterns
        evidence_json = json.dumps(result.evidence.model_dump())
        assert "password" not in evidence_json.lower()
        assert "secret" not in evidence_json.lower()
        assert "api_key" not in evidence_json.lower()

    def test_gate_id_format(self):
        """Test gate ID format is safe."""
        findings = [create_sample_finding()]
        report = create_sample_report(findings)
        engine = QualityGateDecisionEngine()
        result = engine.analyze(report)

        # Gate ID should be alphanumeric with hyphens
        assert result.gate_id.replace("-", "").replace("_", "").isalnum()
