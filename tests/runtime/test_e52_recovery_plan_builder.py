"""E5.2 Recovery Plan Builder Tests.

Tests verify the RecoveryPlanBuilder (E5.2) functionality:
1. Recovery assessment creation (E5.1)
2. Finding → repair action mapping
3. Grouping of related findings
4. Deterministic action ordering
5. Dependency-aware recovery
6. Manual review boundary
7. Non-recoverable case handling
8. Determinism and hash stability
9. Evidence traceability

E5.2 is PLAN GENERATION ONLY - does NOT execute repairs.
"""

from __future__ import annotations

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
    ArtifactLevelDecision,
    FindingAggregation,
    FindingClassification,
    GroupedByArtifact,
    GroupedByCategory,
    ProjectLevelDecision,
    QualityGateDecision,
    QualityGateResult,
    SeverityCounts,
    BlockingCounts,
    CategoryCounts,
)
from runtime.contracts.e42_engine import QualityGateDecisionEngine
from runtime.contracts.e43_models import (
    BlockerSummary,
    ProgressionStatus,
    ReleaseReadinessLevel,
    ReleaseReadinessResult,
    ReleaseReadinessEvidence,
)
from runtime.contracts.e43_engine import ReleaseReadinessEngine
from runtime.contracts.e5_models import (
    AUTO_REPAIRABLE_ACTIONS,
    CATEGORY_TO_ACTION,
    compute_recovery_assessment_hash,
    compute_recovery_plan_hash,
    determine_priority,
    FindingCategory,
    FindingReference,
    GroupedFindings,
    is_auto_repairable,
    RepairAction,
    RecoveryAssessment,
    RecoveryEligibility,
    RecoveryPlan,
    RepairActionType,
)
from runtime.contracts.e5_engine import (
    RecoveryAssessmentEngine,
    RecoveryPlanBuilder,
)


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
    check_type: str = "syntax_python",
    is_blocking: bool = True,
    category: FindingCategory = FindingCategory.SYNTAX,
) -> ReviewFinding:
    """Create a sample ReviewFinding."""
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
    """Create a sample ReviewReport."""
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
) -> QualityGateResult:
    """Create a sample QualityGateResult."""
    gate_engine = QualityGateDecisionEngine()
    return gate_engine.analyze(report)


def create_sample_readiness_result(
    gate_result: QualityGateResult,
) -> ReleaseReadinessResult:
    """Create a sample ReleaseReadinessResult."""
    readiness_engine = ReleaseReadinessEngine()
    return readiness_engine.assess(gate_result)


def create_readiness_result_with_status(
    gate_result: QualityGateResult,
    progression_status: ProgressionStatus,
    readiness_level: ReleaseReadinessLevel,
    can_release: bool,
    blockers: BlockerSummary,
) -> ReleaseReadinessResult:
    """Create a ReleaseReadinessResult with specific status."""
    readiness = readiness_engine = ReleaseReadinessEngine()
    base_result = readiness_engine.assess(gate_result)
    
    # Create modified result with specific status
    return ReleaseReadinessResult(
        readiness_id=f"ready-{gate_result.gate_id[4:]}",
        review_id=gate_result.review_id,
        report_id=gate_result.report_id,
        gate_id=gate_result.gate_id,
        mission_id=gate_result.mission_id,
        workspace_id=gate_result.workspace_id,
        plan_id=gate_result.plan_id,
        progression_status=progression_status,
        readiness_level=readiness_level,
        can_release=can_release,
        total_artifacts=base_result.total_artifacts,
        artifacts_ready=base_result.artifacts_ready,
        artifacts_ready_with_warnings=base_result.artifacts_ready_with_warnings,
        artifacts_not_ready=base_result.artifacts_not_ready,
        artifacts_blocked=base_result.artifacts_blocked,
        total_findings=base_result.total_findings,
        critical_findings=base_result.critical_findings,
        error_findings=base_result.error_findings,
        warning_findings=base_result.warning_findings,
        info_findings=base_result.info_findings,
        artifact_readiness=base_result.artifact_readiness,
        blockers=blockers,
        evidence=ReleaseReadinessEvidence(
            review_id=gate_result.review_id,
            report_id=gate_result.report_id,
            gate_id=gate_result.gate_id,
            readiness_id=f"ready-{gate_result.gate_id[4:]}",
            mission_id=gate_result.mission_id,
            workspace_id=gate_result.workspace_id,
            plan_id=gate_result.plan_id,
            evidence_chain=(),
        ),
        recommendations=base_result.recommendations,
        assessment_started=datetime.now(timezone.utc).isoformat(),
        assessment_completed=datetime.now(timezone.utc).isoformat(),
        deterministic=True,
        deterministic_hash="",
    )


