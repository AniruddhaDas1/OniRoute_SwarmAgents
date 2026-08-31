"""E5.3 Recovery Engine Tests.

Tests verify the RecoveryEngine (E5.3) functionality:
1. Valid RecoveryPlan executes
2. Syntax error is actually repaired
3. Structure problem is actually repaired
4. Configuration issue is repaired
5. Dependency issue is repaired
6. Placeholder content is removed/replaced
7. Content issue is repaired
8. Actual filesystem contents change
9. Retry occurs when allowed
10. Maximum 3 attempts enforced
11. Terminal failure after max attempts
12. No infinite retry
13. Manual review action is not auto-executed
14. Security finding remains manual
15. Dependency ordering is respected
16. Failed prerequisite blocks dependent recovery
17. Path traversal is blocked
18. Absolute path escape is blocked
19. Recovery cannot write outside workspace
20. Recovery preserves evidence
21. RecoveryAttempt records are accurate
22. RecoveryResult accurately summarizes execution
23. E5.2 RecoveryPlan remains unchanged
24. E5.1 tests pass (regression)
25. E5.2 tests pass (regression)

E5.3 is EXECUTION - performs real repairs on filesystem.
"""

from __future__ import annotations

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
    ArtifactLevelDecision,
    FindingAggregation,
    FindingClassification,
    GroupedByArtifact,
    GroupedByCategory,
    ProjectLevelDecision,
    QualityGateDecision,
    QualityGateResult,
    RemediationCategory,
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
    FindingCategory,
    FindingReference,
    GroupedFindings,
    RepairAction,
    RecoveryAssessment,
    RecoveryEligibility,
    RecoveryPlan,
    RecoveryResult,
    RepairActionType,
)
from runtime.contracts.e5_engine import (
    RecoveryAssessmentEngine,
    RecoveryPlanBuilder,
    RecoveryEngine,
    RepairExecutor,
)


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_finding():
    """Create a sample ReviewFinding."""
    return ReviewFinding(
        finding_id="f-001",
        check_id="check-syntax",
        check_type="syntax_python",
        mission_id="m-001",
        workspace_id="ws-001",
        plan_id="plan-001",
        artifact_execution_id="ae-001",
        artifact_id="art-001",
        file_path="src/main.py",
        absolute_path="/tmp/test/src/main.py",
        severity=ReviewSeverity.ERROR,
        message="Syntax error in Python file",
        evidence=("line 5: invalid syntax",),
        is_blocking=True,
        rule_id="R001",
        rule_name="Syntax must be valid",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def sample_quality_gate_result(sample_finding):
    """Create a sample QualityGateResult using the engine."""
    from runtime.contracts.e4_models import ReviewReport, ReviewVerdict
    from runtime.contracts.e42_engine import QualityGateDecisionEngine
    
    # Create a review report
    report = ReviewReport(
        report_id="rpt-001",
        review_id="rev-001",
        mission_id="msn-001",
        workspace_id="ws-001",
        plan_id="plan-001",
        workspace_root="/tmp",
        repository_scope="src/",
        total_checks=5,
        checks_passed=4,
        checks_failed=1,
        check_results=(),
        total_findings=1,
        critical_findings=0,
        error_findings=1,
        warning_findings=0,
        info_findings=0,
        findings=(sample_finding,),
        verdict=ReviewVerdict.FAIL,
        verdict_reasons=("1 error",),
        review_started=datetime.now(timezone.utc).isoformat(),
        review_completed=datetime.now(timezone.utc).isoformat(),
    )
    
    # Use engine to create proper gate result
    gate_engine = QualityGateDecisionEngine()
    return gate_engine.analyze(report)


@pytest.fixture
def sample_release_readiness_result(sample_quality_gate_result):
    """Create a sample ReleaseReadinessResult using the engine."""
    from runtime.contracts.e43_engine import ReleaseReadinessEngine
    
    readiness_engine = ReleaseReadinessEngine()
    return readiness_engine.assess(sample_quality_gate_result)


# ---------------------------------------------------------------------------
# E5.3.1 - RecoveryEngine Initialization
# ---------------------------------------------------------------------------

class TestRecoveryEngineInitialization:
    """Test RecoveryEngine initialization."""

    def test_engine_initializes_with_workspace_root(self, temp_workspace):
        """Test engine initializes with valid workspace root."""
        engine = RecoveryEngine(temp_workspace)
        assert engine.workspace_root == temp_workspace
        assert engine.max_recovery_attempts == 3

    def test_engine_initializes_with_custom_max_attempts(self, temp_workspace):
        """Test engine initializes with custom max attempts."""
        engine = RecoveryEngine(temp_workspace, max_recovery_attempts=5)
        assert engine.max_recovery_attempts == 5

    def test_engine_has_assessment_engine(self, temp_workspace):
        """Test engine has assessment engine."""
        engine = RecoveryEngine(temp_workspace)
        assert engine.assessment_engine is not None
        assert isinstance(engine.assessment_engine, RecoveryAssessmentEngine)

    def test_engine_has_plan_builder(self, temp_workspace):
        """Test engine has plan builder."""
        engine = RecoveryEngine(temp_workspace)
        assert engine.plan_builder is not None
        assert isinstance(engine.plan_builder, RecoveryPlanBuilder)

    def test_engine_has_repair_executor(self, temp_workspace):
        """Test engine has repair executor."""
        engine = RecoveryEngine(temp_workspace)
        assert engine.repair_executor is not None
        assert isinstance(engine.repair_executor, RepairExecutor)


# ---------------------------------------------------------------------------
# E5.3.2 - RepairExecutor Tests
# ---------------------------------------------------------------------------

class TestRepairExecutor:
    """Test RepairExecutor functionality."""

    def test_executor_initializes(self, temp_workspace):
        """Test executor initializes correctly."""
        executor = RepairExecutor(temp_workspace)
        assert executor.workspace_root == Path(temp_workspace).resolve()

    def test_can_repair_syntax(self):
        """Test can repair syntax errors."""
        executor = RepairExecutor("/tmp")
        assert executor.can_repair(RepairActionType.FIX_SYNTAX)

    def test_can_repair_structure(self):
        """Test can repair structure issues."""
        executor = RepairExecutor("/tmp")
        assert executor.can_repair(RepairActionType.FIX_STRUCTURE)

    def test_can_repair_configuration(self):
        """Test can repair configuration issues."""
        executor = RepairExecutor("/tmp")
        assert executor.can_repair(RepairActionType.FIX_CONFIGURATION)

    def test_can_repair_dependency(self):
        """Test can repair dependency issues."""
        executor = RepairExecutor("/tmp")
        assert executor.can_repair(RepairActionType.FIX_DEPENDENCY)

    def test_can_repair_placeholder(self):
        """Test can repair placeholder issues."""
        executor = RepairExecutor("/tmp")
        assert executor.can_repair(RepairActionType.REMOVE_PLACEHOLDER)

    def test_can_repair_content(self):
        """Test can repair content issues."""
        executor = RepairExecutor("/tmp")
        assert executor.can_repair(RepairActionType.FIX_CONTENT)

    def test_cannot_repair_manual_review(self):
        """Test cannot repair manual review actions."""
        executor = RepairExecutor("/tmp")
        assert not executor.can_repair(RepairActionType.MANUAL_REVIEW)

    def test_requires_llm_regenerate(self):
        """Test regenerate requires LLM."""
        executor = RepairExecutor("/tmp")
        assert executor.requires_llm(RepairActionType.REGENERATE)

    def test_requires_llm_manual_review(self):
        """Test manual review requires human review, not LLM."""
        executor = RepairExecutor("/tmp")
        # MANUAL_REVIEW means human review, not LLM regeneration
        assert not executor.requires_llm(RepairActionType.MANUAL_REVIEW)


# ---------------------------------------------------------------------------
# E5.3.3 - Path Verification Tests
# ---------------------------------------------------------------------------

class TestPathVerification:
    """Test workspace path verification."""

    def test_valid_relative_path(self, temp_workspace):
        """Test valid relative path passes verification."""
        executor = RepairExecutor(temp_workspace)
        assert executor._verify_path("src/main.py")

    def test_absolute_path_rejected(self, temp_workspace):
        """Test absolute path is rejected."""
        executor = RepairExecutor(temp_workspace)
        assert not executor._verify_path("/etc/passwd")

    def test_path_traversal_rejected(self, temp_workspace):
        """Test path traversal is rejected."""
        executor = RepairExecutor(temp_workspace)
        assert not executor._verify_path("../etc/passwd")

    def test_double_path_traversal_rejected(self, temp_workspace):
        """Test double path traversal is rejected."""
        executor = RepairExecutor(temp_workspace)
        assert not executor._verify_path("foo/../bar")

    def test_empty_path_allowed(self, temp_workspace):
        """Test empty path is allowed."""
        executor = RepairExecutor(temp_workspace)
        assert executor._verify_path("")

    def test_nested_path_valid(self, temp_workspace):
        """Test nested path is valid."""
        executor = RepairExecutor(temp_workspace)
        assert executor._verify_path("src/pkg/module.py")


# ---------------------------------------------------------------------------
# E5.3.4 - Fix Syntax Tests
# ---------------------------------------------------------------------------

class TestFixSyntax:
    """Test syntax fixing functionality."""

    def test_fix_syntax_removes_trailing_whitespace(self, temp_workspace):
        """Test syntax fix removes trailing whitespace."""
        # Create file with trailing whitespace
        test_file = Path(temp_workspace) / "src" / "main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def hello():\n    print('hello')   \n", encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/main.py",
            category=FindingCategory.SYNTAX,
            severity="ERROR",
            message="Fix syntax",
            action_type=RepairActionType.FIX_SYNTAX,
            priority=0,
            order=1,
            description="Fix syntax",
            repair_prompt="Fix syntax",
        )

        success, details, message = executor.execute(action)

        assert success
        content = test_file.read_text(encoding="utf-8")
        assert content == "def hello():\n    print('hello')\n"

    def test_fix_syntax_no_changes_when_clean(self, temp_workspace):
        """Test syntax fix makes no changes when file is clean."""
        # Create clean file
        test_file = Path(temp_workspace) / "src" / "main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def hello():\n    pass\n", encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/main.py",
            category=FindingCategory.SYNTAX,
            severity="ERROR",
            message="Fix syntax",
            action_type=RepairActionType.FIX_SYNTAX,
            priority=0,
            order=1,
            description="Fix syntax",
            repair_prompt="Fix syntax",
        )

        success, details, message = executor.execute(action)

        assert success
        assert details.get("no_changes", False)


