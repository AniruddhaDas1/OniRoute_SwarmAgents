"""E4.2 Review Finding Analysis & Quality Gate Decision Engine.

Phase E4.2 — Review Finding Analysis & Quality Gate Decision Engine.

Implements:
- FindingClassificationEngine: Classifies findings by category and remediation
- FindingAggregator: Aggregates findings by various dimensions
- QualityGateDecisionEngine: Produces deterministic quality gate decisions
- Artifact-level and project-level decisions

Architecture:
    ReviewReport (E4.1)
        ↓
    FindingClassificationEngine
        ↓
    FindingAggregator
        ↓
    QualityGateDecisionEngine
        ↓
    QualityGateResult
        ↓
    Future remediation phase (E5)

Does NOT:
- Regenerate source code
- Modify generated files
- Perform self-healing
- Call LLM for gate decision
- Modify frozen E1 contracts

Self-contained: depends only on Python stdlib + pydantic + E4.1 models.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from runtime.contracts.e4_models import (
    ReviewFinding,
    ReviewReport,
    ReviewSeverity,
    ReviewVerdict,
)
from runtime.contracts.e42_models import (
    AnalysisError,
    ArtifactLevelDecision,
    BlockingCounts,
    CategoryCounts,
    CHECK_TYPE_TO_CATEGORY,
    classify_finding,
    compute_evidence_hash,
    compute_quality_gate_hash,
    determine_remediation_category,
    EvidenceEntry,
    FindingAggregation,
    FindingCategory,
    FindingClassification,
    GroupedByArtifact,
    GroupedByCategory,
    GroupedByFile,
    GroupedByRule,
    InvalidReportError,
    ProjectLevelDecision,
    QualityGateDecision,
    QualityGateEvidence,
    QualityGateError,
    QualityGateResult,
    RemediationCategory,
    SeverityCounts,
)


# ---------------------------------------------------------------------------
# E4.2.1 - Finding Classification Engine
# ---------------------------------------------------------------------------

class FindingClassificationEngine:
    """Classifies review findings into categories and remediation types.

    Deterministic: Same findings produce same classifications.
    No LLM calls.
    """

    def classify_findings(
        self,
        findings: List[ReviewFinding],
    ) -> List[FindingClassification]:
        """Classify all findings.

        Args:
            findings: List of ReviewFindings to classify

        Returns:
            List of FindingClassifications
        """
        return [classify_finding(f) for f in findings]

    def classify_finding(
        self,
        finding: ReviewFinding,
    ) -> FindingClassification:
        """Classify a single finding.

        Args:
            finding: ReviewFinding to classify

        Returns:
            FindingClassification
        """
        return classify_finding(finding)


# ---------------------------------------------------------------------------
# E4.2.2 - Finding Aggregator
# ---------------------------------------------------------------------------

class FindingAggregator:
    """Aggregates findings by various dimensions.

    Provides deterministic aggregation for:
    - Severity counts
    - Blocking counts
    - Category counts
    - Grouping by artifact, file, rule, category
    """

    def aggregate(
        self,
        findings: List[ReviewFinding],
        classifications: List[FindingClassification],
    ) -> FindingAggregation:
        """Aggregate findings.

        Args:
            findings: Original findings
            classifications: Classifications of findings

        Returns:
            FindingAggregation with counts and groups
        """
        # Severity counts
        severity_counts = SeverityCounts(
            total=len(findings),
            critical=sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL),
            error=sum(1 for f in findings if f.severity == ReviewSeverity.ERROR),
            warning=sum(1 for f in findings if f.severity == ReviewSeverity.WARNING),
            info=sum(1 for f in findings if f.severity == ReviewSeverity.INFO),
        )

        # Blocking counts
        blocking_counts = BlockingCounts(
            total_blocking=sum(1 for f in findings if f.is_blocking),
            non_blocking=sum(1 for f in findings if not f.is_blocking),
        )

        # Category counts
        category_dict: Dict[str, int] = {}
        for c in classifications:
            cat_str = c.category.value
            category_dict[cat_str] = category_dict.get(cat_str, 0) + 1
        category_counts = CategoryCounts(by_category=category_dict)

        # Unique IDs (deterministic ordering)
        unique_artifacts = sorted(set(f.artifact_id for f in findings if f.artifact_id))
        unique_files = sorted(set(f.file_path for f in findings if f.file_path))
        unique_rules = sorted(set(f.rule_id for f in findings if f.rule_id))
        unique_checks = sorted(set(f.check_type for f in findings))

        return FindingAggregation(
            severity_counts=severity_counts,
            blocking_counts=blocking_counts,
            category_counts=category_counts,
            unique_artifact_ids=tuple(unique_artifacts),
            unique_file_paths=tuple(unique_files),
            unique_rule_ids=tuple(unique_rules),
            unique_check_types=tuple(unique_checks),
            affected_artifact_count=len(unique_artifacts),
            affected_file_count=len(unique_files),
        )

    def group_by_artifact(
        self,
        classifications: List[FindingClassification],
        findings: List[ReviewFinding],
    ) -> List[GroupedByArtifact]:
        """Group findings by artifact ID.

        Args:
            classifications: Classified findings
            findings: Original findings

        Returns:
            List of GroupedByArtifact (deterministic order)
        """
        # Create lookup from finding_id to finding
        finding_map = {f.finding_id: f for f in findings}

        # Group by artifact_id
        artifact_groups: Dict[str, List[FindingClassification]] = {}
        for c in classifications:
            if c.artifact_id:
                if c.artifact_id not in artifact_groups:
                    artifact_groups[c.artifact_id] = []
                artifact_groups[c.artifact_id].append(c)

        # Build result in deterministic order
        result = []
        for artifact_id in sorted(artifact_groups.keys()):
            group_findings = artifact_groups[artifact_id]

            # Calculate severity counts for this artifact
            crit = sum(1 for f in group_findings if f.severity == ReviewSeverity.CRITICAL)
            err = sum(1 for f in group_findings if f.severity == ReviewSeverity.ERROR)
            warn = sum(1 for f in group_findings if f.severity == ReviewSeverity.WARNING)
            inf = sum(1 for f in group_findings if f.severity == ReviewSeverity.INFO)

            blocking = sum(1 for f in group_findings if f.is_blocking)

            # Get files for this artifact
            files = sorted(set(f.file_path for f in group_findings if f.file_path))

            result.append(GroupedByArtifact(
                artifact_id=artifact_id,
                findings=tuple(sorted(group_findings, key=lambda x: x.finding_id)),
                severity_counts=SeverityCounts(
                    total=len(group_findings),
                    critical=crit,
                    error=err,
                    warning=warn,
                    info=inf,
                ),
                blocking_count=blocking,
            ))

        return result

    def group_by_file(
        self,
        classifications: List[FindingClassification],
    ) -> List[GroupedByFile]:
        """Group findings by file path.

        Args:
            classifications: Classified findings

        Returns:
            List of GroupedByFile (deterministic order)
        """
        # Group by file_path
        file_groups: Dict[str, List[FindingClassification]] = {}
        for c in classifications:
            if c.file_path:
                if c.file_path not in file_groups:
                    file_groups[c.file_path] = []
                file_groups[c.file_path].append(c)

        # Build result in deterministic order
        result = []
        for file_path in sorted(file_groups.keys()):
            group_findings = file_groups[file_path]

            # Calculate severity counts
            crit = sum(1 for f in group_findings if f.severity == ReviewSeverity.CRITICAL)
            err = sum(1 for f in group_findings if f.severity == ReviewSeverity.ERROR)
            warn = sum(1 for f in group_findings if f.severity == ReviewSeverity.WARNING)
            inf = sum(1 for f in group_findings if f.severity == ReviewSeverity.INFO)

            # Get artifact_id (may be empty)
            artifact_ids = set(f.artifact_id for f in group_findings if f.artifact_id)
            artifact_id = next(iter(artifact_ids), "") if artifact_ids else ""

            result.append(GroupedByFile(
                file_path=file_path,
                artifact_id=artifact_id,
                findings=tuple(sorted(group_findings, key=lambda x: x.finding_id)),
                severity_counts=SeverityCounts(
                    total=len(group_findings),
                    critical=crit,
                    error=err,
                    warning=warn,
                    info=inf,
                ),
            ))

        return result

    def group_by_rule(
        self,
        classifications: List[FindingClassification],
    ) -> List[GroupedByRule]:
        """Group findings by rule ID.

        Args:
            classifications: Classified findings

        Returns:
            List of GroupedByRule (deterministic order)
        """
        # Group by rule_id
        rule_groups: Dict[str, List[FindingClassification]] = {}
        for c in classifications:
            if c.rule_id:
                if c.rule_id not in rule_groups:
                    rule_groups[c.rule_id] = []
                rule_groups[c.rule_id].append(c)

        # Build result in deterministic order
        result = []
        for rule_id in sorted(rule_groups.keys()):
            group_findings = rule_groups[rule_id]

            artifacts = sorted(set(f.artifact_id for f in group_findings if f.artifact_id))
            files = sorted(set(f.file_path for f in group_findings if f.file_path))

            result.append(GroupedByRule(
                rule_id=rule_id,
                findings=tuple(sorted(group_findings, key=lambda x: x.finding_id)),
                affected_artifacts=tuple(artifacts),
                affected_files=tuple(files),
            ))

        return result

    def group_by_category(
        self,
        classifications: List[FindingClassification],
    ) -> List[GroupedByCategory]:
        """Group findings by category.

        Args:
            classifications: Classified findings

        Returns:
            List of GroupedByCategory (deterministic order)
        """
        # Group by category
        category_groups: Dict[FindingCategory, List[FindingClassification]] = {}
        for c in classifications:
            if c.category not in category_groups:
                category_groups[c.category] = []
            category_groups[c.category].append(c)

        # Build result in deterministic order
        result = []
        for category in sorted(category_groups.keys(), key=lambda x: x.value):
            group_findings = category_groups[category]

            # Calculate severity counts
            crit = sum(1 for f in group_findings if f.severity == ReviewSeverity.CRITICAL)
            err = sum(1 for f in group_findings if f.severity == ReviewSeverity.ERROR)
            warn = sum(1 for f in group_findings if f.severity == ReviewSeverity.WARNING)
            inf = sum(1 for f in group_findings if f.severity == ReviewSeverity.INFO)

            # Determine remediation (use highest severity from group)
            if crit > 0:
                remediation = RemediationCategory.BLOCK_RELEASE
            elif err > 0:
                remediation = RemediationCategory.FIX_GENERATED_CODE
            elif warn > 0:
                remediation = RemediationCategory.MANUAL_REVIEW
            else:
                remediation = RemediationCategory.NO_ACTION

            result.append(GroupedByCategory(
                category=category,
                findings=tuple(sorted(group_findings, key=lambda x: x.finding_id)),
                severity_counts=SeverityCounts(
                    total=len(group_findings),
                    critical=crit,
                    error=err,
                    warning=warn,
                    info=inf,
                ),
                remediation=remediation,
            ))

        return result


# ---------------------------------------------------------------------------
# E4.2.3 - Quality Gate Decision Engine
# ---------------------------------------------------------------------------

class QualityGateDecisionEngine:
    """Determines quality gate decisions from ReviewReports.

    Key properties:
    - Deterministic: Same input produces same output
    - No LLM calls for gate decision
    - Preserves full evidence chain
    - Provides artifact-level and project-level decisions
    """

    def __init__(self):
        """Initialize the decision engine."""
        self.classifier = FindingClassificationEngine()
        self.aggregator = FindingAggregator()

    def analyze(
        self,
        report: ReviewReport,
        gate_id: Optional[str] = None,
    ) -> QualityGateResult:
        """Analyze a ReviewReport and produce QualityGateResult.

        This is the main entry point for E4.2 analysis.

        Args:
            report: ReviewReport from E4.1
            gate_id: Optional gate analysis ID (generated if not provided)

        Returns:
            QualityGateResult with full analysis

        Raises:
            InvalidReportError: If report is invalid
            AnalysisError: If analysis fails
        """
        start_time = time.time()
        analysis_started = datetime.now(timezone.utc).isoformat()

        # Validate report
        if not report:
            raise InvalidReportError("ReviewReport cannot be None or empty")

        # Generate gate_id if not provided
        if not gate_id:
            gate_id = f"gate-{report.review_id[4:]}" if len(report.review_id) > 4 else f"gate-{report.report_id}"

        # Step 1: Classify findings
        findings_list = list(report.findings)
        classifications = self.classifier.classify_findings(findings_list)

        # Step 2: Aggregate findings
        aggregation = self.aggregator.aggregate(findings_list, classifications)

        # Step 3: Calculate decisions
        project_decision = self._calculate_project_decision(
            findings_list, classifications, aggregation
        )

        # Step 4: Determine remediation
        remediation, remediation_summary = determine_remediation_category(
            project_decision.decision, aggregation
        )

        # Step 5: Build evidence chain
        evidence = self._build_evidence_chain(report, findings_list, project_decision)

        # Step 6: Calculate hashes
        decision_hash = self._compute_decision_hash(
            gate_id, report, project_decision, remediation
        )

        analysis_completed = datetime.now(timezone.utc).isoformat()

        # Build decision reasons
        reasons = self._build_decision_reasons(project_decision, aggregation)

        # Build result with deterministic hash pre-computed
        result = QualityGateResult(
            gate_id=gate_id,
            review_id=report.review_id,
            report_id=report.report_id,
            mission_id=report.mission_id,
            workspace_id=report.workspace_id,
            plan_id=report.plan_id,
            decision=project_decision.decision,
            can_proceed=project_decision.can_proceed,
            decision_reasons=tuple(reasons),
            required_remediation=remediation,
            remediation_summary=tuple(remediation_summary),
            project_decision=project_decision,
            evidence=evidence,
            analysis_started=analysis_started,
            analysis_completed=analysis_completed,
            deterministic=True,
            deterministic_hash=decision_hash,
        )

        return result

    def _calculate_project_decision(
        self,
        findings: List[ReviewFinding],
        classifications: List[FindingClassification],
        aggregation: FindingAggregation,
    ) -> ProjectLevelDecision:
        """Calculate project-level decision.

        Args:
            findings: All findings
            classifications: Classified findings
            aggregation: Aggregated findings

        Returns:
            ProjectLevelDecision
        """
        # Calculate artifact-level decisions
        artifact_decisions = self._calculate_artifact_decisions(findings, classifications)

        # Determine overall project decision
        if not findings:
            overall_decision = QualityGateDecision.PASS
            can_proceed = True
        elif aggregation.severity_counts.critical > 0:
            overall_decision = QualityGateDecision.BLOCKED
            can_proceed = False
        elif aggregation.severity_counts.error > 0:
            overall_decision = QualityGateDecision.FAIL
            can_proceed = False
        elif aggregation.severity_counts.warning > 0 or aggregation.severity_counts.info > 0:
            overall_decision = QualityGateDecision.PASS_WITH_WARNINGS
            can_proceed = True
        else:
            overall_decision = QualityGateDecision.PASS
            can_proceed = True

        # Count artifacts by decision
        passing = sum(1 for d in artifact_decisions if d.decision == QualityGateDecision.PASS)
        with_warnings = sum(1 for d in artifact_decisions if d.decision == QualityGateDecision.PASS_WITH_WARNINGS)
        failing = sum(1 for d in artifact_decisions if d.decision == QualityGateDecision.FAIL)
        blocked = sum(1 for d in artifact_decisions if d.decision == QualityGateDecision.BLOCKED)

        # Get blocking artifacts and rules
        blocking_artifacts = tuple(sorted(set(
            d.artifact_id for d in artifact_decisions
            if d.decision in (QualityGateDecision.FAIL, QualityGateDecision.BLOCKED)
        )))

        blocking_rules = tuple(sorted(set(
            c.rule_id for c in classifications
            if c.is_blocking and c.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.ERROR)
        )))

        # Group findings
        by_artifact = self.aggregator.group_by_artifact(classifications, findings)
        by_file = self.aggregator.group_by_file(classifications)
        by_rule = self.aggregator.group_by_rule(classifications)
        by_category = self.aggregator.group_by_category(classifications)

        return ProjectLevelDecision(
            decision=overall_decision,
            can_proceed=can_proceed,
            total_artifacts=len(artifact_decisions),
            artifacts_passing=passing,
            artifacts_with_warnings=with_warnings,
            artifacts_failing=failing,
            artifacts_blocked=blocked,
            aggregation=aggregation,
            artifact_decisions=tuple(artifact_decisions),
            by_artifact=tuple(by_artifact),
            by_file=tuple(by_file),
            by_rule=tuple(by_rule),
            by_category=tuple(by_category),
            blocking_artifact_ids=blocking_artifacts,
            blocking_rule_ids=blocking_rules,
        )

    def _calculate_artifact_decisions(
        self,
        findings: List[ReviewFinding],
        classifications: List[FindingClassification],
    ) -> List[ArtifactLevelDecision]:
        """Calculate per-artifact decisions.

        Args:
            findings: All findings
            classifications: Classified findings

        Returns:
            List of ArtifactLevelDecision
        """
        # Group findings by artifact_id
        artifact_findings: Dict[str, List[Tuple[ReviewFinding, FindingClassification]]] = {}
        for f, c in zip(findings, classifications):
            artifact_id = c.artifact_id or f.artifact_execution_id.replace("aeu-", "art-") if f.artifact_execution_id else "unknown"
            if artifact_id not in artifact_findings:
                artifact_findings[artifact_id] = []
            artifact_findings[artifact_id].append((f, c))

        # Build decisions
        decisions = []
        for artifact_id in sorted(artifact_findings.keys()):
            pairs = artifact_findings[artifact_id]
            artifact_findings_list = [p[0] for p in pairs]
            artifact_classifications = [p[1] for p in pairs]

            # Get artifact execution ID from first finding
            execution_id = next(
                (f.artifact_execution_id for f in artifact_findings_list if f.artifact_execution_id),
                ""
            )

            # Calculate counts
            total = len(artifact_findings_list)
            blocking = sum(1 for f in artifact_findings_list if f.is_blocking)
            has_critical = any(f.severity == ReviewSeverity.CRITICAL for f in artifact_findings_list)
            has_error = any(f.severity == ReviewSeverity.ERROR for f in artifact_findings_list)
            has_warning = any(f.severity == ReviewSeverity.WARNING for f in artifact_findings_list)
            has_info = any(f.severity == ReviewSeverity.INFO for f in artifact_findings_list)

            # Determine top severity
            if has_critical:
                top_severity = ReviewSeverity.CRITICAL
            elif has_error:
                top_severity = ReviewSeverity.ERROR
            elif has_warning:
                top_severity = ReviewSeverity.WARNING
            else:
                top_severity = ReviewSeverity.INFO

            # Determine decision
            if has_critical:
                decision = QualityGateDecision.BLOCKED
                can_proceed = False
            elif has_error:
                decision = QualityGateDecision.FAIL
                can_proceed = False
            elif has_warning or has_info:
                decision = QualityGateDecision.PASS_WITH_WARNINGS
                can_proceed = True
            else:
                decision = QualityGateDecision.PASS
                can_proceed = True

            # Get affected files
            files = tuple(sorted(set(f.file_path for f in artifact_findings_list if f.file_path)))

            decisions.append(ArtifactLevelDecision(
                artifact_id=artifact_id,
                artifact_execution_id=execution_id,
                decision=decision,
                can_proceed=can_proceed,
                total_findings=total,
                blocking_findings=blocking,
                has_critical=has_critical,
                has_error=has_error,
                has_warning=has_warning,
                has_info=has_info,
                affected_files=files,
                top_severity=top_severity,
            ))

        return decisions

    def _build_evidence_chain(
        self,
        report: ReviewReport,
        findings: List[ReviewFinding],
        project_decision: ProjectLevelDecision,
    ) -> QualityGateEvidence:
        """Build evidence chain for traceability.

        Args:
            report: Original report
            findings: All findings
            project_decision: Calculated decision

        Returns:
            QualityGateEvidence with evidence chain
        """
        evidence_chain: List[EvidenceEntry] = []

        # Evidence 1: Review report reference
        evidence_chain.append(EvidenceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="ReviewReport",
            type="report_reference",
            content={
                "review_id": report.review_id,
                "report_id": report.report_id,
                "verdict": report.verdict.value,
            },
        ))

        # Evidence 2: Finding summary
        evidence_chain.append(EvidenceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="FindingAnalysis",
            type="finding_summary",
            content={
                "total_findings": len(findings),
                "critical": sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL),
                "error": sum(1 for f in findings if f.severity == ReviewSeverity.ERROR),
                "warning": sum(1 for f in findings if f.severity == ReviewSeverity.WARNING),
                "info": sum(1 for f in findings if f.severity == ReviewSeverity.INFO),
            },
        ))

        # Evidence 3: Decision result
        evidence_chain.append(EvidenceEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="QualityGateDecision",
            type="decision_result",
            content={
                "decision": project_decision.decision.value,
                "can_proceed": project_decision.can_proceed,
                "blocking_artifacts": list(project_decision.blocking_artifact_ids),
                "blocking_rules": list(project_decision.blocking_rule_ids),
            },
        ))

        # Compute evidence hash
        evidence_hash = compute_evidence_hash(
            report.review_id,
            report.report_id,
            tuple(findings),
        )

        return QualityGateEvidence(
            review_id=report.review_id,
            report_id=report.report_id,
            mission_id=report.mission_id,
            workspace_id=report.workspace_id,
            plan_id=report.plan_id,
            evidence_chain=tuple(evidence_chain),
            deterministic_hash=evidence_hash,
            decision_hash="",
        )

    def _compute_decision_hash(
        self,
        gate_id: str,
        report: ReviewReport,
        decision: ProjectLevelDecision,
        remediation: RemediationCategory,
    ) -> str:
        """Compute decision hash.

        Args:
            gate_id: Gate ID
            report: Original report
            decision: Project decision
            remediation: Remediation category

        Returns:
            SHA-256 hash string
        """
        hash_payload = {
            "gate_id": gate_id,
            "review_id": report.review_id,
            "report_id": report.report_id,
            "decision": decision.decision.value,
            "can_proceed": decision.can_proceed,
            "remediation": remediation.value,
            "total_findings": decision.aggregation.severity_counts.total,
        }
        json_bytes = __import__("json").dumps(hash_payload, sort_keys=True).encode("utf-8")
        return __import__("hashlib").sha256(json_bytes).hexdigest()

    def _build_decision_reasons(
        self,
        decision: ProjectLevelDecision,
        aggregation: FindingAggregation,
    ) -> List[str]:
        """Build human-readable decision reasons.

        Args:
            decision: Project decision
            aggregation: Finding aggregation

        Returns:
            List of reason strings
        """
        reasons = []

        if aggregation.severity_counts.critical > 0:
            reasons.append(
                f"{aggregation.severity_counts.critical} CRITICAL finding(s) detected"
            )

        if aggregation.severity_counts.error > 0:
            reasons.append(
                f"{aggregation.severity_counts.error} ERROR finding(s) detected"
            )

        if aggregation.severity_counts.warning > 0:
            reasons.append(
                f"{aggregation.severity_counts.warning} WARNING finding(s) detected"
            )

        if aggregation.severity_counts.info > 0:
            reasons.append(
                f"{aggregation.severity_counts.info} INFO finding(s) detected"
            )

        if aggregation.affected_artifact_count > 0:
            reasons.append(
                f"{aggregation.affected_artifact_count} artifact(s) affected"
            )

        if decision.blocking_artifact_ids:
            reasons.append(
                f"{len(decision.blocking_artifact_ids)} artifact(s) blocking progression"
            )

        # Add verdict translation
        if decision.decision == QualityGateDecision.PASS:
            reasons.append("Review verdict: All checks passed")
        elif decision.decision == QualityGateDecision.PASS_WITH_WARNINGS:
            reasons.append("Review verdict: Passed with warnings")
        elif decision.decision == QualityGateDecision.FAIL:
            reasons.append("Review verdict: Failed")
        elif decision.decision == QualityGateDecision.BLOCKED:
            reasons.append("Review verdict: Blocked")

        return reasons


# Alias for backwards compatibility
QualityGateEngine = QualityGateDecisionEngine


# ---------------------------------------------------------------------------
# E4.2.4 - Review History Integration
# ---------------------------------------------------------------------------

class QualityGateHistoryEntry:
    """Represents a quality gate analysis in review history.

    Extends E4.1 ReviewHistory with E4.2 gate analysis results.
    """

    @staticmethod
    def from_quality_gate_result(result: QualityGateResult) -> Dict:
        """Convert QualityGateResult to history entry format.

        Args:
            result: QualityGateResult to convert

        Returns:
            Dictionary suitable for history storage
        """
        return {
            "gate_id": result.gate_id,
            "review_id": result.review_id,
            "report_id": result.report_id,
            "mission_id": result.mission_id,
            "decision": result.decision.value,
            "can_proceed": result.can_proceed,
            "required_remediation": result.required_remediation.value,
            "total_findings": result.project_decision.aggregation.severity_counts.total,
            "critical_findings": result.project_decision.aggregation.severity_counts.critical,
            "error_findings": result.project_decision.aggregation.severity_counts.error,
            "warning_findings": result.project_decision.aggregation.severity_counts.warning,
            "blocking_artifacts": list(result.project_decision.blocking_artifact_ids),
            "analysis_started": result.analysis_started,
            "analysis_completed": result.analysis_completed,
            "deterministic_hash": result.deterministic_hash,
        }


# ---------------------------------------------------------------------------
# E4.2.5 - Frozen Architecture Guards
# ---------------------------------------------------------------------------

# Guards to ensure E4.2 does NOT violate frozen contracts
FROZEN_ARCHITECTURE_GUARDS = {
    "no_invocation_engine": "E4.2 must not create another InvocationEngine",
    "no_provider_registry": "E4.2 must not create another provider registry",
    "no_model_selector": "E4.2 must not create another model selector",
    "no_umal_bypass": "E4.2 must not bypass UMAL",
    "no_direct_provider_calls": "E4.2 must not directly call providers",
    "no_frozen_contract_modification": "E4.2 must not modify frozen E1 contracts",
    "no_self_healing": "E4.2 must not perform self-healing",
    "no_auto_regeneration": "E4.2 must not perform automatic regeneration",
    "no_finding_mutation": "E4.2 must not mutate ReviewFindings after creation",
}


def verify_frozen_architecture_compliance() -> Tuple[bool, List[str]]:
    """Verify E4.2 does not violate frozen architecture.

    Returns:
        Tuple of (is_compliant, list_of_violations)
    """
    violations = []

    # This function serves as documentation and can be extended
    # with actual runtime checks if needed

    # For now, just verify we import from correct locations
    try:
        # Verify E4.1 models are from correct module
        from runtime.contracts.e4_models import (
            ReviewFinding,
            ReviewReport,
            ReviewSeverity,
            ReviewVerdict,
        )
        # Verify we don't re-implement InvocationEngine
        import sys
        if "runtime.invocation.engine" in sys.modules:
            # It's okay to import, just not create new instances
            pass
    except ImportError as e:
        violations.append(f"Import error: {e}")

    return len(violations) == 0, violations