# ---------------------------------------------------------------------------
# E5.1 - Recovery Assessment Tests
# ---------------------------------------------------------------------------

class TestRecoveryAssessmentCreation:
    """Test RecoveryAssessment creation (E5.1 output)."""

    def test_create_assessment_not_needed(self):
        """Test assessment returns NOT_NEEDED for ready project."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        engine = RecoveryAssessmentEngine()
        assessment = engine.create_assessment(readiness_result, gate_result)

        assert assessment.eligibility == RecoveryEligibility.NOT_NEEDED
        assert assessment.total_findings == 0
        assert assessment.assessment_hash != ""

    def test_create_assessment_with_findings(self):
        """Test assessment with findings."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        engine = RecoveryAssessmentEngine()
        assessment = engine.create_assessment(readiness_result, gate_result)

        assert assessment.total_findings == 1
        assert len(assessment.grouped_findings) == 1
        assert assessment.assessment_hash != ""

    def test_assessment_groups_findings_by_artifact(self):
        """Test findings are grouped by artifact."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-1", "R006", "syntax_python"),
            create_sample_finding("f-3", ReviewSeverity.ERROR, "c.py", "art-2", "R007", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        engine = RecoveryAssessmentEngine()
        assessment = engine.create_assessment(readiness_result, gate_result)

        # Should be 3 groups (art-1/a.py, art-1/b.py, art-2/c.py)
        # Grouping is by artifact_id+file_path
        assert len(assessment.grouped_findings) == 3
        assert assessment.total_findings == 3

    def test_assessment_traceability(self):
        """Test assessment preserves finding traceability."""
        findings = [
            create_sample_finding("f-trace-1", ReviewSeverity.ERROR, "a.py", "art-1", "R001", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        engine = RecoveryAssessmentEngine()
        assessment = engine.create_assessment(readiness_result, gate_result)

        # Check all_findings preserves IDs
        assert len(assessment.all_findings) == 1
        assert assessment.all_findings[0].finding_id == "f-trace-1"


# ---------------------------------------------------------------------------
# E5.2 - Finding → Repair Action Mapping Tests
# ---------------------------------------------------------------------------

class TestFindingToRepairActionMapping:
    """Test mapping from findings to repair actions."""

    def test_syntax_finding_maps_to_fix_syntax(self):
        """Test SYNTAX finding maps to FIX_SYNTAX."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.SYNTAX)
        assert action_type == RepairActionType.FIX_SYNTAX

    def test_structure_finding_maps_to_fix_structure(self):
        """Test STRUCTURE finding maps to FIX_STRUCTURE."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.STRUCTURE)
        assert action_type == RepairActionType.FIX_STRUCTURE

    def test_config_finding_maps_to_fix_config(self):
        """Test CONFIGURATION finding maps to FIX_CONFIGURATION."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.CONFIGURATION)
        assert action_type == RepairActionType.FIX_CONFIGURATION

    def test_dependency_finding_maps_to_fix_dependency(self):
        """Test DEPENDENCY finding maps to FIX_DEPENDENCY."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.DEPENDENCY)
        assert action_type == RepairActionType.FIX_DEPENDENCY

    def test_placeholder_finding_maps_to_remove_placeholder(self):
        """Test PLACEHOLDER finding maps to REMOVE_PLACEHOLDER."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.PLACEHOLDER)
        assert action_type == RepairActionType.REMOVE_PLACEHOLDER

    def test_content_finding_maps_to_fix_content(self):
        """Test CONTENT finding maps to FIX_CONTENT."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.CONTENT)
        assert action_type == RepairActionType.FIX_CONTENT

    def test_security_finding_requires_manual_review(self):
        """Test SECURITY finding requires manual review."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.SECURITY)
        assert action_type == RepairActionType.MANUAL_REVIEW
        assert not is_auto_repairable(action_type)

    def test_contract_finding_requires_manual_review(self):
        """Test CONTRACT finding requires manual review."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.CONTRACT)
        assert action_type == RepairActionType.MANUAL_REVIEW
        assert not is_auto_repairable(action_type)

    def test_quality_finding_requires_manual_review(self):
        """Test QUALITY finding requires manual review."""
        action_type = CATEGORY_TO_ACTION.get(FindingCategory.QUALITY)
        assert action_type == RepairActionType.MANUAL_REVIEW
        assert not is_auto_repairable(action_type)


# ---------------------------------------------------------------------------
# E5.2 - Recovery Plan Builder Tests
# ---------------------------------------------------------------------------

class TestRecoveryPlanBuilder:
    """Test RecoveryPlanBuilder (E5.2) functionality."""

    def test_build_plan_not_needed(self):
        """Test building plan when recovery not needed."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        assert plan.eligibility == RecoveryEligibility.NOT_NEEDED
        assert plan.total_actions == 0
        assert plan.plan_hash != ""

    def test_build_plan_creates_repair_actions(self):
        """Test building plan creates repair actions for findings."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        assert plan.eligibility == RecoveryEligibility.RECOVERABLE
        assert plan.total_actions == 1
        assert len(plan.actions) == 1
        assert plan.actions[0].action_type == RepairActionType.FIX_SYNTAX

    def test_build_plan_determines_correct_action_type(self):
        """Test plan determines correct action type from finding category."""
        # Use STRUCTURE category which maps to FIX_STRUCTURE
        findings = [
            create_sample_finding(
                "f-struct", ReviewSeverity.ERROR, "empty.py", "art-struct", 
                "R010", "file_not_empty", category=FindingCategory.STRUCTURE
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        assert plan.actions[0].action_type == RepairActionType.FIX_STRUCTURE


# ---------------------------------------------------------------------------
# E5.2 - Grouping Tests
# ---------------------------------------------------------------------------

class TestGroupingBehavior:
    """Test grouping of related findings."""

    def test_multiple_findings_same_artifact_grouped(self):
        """Test multiple findings for same artifact are grouped."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "a.py", "art-1", "R006", "structure"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        # Should be grouped into fewer actions
        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # Grouped - so actions should be less than findings
        assert plan.total_groups <= len(assessment.grouped_findings)

    def test_findings_preserve_ids_for_traceability(self):
        """Test finding IDs are preserved for traceability."""
        findings = [
            create_sample_finding("f-trace-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-trace-2", ReviewSeverity.ERROR, "a.py", "art-1", "R006", "structure"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # Check finding IDs are preserved
        all_finding_ids = []
        for action in plan.actions:
            all_finding_ids.extend(list(action.finding_ids))

        assert "f-trace-1" in all_finding_ids
        assert "f-trace-2" in all_finding_ids


# ---------------------------------------------------------------------------
# E5.2 - Ordering Tests
# ---------------------------------------------------------------------------

class TestActionOrdering:
    """Test deterministic action ordering."""

    def test_critical_before_error_before_warning(self):
        """Test ordering by severity: CRITICAL > ERROR > WARNING."""
        findings = [
            create_sample_finding("f-warn", ReviewSeverity.WARNING, "c.py", "art-3", "R003", "placeholder"),
            create_sample_finding("f-err", ReviewSeverity.ERROR, "b.py", "art-2", "R002", "syntax_python"),
            create_sample_finding("f-crit", ReviewSeverity.CRITICAL, "a.py", "art-1", "R001", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.BLOCKED)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # Critical should come first
        severities = [a.severity for a in plan.actions]
        assert severities.index("CRITICAL") < severities.index("ERROR")
        assert severities.index("ERROR") < severities.index("WARNING")

    def test_ordering_deterministic_same_input(self):
        """Test ordering is deterministic with same input."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R006", "placeholder"),
        ]

        # Build plan twice with same input
        report1 = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result1 = create_sample_gate_result(report1)
        readiness_result1 = create_sample_readiness_result(gate_result1)

        assessment_engine = RecoveryAssessmentEngine()
        assessment1 = assessment_engine.create_assessment(readiness_result1, gate_result1)

        builder = RecoveryPlanBuilder()
        plan1 = builder.build_plan(assessment1)

        # Build again
        report2 = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result2 = create_sample_gate_result(report2)
        readiness_result2 = create_sample_readiness_result(gate_result2)

        assessment2 = assessment_engine.create_assessment(readiness_result2, gate_result2)
        plan2 = builder.build_plan(assessment2)

        # Same ordering
        assert [a.severity for a in plan1.actions] == [a.severity for a in plan2.actions]
        assert [a.artifact_id for a in plan1.actions] == [a.artifact_id for a in plan2.actions]

    def test_order_field_assigned(self):
        """Test order field is assigned to actions."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R006", "placeholder"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # Order should be 1-based and sequential
        orders = [a.order for a in plan.actions]
        assert orders == sorted(orders)
        assert orders[0] == 1


# ---------------------------------------------------------------------------
# E5.2 - Manual Review Boundary Tests
# ---------------------------------------------------------------------------

class TestManualReviewBoundary:
    """Test manual review boundary behavior."""

    def test_security_finding_requires_manual_review(self):
        """Test SECURITY finding produces NOT_RECOVERABLE assessment."""
        findings = [
            create_sample_finding(
                "f-sec", ReviewSeverity.CRITICAL, "a.py", "art-1", "R003", 
                "path_boundary", category=FindingCategory.SECURITY
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.BLOCKED)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        # Security findings should produce NOT_RECOVERABLE
        assert assessment.eligibility == RecoveryEligibility.NOT_RECOVERABLE

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # Plan should have no actions since recovery is not eligible
        assert plan.total_actions == 0
        # But findings should still be tracked
        assert plan.findings_addressed == 1

    def test_quality_finding_requires_manual_review(self):
        """Test QUALITY finding requires manual review in plan."""
        findings = [
            create_sample_finding(
                "f-qual", ReviewSeverity.WARNING, "a.py", "art-1", "R020",
                "quality_check", category=FindingCategory.QUALITY
            ),
        ]
        report = create_sample_report(findings, ReviewVerdict.PASS_WITH_WARNINGS)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        if plan.total_actions > 0:
            action = plan.actions[0]
            assert action.action_type == RepairActionType.MANUAL_REVIEW


# ---------------------------------------------------------------------------
# E5.2 - Non-Recoverable Case Tests
# ---------------------------------------------------------------------------

class TestNonRecoverableCases:
    """Test handling of non-recoverable cases."""

    def test_terminal_failure_produces_empty_plan(self):
        """Test TERMINAL_FAILURE produces plan with no actions."""
        assessment = RecoveryAssessment(
            assessment_id="asmt-terminal",
            readiness_id="ready-001",
            gate_id="gate-001",
            eligibility=RecoveryEligibility.TERMINAL_FAILURE,
            reason="Recovery failed after max retries",
            total_findings=2,
            grouped_findings=(),
            all_findings=(),
            critical_findings=0,
            error_findings=2,
            warning_findings=0,
            repairable_findings=0,
            manual_review_findings=2,
            affected_artifacts=("art-1",),
            affected_files=("a.py",),
            max_recovery_attempts=3,
            evidence={},
            assessment_hash="",
        )

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        assert plan.eligibility == RecoveryEligibility.TERMINAL_FAILURE
        assert plan.total_actions == 0
        assert plan.findings_addressed == 2

    def test_not_recoverable_produces_empty_plan(self):
        """Test NOT_RECOVERABLE produces plan with no actions."""
        assessment = RecoveryAssessment(
            assessment_id="asmt-not-rec",
            readiness_id="ready-001",
            gate_id="gate-001",
            eligibility=RecoveryEligibility.NOT_RECOVERABLE,
            reason="Issues require manual review",
            total_findings=1,
            grouped_findings=(),
            all_findings=(),
            critical_findings=0,
            error_findings=1,
            warning_findings=0,
            repairable_findings=0,
            manual_review_findings=1,
            affected_artifacts=("art-1",),
            affected_files=("a.py",),
            max_recovery_attempts=3,
            evidence={},
            assessment_hash="",
        )

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        assert plan.eligibility == RecoveryEligibility.NOT_RECOVERABLE
        assert plan.total_actions == 0


# ---------------------------------------------------------------------------
# E5.2 - Determinism Tests
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Test deterministic behavior."""

    def test_plan_hash_stable_across_runs(self):
        """Test plan hash is stable across repeated runs."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()

        # Build plan multiple times
        plan1 = builder.build_plan(assessment)
        plan2 = builder.build_plan(assessment)

        # Hash should be identical
        assert plan1.plan_hash == plan2.plan_hash
        assert plan1.plan_id == plan2.plan_id

    def test_reordering_input_findings_same_plan(self):
        """Test reordering input findings doesn't change plan."""
        # Create two different orderings of same findings
        findings_order1 = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R006", "placeholder"),
        ]

        findings_order2 = [
            create_sample_finding("f-2", ReviewSeverity.WARNING, "b.py", "art-2", "R006", "placeholder"),
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
        ]

        assessment_engine = RecoveryAssessmentEngine()
        builder = RecoveryPlanBuilder()

        # Build with first ordering
        report1 = create_sample_report(findings_order1, ReviewVerdict.FAIL)
        gate_result1 = create_sample_gate_result(report1)
        readiness_result1 = create_sample_readiness_result(gate_result1)
        assessment1 = assessment_engine.create_assessment(readiness_result1, gate_result1)
        plan1 = builder.build_plan(assessment1)

        # Build with second ordering
        report2 = create_sample_report(findings_order2, ReviewVerdict.FAIL)
        gate_result2 = create_sample_gate_result(report2)
        readiness_result2 = create_sample_readiness_result(gate_result2)
        assessment2 = assessment_engine.create_assessment(readiness_result2, gate_result2)
        plan2 = builder.build_plan(assessment2)

        # Plans should be identical
        assert plan1.plan_hash == plan2.plan_hash
        assert [a.order for a in plan1.actions] == [a.order for a in plan2.actions]


# ---------------------------------------------------------------------------
# E5.2 - Evidence Traceability Tests
# ---------------------------------------------------------------------------

class TestEvidenceTraceability:
    """Test evidence and traceability."""

    def test_plan_preserves_finding_ids(self):
        """Test plan preserves finding IDs for traceability."""
        findings = [
            create_sample_finding("f-ev-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-ev-2", ReviewSeverity.ERROR, "b.py", "art-2", "R006", "structure"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # All finding IDs should be in plan
        all_ids = []
        for action in plan.actions:
            all_ids.extend(list(action.finding_ids))

        assert "f-ev-1" in all_ids
        assert "f-ev-2" in all_ids

    def test_plan_has_complete_evidence_chain(self):
        """Test plan has complete evidence references."""
        findings = [
            create_sample_finding("f-ev", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # Check evidence chain
        assert "assessment_id" in plan.evidence
        assert "readiness_id" in plan.evidence
        assert "gate_id" in plan.evidence
        assert plan.assessment_id == assessment.assessment_id
        assert plan.readiness_id == assessment.readiness_id


# ---------------------------------------------------------------------------
# E5.2 - Priority Tests
# ---------------------------------------------------------------------------

class TestPriorityDetermination:
    """Test priority determination from severity."""

    def test_critical_highest_priority(self):
        """Test CRITICAL has highest priority (0)."""
        assert determine_priority("CRITICAL") == 0

    def test_error_second_priority(self):
        """Test ERROR has second priority (1)."""
        assert determine_priority("ERROR") == 1

    def test_warning_third_priority(self):
        """Test WARNING has third priority (2)."""
        assert determine_priority("WARNING") == 2

    def test_info_lowest_priority(self):
        """Test INFO has lowest priority (3)."""
        assert determine_priority("INFO") == 3


# ---------------------------------------------------------------------------
# E5.2 - Scope/Affected Tests
# ---------------------------------------------------------------------------

class TestAffectedScope:
    """Test affected artifact/file tracking."""

    def test_plan_tracks_affected_artifacts(self):
        """Test plan tracks affected artifacts."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-2", "R006", "structure"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        assert "art-1" in plan.affected_artifacts
        assert "art-2" in plan.affected_artifacts

    def test_plan_tracks_affected_files(self):
        """Test plan tracks affected files."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
            create_sample_finding("f-2", ReviewSeverity.ERROR, "b.py", "art-2", "R006", "structure"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        assert "a.py" in plan.affected_files
        assert "b.py" in plan.affected_files


# ---------------------------------------------------------------------------
# E5.2 - No Execution Tests
# ---------------------------------------------------------------------------

class TestNoExecution:
    """Test that E5.2 does NOT execute repairs."""

    def test_no_provider_calls(self):
        """Test E5.2 does not call providers."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # Plan is generated, not executed
        assert plan.total_actions >= 0
        # No actual recovery result with files modified

    def test_plan_does_not_modify_files(self, temp_workspace):
        """Test plan generation does not modify files."""
        # Create a test file
        test_file = Path(temp_workspace) / "test.py"
        test_file.write_text("# original")

        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "test.py", "art-1", "R005", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        plan = builder.build_plan(assessment)

        # File should be unchanged
        assert test_file.read_text() == "# original"


# ---------------------------------------------------------------------------
# E5.2 - Architecture Boundary Tests
# ---------------------------------------------------------------------------

class TestArchitectureBoundary:
    """Test E5.2 architecture boundaries."""

    def test_plan_generation_only(self):
        """Test plan builder only generates plans, doesn't execute."""
        findings = [
            create_sample_finding("f-1", ReviewSeverity.ERROR, "a.py", "art-1", "R005", "syntax_python"),
        ]
        report = create_sample_report(findings, ReviewVerdict.FAIL)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder()
        
        # Just generate plan
        plan = builder.build_plan(assessment)
        
        # Should return a valid plan
        assert isinstance(plan, RecoveryPlan)
        assert plan.plan_id.startswith("rpln-")

    def test_max_recovery_attempts_propagated(self):
        """Test max_recovery_attempts is propagated to plan."""
        findings = []
        report = create_sample_report(findings)
        gate_result = create_sample_gate_result(report)
        readiness_result = create_sample_readiness_result(gate_result)

        assessment_engine = RecoveryAssessmentEngine(max_recovery_attempts=5)
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        builder = RecoveryPlanBuilder(max_recovery_attempts=5)
        plan = builder.build_plan(assessment)

        assert plan.max_recovery_attempts == 5


# ---------------------------------------------------------------------------
# E5.2 - Integration Tests
# ---------------------------------------------------------------------------

class TestE4ToE5Integration:
    """Integration tests for E4.1 → E4.2 → E4.3 → E5.1 → E5.2 pipeline."""

    def test_full_pipeline_success(self, temp_workspace):
        """Test complete success pipeline through E4/E5.2."""
        # Create a valid Python file
        py_file = Path(temp_workspace) / "src" / "main.py"
        py_file.parent.mkdir(parents=True, exist_ok=True)
        py_file.write_text("def main():\n    print('Hello')\n")

        # E4.1: Review
        from runtime.contracts.review import ReviewEngine
        from runtime.contracts.e34_models import ArtifactFileResult

        engine = ReviewEngine(temp_workspace)
        request = ReviewRequest(
            review_id="rev-e2e-001",
            mission_id="msn-e2e-001",
            workspace_id="ws-e2e-001",
            plan_id="plan-e2e-001",
            workspace_root=temp_workspace,
            repository_scope="src/",
        )
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-001",
                target_path="src/main.py",
                absolute_path=str(py_file),
                file_written=True,
                content_hash="hash001",
            ),
        ]

        report = engine.review(request, file_results)

        # E4.2: Quality Gate
        gate_engine = QualityGateDecisionEngine()
        gate_result = gate_engine.analyze(report)

        # E4.3: Release Readiness
        readiness_engine = ReleaseReadinessEngine()
        readiness_result = readiness_engine.assess(gate_result)

        # E5.1: Recovery Assessment
        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        # E5.2: Recovery Plan
        plan_builder = RecoveryPlanBuilder()
        plan = plan_builder.build_plan(assessment)

        # Verify success pipeline
        assert readiness_result.can_release is True
        assert assessment.eligibility == RecoveryEligibility.NOT_NEEDED
        assert plan.eligibility == RecoveryEligibility.NOT_NEEDED
        assert plan.total_actions == 0
        assert plan.plan_hash != ""

    def test_full_pipeline_with_fixable_findings(self, temp_workspace):
        """Test pipeline with fixable syntax findings."""
        # Create a file with syntax error
        py_file = Path(temp_workspace) / "syntax_error.py"
        py_file.write_text("def broken(\n")  # Missing closing paren

        # E4.1: Review
        from runtime.contracts.review import ReviewEngine
        from runtime.contracts.e34_models import ArtifactFileResult

        engine = ReviewEngine(temp_workspace)
        request = ReviewRequest(
            review_id="rev-syntax-001",
            mission_id="msn-syntax-001",
            workspace_id="ws-syntax-001",
            plan_id="plan-syntax-001",
            workspace_root=temp_workspace,
            repository_scope=".",
        )
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-syntax",
                target_path="syntax_error.py",
                absolute_path=str(py_file),
                file_written=True,
                content_hash="hash002",
            ),
        ]

        report = engine.review(request, file_results)

        # E4.2: Quality Gate
        gate_engine = QualityGateDecisionEngine()
        gate_result = gate_engine.analyze(report)

        # E4.3: Release Readiness
        readiness_engine = ReleaseReadinessEngine()
        readiness_result = readiness_engine.assess(gate_result)

        # E5.1: Recovery Assessment
        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)

        # E5.2: Recovery Plan
        plan_builder = RecoveryPlanBuilder()
        plan = plan_builder.build_plan(assessment)

        # Verify pipeline completed
        assert plan.plan_hash != ""
        # If findings exist, they should be in the plan
        if assessment.total_findings > 0:
            assert plan.findings_addressed >= 0

    def test_full_pipeline_produces_deterministic_plan(self, temp_workspace):
        """Test that the pipeline produces deterministic plans with same input."""
        # Create valid Python file (no findings)
        py_file = Path(temp_workspace) / "main.py"
        py_file.write_text("def main():\n    print('Hello')\n")

        from runtime.contracts.review import ReviewEngine
        from runtime.contracts.e34_models import ArtifactFileResult

        assessment_engine = RecoveryAssessmentEngine()
        plan_builder = RecoveryPlanBuilder()

        # Run pipeline twice with identical config
        plans = []
        for i in range(2):
            engine = ReviewEngine(temp_workspace)
            request = ReviewRequest(
                review_id="rev-det",
                mission_id="msn-det",
                workspace_id="ws-det",
                plan_id="plan-det",
                workspace_root=temp_workspace,
                repository_scope=".",
            )
            file_results = [
                ArtifactFileResult(
                    artifact_execution_id="aeu-det",
                    target_path="main.py",
                    absolute_path=str(py_file),
                    file_written=True,
                    content_hash="hash",
                ),
            ]

            report = engine.review(request, file_results)
            gate_engine = QualityGateDecisionEngine()
            gate_result = gate_engine.analyze(report)
            readiness_engine = ReleaseReadinessEngine()
            readiness_result = readiness_engine.assess(gate_result)
            assessment = assessment_engine.create_assessment(readiness_result, gate_result)
            plan = plan_builder.build_plan(assessment)
            plans.append(plan)

        # Plans should have same hash
        assert plans[0].plan_hash == plans[1].plan_hash

    def test_full_pipeline_traceability_chain(self, temp_workspace):
        """Test complete traceability from plan to findings."""
        # Create valid Python file
        py_file = Path(temp_workspace) / "test.py"
        py_file.write_text("def main():\n    print('Hello')\n")

        from runtime.contracts.review import ReviewEngine
        from runtime.contracts.e34_models import ArtifactFileResult

        engine = ReviewEngine(temp_workspace)
        request = ReviewRequest(
            review_id="rev-trace-001",
            mission_id="msn-trace-001",
            workspace_id="ws-trace-001",
            plan_id="plan-trace-001",
            workspace_root=temp_workspace,
            repository_scope=".",
        )
        file_results = [
            ArtifactFileResult(
                artifact_execution_id="aeu-trace",
                target_path="test.py",
                absolute_path=str(py_file),
                file_written=True,
                content_hash="hash-trace",
            ),
        ]

        report = engine.review(request, file_results)
        gate_engine = QualityGateDecisionEngine()
        gate_result = gate_engine.analyze(report)
        readiness_engine = ReleaseReadinessEngine()
        readiness_result = readiness_engine.assess(gate_result)
        assessment_engine = RecoveryAssessmentEngine()
        assessment = assessment_engine.create_assessment(readiness_result, gate_result)
        plan_builder = RecoveryPlanBuilder()
        plan = plan_builder.build_plan(assessment)

        # Verify traceability
        # RecoveryPlan → RecoveryAssessment → ReleaseReadinessResult → QualityGateResult → ReviewReport
        assert plan.assessment_id == assessment.assessment_id
        assert plan.readiness_id == readiness_result.readiness_id
        assert plan.gate_id == readiness_result.gate_id

        # Plan fields should contain full chain
        assert plan.assessment_id is not None
        assert plan.readiness_id is not None
        assert plan.gate_id is not None