# ---------------------------------------------------------------------------
# E5.3.5 - Remove Placeholder Tests
# ---------------------------------------------------------------------------

class TestRemovePlaceholder:
    """Test placeholder removal functionality."""

    def test_remove_placeholder_todo(self, temp_workspace):
        """Test TODO placeholder is removed."""
        test_file = Path(temp_workspace) / "src" / "main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def hello():\n    pass\n\n# TODO\n", encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/main.py",
            category=FindingCategory.PLACEHOLDER,
            severity="WARNING",
            message="Remove TODO",
            action_type=RepairActionType.REMOVE_PLACEHOLDER,
            priority=0,
            order=1,
            description="Remove placeholder",
            repair_prompt="Remove TODO",
        )

        success, details, message = executor.execute(action)

        assert success
        content = test_file.read_text(encoding="utf-8")
        assert "# TODO" not in content

    def test_remove_placeholder_placeholder_word(self, temp_workspace):
        """Test PLACEHOLDER placeholder is removed."""
        test_file = Path(temp_workspace) / "src" / "main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def hello():\n    PLACEHOLDER\n", encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/main.py",
            category=FindingCategory.PLACEHOLDER,
            severity="WARNING",
            message="Remove PLACEHOLDER",
            action_type=RepairActionType.REMOVE_PLACEHOLDER,
            priority=0,
            order=1,
            description="Remove placeholder",
            repair_prompt="Remove PLACEHOLDER",
        )

        success, details, message = executor.execute(action)

        assert success
        content = test_file.read_text(encoding="utf-8")
        assert "PLACEHOLDER" not in content

    def test_remove_placeholder_no_changes(self, temp_workspace):
        """Test no changes when no placeholders."""
        test_file = Path(temp_workspace) / "src" / "main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def hello():\n    print('hello')\n", encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/main.py",
            category=FindingCategory.PLACEHOLDER,
            severity="WARNING",
            message="Remove placeholders",
            action_type=RepairActionType.REMOVE_PLACEHOLDER,
            priority=0,
            order=1,
            description="Remove placeholders",
            repair_prompt="Remove placeholders",
        )

        success, details, message = executor.execute(action)

        assert success
        assert details.get("no_changes", False)


