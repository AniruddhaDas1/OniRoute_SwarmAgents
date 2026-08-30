"""E4.1 Review Pipeline Integration.

Phase E4.1 — Real Artifact Review & Quality Gates.

Integrates ReviewEngine into the existing ProjectExecutionEngine flow.

Target flow:
    Mission
        ↓
    Requirements
        ↓
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionOrchestrator
        ↓
    RealCodeGenerationEngine
        ↓
    InvocationEngine / UMAL
        ↓
    RepositoryWriter
        ↓
    REAL FILES
        ↓
    ReviewEngine
        ↓
    ReviewReport
        ↓
    ReviewVerdict
        ↓
    ProjectExecutionResult

Does NOT:
- Move orchestration logic into CLI
- Change frozen E1 contracts
- Implement self-healing (E5)
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from runtime.contracts.e34_models import (
    ArtifactFileResult,
    ProjectExecutionResult,
)
from runtime.contracts.e4_models import (
    ReviewCheckResult,
    ReviewError,
    ReviewFinding,
    ReviewHistoryEntry,
    ReviewReport,
    ReviewRequest,
    ReviewSeverity,
    ReviewVerdict,
    compute_review_report_hash,
    generate_review_id,
)
from runtime.contracts.review import ReviewEngine


# ---------------------------------------------------------------------------
# E4.7 - Review Integration with ProjectExecutionResult
# ---------------------------------------------------------------------------

class ReviewIntegration:
    """Integrates ReviewEngine into project execution flow.

    This class:
    - Runs ReviewEngine after generation/writing
    - Produces ReviewReport with findings and verdict
    - Merges review results into ProjectExecutionResult
    - Preserves generated files on review failure
    - Does NOT retry or self-heal (E5)
    """

    def __init__(self, workspace_root: str):
        """Initialize review integration.

        Args:
            workspace_root: Absolute path to workspace root
        """
        self.workspace_root = workspace_root
        self._review_engine = ReviewEngine(workspace_root)

    def execute_review(
        self,
        execution_result: ProjectExecutionResult,
        file_results: List[ArtifactFileResult],
        strict_mode: bool = False,
        skip_syntax_checks: bool = False,
    ) -> Tuple[ProjectExecutionResult, ReviewReport]:
        """Execute review on generated artifacts.

        Args:
            execution_result: Result from ProjectExecutionEngine
            file_results: List of file results from generation
            strict_mode: If True, treat warnings as errors
            skip_syntax_checks: If True, skip syntax validation

        Returns:
            Tuple of (updated_execution_result, review_report)
        """
        # Create review request
        review_id = generate_review_id(execution_result.mission_id)
        request = ReviewRequest(
            review_id=review_id,
            mission_id=execution_result.mission_id,
            workspace_id=execution_result.workspace_id,
            plan_id=execution_result.plan_id,
            workspace_root=execution_result.workspace_root,
            repository_scope=execution_result.repository_scope,
            file_paths=tuple(fr.target_path for fr in file_results),
            artifact_files=tuple(
                (fr.artifact_execution_id, fr.target_path)
                for fr in file_results
            ),
            artifact_execution_ids=tuple(fr.artifact_execution_id for fr in file_results),
            strict_mode=strict_mode,
            skip_syntax_checks=skip_syntax_checks,
        )

        # Execute review
        report = self._review_engine.review(request, file_results)

        # Update verdict based on execution result if needed
        if not execution_result.is_success:
            # If generation failed, review is blocked
            report.verdict = ReviewVerdict.BLOCKED
            report.verdict_reasons = (
                ("Generation failed - review blocked",) +
                report.verdict_reasons
            )

        # Update execution result with review info
        updated_result = self._merge_review_into_result(execution_result, report)

        return updated_result, report

    def _merge_review_into_result(
        self,
        execution_result: ProjectExecutionResult,
        report: ReviewReport,
    ) -> ProjectExecutionResult:
        """Merge review results into execution result.

        Args:
            execution_result: Original execution result
            report: Review report

        Returns:
            Updated execution result with review info
        """
        # Determine overall status based on review
        if report.verdict == ReviewVerdict.BLOCKED:
            overall_status = "BLOCKED"
            is_success = False
        elif report.verdict == ReviewVerdict.FAIL:
            overall_status = "FAILED"
            is_success = False
        elif report.verdict == ReviewVerdict.PASS_WITH_WARNINGS:
            overall_status = "SUCCESS_WITH_WARNINGS"
            is_success = True
        else:
            overall_status = execution_result.execution_status
            is_success = execution_result.is_success

        # Collect errors from review
        review_errors = []
        for finding in report.findings:
            if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.ERROR):
                review_errors.append(f"[{finding.severity.value}] {finding.message}")

        # Update execution result
        execution_result.execution_status = overall_status
        execution_result.is_success = is_success

        # Add review-specific failure evidence
        if report.findings:
            for finding in report.findings:
                if finding.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.ERROR):
                    evidence = f"Review finding: {finding.check_type} - {finding.message}"
                    if evidence not in execution_result.failure_evidence:
                        execution_result.failure_evidence.append(evidence)

        # Re-compute deterministic hash
        execution_result.deterministic_hash = self._compute_result_hash(
            execution_result, report
        )

        return execution_result

    def _compute_result_hash(
        self,
        result: ProjectExecutionResult,
        report: ReviewReport,
    ) -> str:
        """Compute deterministic hash including review result."""
        payload = {
            "execution_id": result.execution_id,
            "mission_id": result.mission_id,
            "plan_id": result.plan_id,
            "files_written": result.files_written,
            "review_verdict": report.verdict.value,
            "review_findings": report.total_findings,
        }
        json_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# E4.9 - Review History Integration
# ---------------------------------------------------------------------------

class ReviewHistory:
    """Manages review history and evidence preservation.

    Integrates with existing runtime history/evidence mechanisms.
    """

    def __init__(self, history_file: Optional[str] = None):
        """Initialize review history.

        Args:
            history_file: Optional path to history file
        """
        self.history_file = history_file

    def record_review(
        self,
        report: ReviewReport,
    ) -> ReviewHistoryEntry:
        """Record a review in history.

        Args:
            report: The review report to record

        Returns:
            ReviewHistoryEntry
        """
        entry = ReviewHistoryEntry(
            entry_id=f"hist-{report.review_id}",
            review_id=report.review_id,
            mission_id=report.mission_id,
            workspace_id=report.workspace_id,
            plan_id=report.plan_id,
            verdict=report.verdict,
            total_findings=report.total_findings,
            critical_count=report.critical_findings,
            error_count=report.error_findings,
            warning_count=report.warning_findings,
            timestamp=report.review_completed,
            duration_ms=report.total_duration_ms,
            files_reviewed=report.files_reviewed,
            files_with_issues=report.files_with_issues,
            report_id=report.report_id,
        )

        # Persist to file if configured
        if self.history_file:
            self._append_to_file(entry)

        return entry

    def _append_to_file(self, entry: ReviewHistoryEntry) -> None:
        """Append entry to history file.

        Args:
            entry: History entry to append
        """
        import os
        from pathlib import Path

        path = Path(self.history_file) if self.history_file else Path.home() / ".oniroute" / "review_history.json"

        # Create directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing entries
        entries = []
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, OSError):
                entries = []

        # Append new entry
        entries.append(entry.model_dump())

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

    def get_history(
        self,
        mission_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ReviewHistoryEntry]:
        """Get review history.

        Args:
            mission_id: Optional filter by mission ID
            limit: Maximum entries to return

        Returns:
            List of review history entries
        """
        if not self.history_file:
            return []

        path = Path(self.history_file)
        if not path.exists():
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        # Filter by mission if specified
        if mission_id:
            entries = [e for e in entries if e.get("mission_id") == mission_id]

        # Convert to objects and limit
        result = []
        for entry_data in entries[-limit:]:
            try:
                result.append(ReviewHistoryEntry(**entry_data))
            except Exception:
                continue

        return result


# ---------------------------------------------------------------------------
# E4.8 - Review Failure Boundary
# ---------------------------------------------------------------------------

class ReviewFailureBoundary:
    """Implements failure boundary for review failures.

    Ensures:
    - Generated files are preserved
    - Review evidence is preserved
    - Execution context is preserved
    - Structured failure is returned
    - No silent deletion of artifacts
    - No regeneration or retry
    """

    @staticmethod
    def handle_review_failure(
        report: ReviewReport,
        file_results: List[ArtifactFileResult],
        workspace_root: str,
    ) -> Dict[str, Any]:
        """Handle review failure with full evidence preservation.

        Args:
            report: The review report with failures
            file_results: File results from generation
            workspace_root: Workspace root path

        Returns:
            Failure report with preserved evidence
        """
        # Collect all artifacts that exist on disk
        preserved_artifacts = []
        for fr in file_results:
            if fr.file_written and fr.absolute_path:
                import os
                if os.path.exists(fr.absolute_path):
                    preserved_artifacts.append({
                        "artifact_execution_id": fr.artifact_execution_id,
                        "target_path": fr.target_path,
                        "absolute_path": fr.absolute_path,
                        "size_bytes": os.path.getsize(fr.absolute_path),
                    })

        return {
            "status": "REVIEW_FAILED",
            "verdict": report.verdict.value,
            "review_id": report.review_id,
            "report_id": report.report_id,
            "total_findings": report.total_findings,
            "critical_findings": report.critical_findings,
            "error_findings": report.error_findings,
            "warning_findings": report.warning_findings,
            "findings": [
                {
                    "finding_id": f.finding_id,
                    "check_type": f.check_type,
                    "severity": f.severity.value,
                    "message": f.message,
                    "file_path": f.file_path,
                    "is_blocking": f.is_blocking,
                }
                for f in report.findings
            ],
            "workspace_root": workspace_root,
            "preserved_artifacts": preserved_artifacts,
            "artifacts_preserved": len(preserved_artifacts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def is_review_blocking(verdict: ReviewVerdict) -> bool:
        """Check if verdict blocks mission completion.

        Args:
            verdict: Review verdict

        Returns:
            True if verdict blocks mission
        """
        return verdict in (ReviewVerdict.BLOCKED, ReviewVerdict.FAIL)
