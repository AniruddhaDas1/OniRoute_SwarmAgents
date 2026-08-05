"""Repair Planner Engine (Phase P5.E3).

Consumes QualityReport and produces deterministic RepairPlan objects for SelfHealingEngine.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from runtime.healing.exceptions import RepairPlanningError
from runtime.healing.models import RepairAction, RepairPlan
from runtime.review.models import QualityFinding, QualityReport, ReviewSeverity


class RepairPlanner:
    """Deterministic Repair Planner for Phase P5.E3."""

    def create_repair_plan(self, quality_report: QualityReport) -> RepairPlan:
        """Create deterministic RepairPlan from QualityReport.

        Args:
            quality_report: Immutable QualityReport input contract.

        Returns:
            RepairPlan: Immutable repair plan contract.
        """
        if not isinstance(quality_report, QualityReport):
            raise RepairPlanningError(
                f"RepairPlanner consumes ONLY QualityReport. "
                f"Received invalid input type: {type(quality_report).__name__}"
            )

        report_id = quality_report.report_id
        res_id = quality_report.engineering_result_id

        actions: List[RepairAction] = []
        target_files_set: Set[str] = set()
        action_counter = 1

        for finding in quality_report.findings:
            if finding.severity in (
                ReviewSeverity.CRITICAL.value,
                ReviewSeverity.HIGH.value,
                ReviewSeverity.MEDIUM.value,
            ):
                act_id = f"act-{action_counter:04d}"
                action_counter += 1

                priority = "P0_CRITICAL" if finding.severity == ReviewSeverity.CRITICAL.value else ("P1_HIGH" if finding.severity == ReviewSeverity.HIGH.value else "P2_MEDIUM")

                action = RepairAction(
                    action_id=act_id,
                    finding_id=finding.finding_id,
                    target_path=finding.target_path,
                    priority=priority,
                    required_changes=finding.recommended_fix,
                    dependencies=[],
                    execution_order=action_counter - 1,
                    acceptance_criteria=[
                        f"Verify finding '{finding.finding_id}' in '{finding.target_path}' is fully resolved.",
                        "Verify code generation complies with safety boundaries.",
                    ],
                )
                actions.append(action)
                target_files_set.add(finding.target_path)

        timestamp_iso = datetime.now(timezone.utc).isoformat()
        plan_id = f"rprplan-{abs(hash(f'{report_id}-{res_id}-{timestamp_iso}')) % 1000000:06d}"
        target_files = sorted(list(target_files_set))

        plan_hash = self._compute_plan_hash(
            plan_id=plan_id,
            quality_report_id=report_id,
            engineering_result_id=res_id,
            actions=actions,
            target_files=target_files,
        )

        return RepairPlan(
            plan_id=plan_id,
            quality_report_id=report_id,
            engineering_result_id=res_id,
            actions=actions,
            target_files=target_files,
            timestamp=timestamp_iso,
            plan_hash=plan_hash,
        )

    def _compute_plan_hash(
        self,
        plan_id: str,
        quality_report_id: str,
        engineering_result_id: str,
        actions: List[RepairAction],
        target_files: List[str],
    ) -> str:
        """Compute SHA-256 hash of repair plan payload."""
        hash_payload = {
            "plan_id": plan_id,
            "quality_report_id": quality_report_id,
            "engineering_result_id": engineering_result_id,
            "actions": [a.model_dump(mode="json") for a in actions],
            "target_files": target_files,
        }
        json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(json_bytes).hexdigest()