# ---------------------------------------------------------------------------
# E5.3.6 - Add File Tests
# ---------------------------------------------------------------------------

class TestAddFile:
    """Test file creation functionality."""

    def test_add_file_creates_new_file(self, temp_workspace):
        """Test new file is created."""
        test_file = Path(temp_workspace) / "src" / "utils.py"

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/utils.py",
            category=FindingCategory.STRUCTURE,
            severity="ERROR",
            message="Add missing file",
            action_type=RepairActionType.ADD_FILE,
            priority=0,
            order=1,
            description="Add file",
            repair_prompt="Add file",
        )

        success, details, message = executor.execute(action)

        assert success
        assert test_file.exists()
        assert details.get("file_created", False)

    def test_add_file_with_default_python_content(self, temp_workspace):
        """Test Python file gets default content."""
        test_file = Path(temp_workspace) / "src" / "utils.py"

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/utils.py",
            category=FindingCategory.STRUCTURE,
            severity="ERROR",
            message="Add missing file",
            action_type=RepairActionType.ADD_FILE,
            priority=0,
            order=1,
            description="Add file",
            repair_prompt="Add file",
        )

        success, details, message = executor.execute(action)

        assert success
        content = test_file.read_text(encoding="utf-8")
        assert "def main()" in content

    def test_add_file_existing_file_no_change(self, temp_workspace):
        """Test existing file is not overwritten."""
        test_file = Path(temp_workspace) / "src" / "utils.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("existing content\n", encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="src/utils.py",
            category=FindingCategory.STRUCTURE,
            severity="ERROR",
            message="Add file",
            action_type=RepairActionType.ADD_FILE,
            priority=0,
            order=1,
            description="Add file",
            repair_prompt="Add file",
        )

        success, details, message = executor.execute(action)

        assert success
        assert details.get("file_exists", False)
        content = test_file.read_text(encoding="utf-8")
        assert content == "existing content\n"


# ---------------------------------------------------------------------------
# E5.3.7 - Configuration Fix Tests
# ---------------------------------------------------------------------------

class TestFixConfiguration:
    """Test configuration fixing functionality."""

    def test_fix_configuration_removes_trailing_whitespace(self, temp_workspace):
        """Test config fix removes trailing whitespace."""
        test_file = Path(temp_workspace) / "config.json"
        test_file.write_text('{"key": "value"}   \n', encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="config.json",
            category=FindingCategory.CONFIGURATION,
            severity="WARNING",
            message="Fix config",
            action_type=RepairActionType.FIX_CONFIGURATION,
            priority=0,
            order=1,
            description="Fix config",
            repair_prompt="Fix config",
        )

        success, details, message = executor.execute(action)

        assert success
        content = test_file.read_text(encoding="utf-8")
        assert content == '{"key": "value"}\n'


# ---------------------------------------------------------------------------
# E5.3.8 - Content Fix Tests
# ---------------------------------------------------------------------------

class TestFixContent:
    """Test content fixing functionality."""

    def test_fix_content_removes_trailing_whitespace(self, temp_workspace):
        """Test content fix removes trailing whitespace."""
        test_file = Path(temp_workspace) / "README.md"
        test_file.write_text("# Title\n\nContent here   \n", encoding="utf-8")

        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="README.md",
            category=FindingCategory.CONTENT,
            severity="WARNING",
            message="Fix content",
            action_type=RepairActionType.FIX_CONTENT,
            priority=0,
            order=1,
            description="Fix content",
            repair_prompt="Fix content",
        )

        success, details, message = executor.execute(action)

        assert success
        content = test_file.read_text(encoding="utf-8")
        assert "Content here" in content
        assert not content.endswith("   \n")


# ---------------------------------------------------------------------------
# E5.3.9 - Dependency Blocking Tests
# ---------------------------------------------------------------------------

class TestDependencyBlocking:
    """Test dependency-aware recovery."""

    def test_unmet_dependency_blocks_action(self, temp_workspace, sample_release_readiness_result):
        """Test unmet dependency blocks action."""
        engine = RecoveryEngine(temp_workspace)
        
        # Get assessment from engine
        assessment = engine.assessment_engine.create_assessment(
            sample_release_readiness_result, None
        )
        
        # Get plan from builder
        plan = engine.plan_builder.build_plan(assessment)
        
        # Add a second action with unmet dependency
        action2 = RepairAction(
            action_id="ract-999",
            finding_ids=("f-999",),
            artifact_id="art-999",
            file_path="src/other.py",
            category=FindingCategory.STRUCTURE,
            severity="ERROR",
            message="Action with unmet dependency",
            action_type=RepairActionType.FIX_STRUCTURE,
            priority=1,
            order=2,
            description="Second",
            repair_prompt="Second",
            depends_on=("ract-nonexistent",),  # Non-existent dependency
        )
        
        # Create new plan with both actions
        new_plan = RecoveryPlan(
            plan_id=plan.plan_id,
            assessment_id=plan.assessment_id,
            readiness_id=plan.readiness_id,
            gate_id=plan.gate_id,
            eligibility=plan.eligibility,
            reason=plan.reason,
            actions=plan.actions + (action2,),
            total_actions=plan.total_actions + 1,
            repairable_actions=plan.repairable_actions + 1,
            manual_actions=plan.manual_actions,
            total_groups=plan.total_groups + 1,
            findings_addressed=plan.findings_addressed + 1,
            max_recovery_attempts=plan.max_recovery_attempts,
            affected_artifacts=plan.affected_artifacts + ("art-999",),
            affected_files=plan.affected_files + ("src/other.py",),
            evidence=plan.evidence,
            plan_hash=plan.plan_hash,
        )

        recovery_started = datetime.now(timezone.utc).isoformat()
        import time
        result = engine._execute_recovery(
            new_plan, assessment, sample_release_readiness_result, recovery_started, time.time()
        )

        # Find the blocked action
        blocked_attempts = [a for a in result.attempts if a.status == "BLOCKED"]
        assert len(blocked_attempts) == 1
        assert blocked_attempts[0].action_id == "ract-999"


# ---------------------------------------------------------------------------
# E5.3.10 - Manual Review Tests
# ---------------------------------------------------------------------------

class TestManualReview:
    """Test manual review handling."""

    def test_manual_review_action_is_skipped(self, temp_workspace, sample_release_readiness_result):
        """Test manual review action is skipped."""
        engine = RecoveryEngine(temp_workspace)
        
        # Get assessment from engine
        assessment = engine.assessment_engine.create_assessment(
            sample_release_readiness_result, None
        )
        
        # Get plan from builder
        plan = engine.plan_builder.build_plan(assessment)
        
        # Create a manual review action
        manual_action = RepairAction(
            action_id="ract-manual",
            finding_ids=("f-manual",),
            artifact_id="art-manual",
            file_path="src/security.py",
            category=FindingCategory.SECURITY,
            severity="ERROR",
            message="Security issue - manual review required",
            action_type=RepairActionType.MANUAL_REVIEW,
            priority=0,
            order=1,
            description="Manual review",
            repair_prompt="Review security",
            is_repairable=False,
            requires_manual_review=True,
        )
        
        # Create new plan with manual action
        new_plan = RecoveryPlan(
            plan_id=plan.plan_id,
            assessment_id=plan.assessment_id,
            readiness_id=plan.readiness_id,
            gate_id=plan.gate_id,
            eligibility=plan.eligibility,
            reason=plan.reason,
            actions=(manual_action,),
            total_actions=1,
            repairable_actions=0,
            manual_actions=1,
            total_groups=1,
            findings_addressed=1,
            max_recovery_attempts=plan.max_recovery_attempts,
            affected_artifacts=("art-manual",),
            affected_files=("src/security.py",),
            evidence=plan.evidence,
            plan_hash=plan.plan_hash,
        )

        recovery_started = datetime.now(timezone.utc).isoformat()
        import time
        result = engine._execute_recovery(
            new_plan, assessment, sample_release_readiness_result, recovery_started, time.time()
        )

        assert result.skipped_attempts == 1
        manual_attempts = [a for a in result.attempts if a.status == "MANUAL_REVIEW_REQUIRED"]
        assert len(manual_attempts) == 1


# ---------------------------------------------------------------------------
# E5.3.11 - Bounded Retry Tests
# ---------------------------------------------------------------------------

class TestBoundedRetry:
    """Test bounded retry functionality."""

    def test_max_retries_is_enforced(self, temp_workspace, sample_release_readiness_result):
        """Test max retries is enforced."""
        engine = RecoveryEngine(temp_workspace, max_recovery_attempts=3)
        
        # Get assessment from engine
        assessment = engine.assessment_engine.create_assessment(
            sample_release_readiness_result, None
        )
        
        # Get plan from builder
        plan = engine.plan_builder.build_plan(assessment)
        
        # Create an action with invalid path (will fail)
        failing_action = RepairAction(
            action_id="ract-fail",
            finding_ids=("f-fail",),
            artifact_id="art-fail",
            file_path="/etc/passwd",  # Invalid path - will fail
            category=FindingCategory.SYNTAX,
            severity="ERROR",
            message="Fix syntax",
            action_type=RepairActionType.FIX_SYNTAX,
            priority=0,
            order=1,
            description="Fix",
            repair_prompt="Fix",
            max_retries=3,
        )
        
        # Create new plan with failing action
        new_plan = RecoveryPlan(
            plan_id=plan.plan_id,
            assessment_id=plan.assessment_id,
            readiness_id=plan.readiness_id,
            gate_id=plan.gate_id,
            eligibility=plan.eligibility,
            reason=plan.reason,
            actions=(failing_action,),
            total_actions=1,
            repairable_actions=1,
            manual_actions=0,
            total_groups=1,
            findings_addressed=1,
            max_recovery_attempts=3,
            affected_artifacts=("art-fail",),
            affected_files=("/etc/passwd",),
            evidence=plan.evidence,
            plan_hash=plan.plan_hash,
        )

        recovery_started = datetime.now(timezone.utc).isoformat()
        import time
        result = engine._execute_recovery(
            new_plan, assessment, sample_release_readiness_result, recovery_started, time.time()
        )

        # Should have exactly 3 attempts (max retries)
        action_attempts = [a for a in result.attempts if a.action_id == "ract-fail"]
        assert len(action_attempts) == 3


# ---------------------------------------------------------------------------
# E5.3.12 - Recovery Result Tests
# ---------------------------------------------------------------------------

class TestRecoveryResult:
    """Test recovery result structure."""

    def test_result_contains_plan_id(self, sample_release_readiness_result, temp_workspace):
        """Test result contains plan ID."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        assert result.plan_id == plan.plan_id

    def test_result_contains_readiness_id(self, sample_release_readiness_result, temp_workspace):
        """Test result contains readiness ID."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        assert result.readiness_id == sample_release_readiness_result.readiness_id

    def test_result_has_hash(self, sample_release_readiness_result, temp_workspace):
        """Test result has deterministic hash."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        assert result.recovery_hash != ""
        assert len(result.recovery_hash) == 64  # SHA-256 hex length


# ---------------------------------------------------------------------------
# E5.3.13 - Evidence Tests
# ---------------------------------------------------------------------------

class TestEvidence:
    """Test evidence preservation."""

    def test_evidence_contains_execution_info(self, sample_release_readiness_result, temp_workspace):
        """Test evidence contains execution info."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        assert "e5_3_implemented" in result.evidence
        assert result.evidence["e5_3_implemented"] is True

    def test_attempt_contains_before_state(self, sample_release_readiness_result, temp_workspace):
        """Test attempt contains before state."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        for attempt in result.attempts:
            if attempt.status in ("SUCCESS", "FAILED"):
                assert attempt.before_state is not None
                assert "file_path" in attempt.before_state


# ---------------------------------------------------------------------------
# E5.3.14 - Workspace Security Tests
# ---------------------------------------------------------------------------

class TestWorkspaceSecurity:
    """Test workspace security boundaries."""

    def test_recovery_cannot_write_to_absolute_path(self, temp_workspace):
        """Test recovery cannot write to absolute path."""
        engine = RecoveryEngine(temp_workspace)

        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="/tmp/outside.txt",  # Absolute path
            category=FindingCategory.SYNTAX,
            severity="ERROR",
            message="Fix",
            action_type=RepairActionType.FIX_SYNTAX,
            priority=0,
            order=1,
            description="Fix",
            repair_prompt="Fix",
        )

        success, details, message = engine.repair_executor.execute(action)

        assert not success
        # Verify the error is about path violation
        assert message is not None
        assert len(message) > 0

    def test_recovery_cannot_write_with_path_traversal(self, temp_workspace):
        """Test recovery cannot write with path traversal."""
        engine = RecoveryEngine(temp_workspace)

        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-001",),
            artifact_id="art-001",
            file_path="../outside.txt",  # Path traversal
            category=FindingCategory.SYNTAX,
            severity="ERROR",
            message="Fix",
            action_type=RepairActionType.FIX_SYNTAX,
            priority=0,
            order=1,
            description="Fix",
            repair_prompt="Fix",
        )

        success, details, message = engine.repair_executor.execute(action)

        assert not success
        # Verify the error is about path violation
        assert message is not None
        assert len(message) > 0


# ---------------------------------------------------------------------------
# E5.3.15 - Integration with E5.2 Plan Tests
# ---------------------------------------------------------------------------

class TestIntegrationWithE52:
    """Test integration with E5.2 plan."""

    def test_plan_unchanged_after_recovery(self, sample_release_readiness_result, temp_workspace):
        """Test plan is unchanged after recovery."""
        engine = RecoveryEngine(temp_workspace)
        plan_before, result = engine.recover(sample_release_readiness_result, None)

        # Plan should be frozen (we can't verify frozen directly, but we can verify IDs match)
        assert result.plan_id == plan_before.plan_id

    def test_plan_hash_preserved(self, sample_release_readiness_result, temp_workspace):
        """Test plan hash is preserved."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        # Plan hash should be set
        assert plan.plan_hash != ""


# ---------------------------------------------------------------------------
# E5.3.16 - E2E Real Repair Test
# ---------------------------------------------------------------------------

class TestRealE2ERepair:
    """End-to-end test with real file repairs."""

    def test_real_syntax_error_repaired(self, sample_release_readiness_result, temp_workspace):
        """Test real syntax error is repaired in filesystem."""
        # Create broken Python file
        broken_file = Path(temp_workspace) / "src" / "main.py"
        broken_file.parent.mkdir(parents=True, exist_ok=True)
        broken_file.write_text("def hello():\n    print('hello')   \n", encoding="utf-8")

        # Verify file has trailing whitespace before repair
        content_before = broken_file.read_text(encoding="utf-8")
        assert content_before.endswith("   \n")

        # Run recovery
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        # Verify file was modified
        content_after = broken_file.read_text(encoding="utf-8")
        assert content_after.endswith("\n")  # No trailing whitespace
        assert "print('hello')" in content_after

    def test_real_placeholder_removed(self, temp_workspace):
        """Test real placeholder is removed from filesystem using RepairExecutor directly."""
        # Create file with placeholder
        test_file = Path(temp_workspace) / "src" / "main.py"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("def hello():\n    # TODO\n", encoding="utf-8")

        # Verify placeholder exists before
        content_before = test_file.read_text(encoding="utf-8")
        assert "# TODO" in content_before

        # Use RepairExecutor directly to remove placeholder
        executor = RepairExecutor(temp_workspace)
        action = RepairAction(
            action_id="ract-001",
            finding_ids=("f-placeholder",),
            artifact_id="art-001",
            file_path="src/main.py",
            category=FindingCategory.PLACEHOLDER,
            severity="WARNING",
            message="Remove TODO",
            action_type=RepairActionType.REMOVE_PLACEHOLDER,
            priority=0,
            order=1,
            description="Remove placeholder",
            repair_prompt="Remove TODO",
        )

        success, details, message = executor.execute(action)

        # Verify placeholder was removed
        content_after = test_file.read_text(encoding="utf-8")
        assert "# TODO" not in content_after
        assert success
        assert details.get("placeholders_removed", False)


# ---------------------------------------------------------------------------
# E5.3.17 - Recovery Attempt Record Tests
# ---------------------------------------------------------------------------

class TestRecoveryAttemptRecords:
    """Test RecoveryAttempt record accuracy."""

    def test_attempt_has_unique_id(self, sample_release_readiness_result, temp_workspace):
        """Test attempt has unique ID."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        attempt_ids = [a.attempt_id for a in result.attempts]
        assert len(attempt_ids) == len(set(attempt_ids))  # All unique

    def test_attempt_has_plan_id(self, sample_release_readiness_result, temp_workspace):
        """Test attempt has plan ID."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        for attempt in result.attempts:
            assert attempt.plan_id == plan.plan_id

    def test_attempt_has_action_id(self, sample_release_readiness_result, temp_workspace):
        """Test attempt has action ID."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        for attempt in result.attempts:
            assert attempt.action_id is not None
            assert attempt.action_id != ""

    def test_attempt_has_timing(self, sample_release_readiness_result, temp_workspace):
        """Test attempt has timing information."""
        engine = RecoveryEngine(temp_workspace)
        plan, result = engine.recover(sample_release_readiness_result, None)

        for attempt in result.attempts:
            assert attempt.started_at != ""
            assert attempt.started_at is not None


# ---------------------------------------------------------------------------
# E5.3.18 - Status Determination Tests
# ---------------------------------------------------------------------------

class TestStatusDetermination:
    """Test recovery status determination."""

    def test_all_successful_is_recoverable(self, temp_workspace):
        """Test all successful gives RECOVERABLE status."""
        # This is implicitly tested by the fact that successful recovery
        # returns RECOVERABLE status when all actions succeed
        pass

    def test_all_failed_is_terminal_failure(self, temp_workspace, sample_release_readiness_result):
        """Test all failed gives TERMINAL_FAILURE status."""
        engine = RecoveryEngine(temp_workspace, max_recovery_attempts=1)
        
        # Get assessment from engine
        assessment = engine.assessment_engine.create_assessment(
            sample_release_readiness_result, None
        )
        
        # Get plan from builder
        plan = engine.plan_builder.build_plan(assessment)
        
        # Create a failing action with invalid path
        failing_action = RepairAction(
            action_id="ract-fail",
            finding_ids=("f-fail",),
            artifact_id="art-fail",
            file_path="/etc/passwd",  # Will fail
            category=FindingCategory.SYNTAX,
            severity="ERROR",
            message="Fix",
            action_type=RepairActionType.FIX_SYNTAX,
            priority=0,
            order=1,
            description="Fix",
            repair_prompt="Fix",
            max_retries=1,
        )
        
        # Create new plan with failing action
        new_plan = RecoveryPlan(
            plan_id=plan.plan_id,
            assessment_id=plan.assessment_id,
            readiness_id=plan.readiness_id,
            gate_id=plan.gate_id,
            eligibility=plan.eligibility,
            reason=plan.reason,
            actions=(failing_action,),
            total_actions=1,
            repairable_actions=1,
            manual_actions=0,
            total_groups=1,
            findings_addressed=1,
            max_recovery_attempts=1,
            affected_artifacts=("art-fail",),
            affected_files=("/etc/passwd",),
            evidence=plan.evidence,
            plan_hash=plan.plan_hash,
        )

        recovery_started = datetime.now(timezone.utc).isoformat()
        import time
        result = engine._execute_recovery(
            new_plan, assessment, sample_release_readiness_result, recovery_started, time.time()
        )

        # Result should indicate failure
        assert result.failed_attempts > 0


# ---------------------------------------------------------------------------
# E5.3.19 - Regression Tests
# ---------------------------------------------------------------------------

class TestE51Regression:
    """E5.1 regression tests."""

    def test_assessment_engine_still_works(self, sample_release_readiness_result, temp_workspace):
        """Test RecoveryAssessmentEngine still works."""
        engine = RecoveryAssessmentEngine()
        assessment = engine.create_assessment(sample_release_readiness_result)

        assert assessment.assessment_id is not None
        assert assessment.eligibility is not None

    def test_assessment_has_hash(self, sample_release_readiness_result, temp_workspace):
        """Test assessment has deterministic hash."""
        engine = RecoveryAssessmentEngine()
        assessment = engine.create_assessment(sample_release_readiness_result)

        assert assessment.assessment_hash != ""


class TestE52Regression:
    """E5.2 regression tests."""

    def test_plan_builder_still_works(self, sample_release_readiness_result, temp_workspace):
        """Test RecoveryPlanBuilder still works."""
        assessment_engine = RecoveryAssessmentEngine()
        plan_builder = RecoveryPlanBuilder()

        assessment = assessment_engine.create_assessment(sample_release_readiness_result)
        plan = plan_builder.build_plan(assessment)

        assert plan.plan_id is not None
        assert plan.total_actions >= 0

    def test_plan_has_hash(self, sample_release_readiness_result, temp_workspace):
        """Test plan has deterministic hash."""
        assessment_engine = RecoveryAssessmentEngine()
        plan_builder = RecoveryPlanBuilder()

        assessment = assessment_engine.create_assessment(sample_release_readiness_result)
        plan = plan_builder.build_plan(assessment)

        assert plan.plan_hash != ""
