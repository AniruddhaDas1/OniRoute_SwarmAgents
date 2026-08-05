"""Approval Coordinator for Engineering Collaboration (ACR-007 Phase C4).

Implements ApprovalCoordinatorContract for governance and human approval workflows.
Integrates with the frozen RuntimeReviewPolicy engine (SECURITY_POLICY, INFRASTRUCTURE_POLICY,
DEPLOYMENT_POLICY, DefaultReviewPolicy) to evaluate approval requirements without hardcoding logic.

Every transition is recorded on the CollaborationTimeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from runtime.agent.recovery.policy import DefaultReviewPolicy, ReviewPolicy
from .contracts import ApprovalCoordinatorContract
from .models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    ArtifactReference,
    CollaborationApproval,
    TimelineEventType,
)
from .timeline import CollaborationTimeline


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApprovalCoordinator(ApprovalCoordinatorContract):
    """Concrete implementation of ApprovalCoordinatorContract.

    Coordinates governance approval requests, integrates with RuntimeReviewPolicy,
    and manages approval decisions.
    """

    def __init__(
        self,
        timeline: CollaborationTimeline | None = None,
        default_policy: ReviewPolicy | None = None,
    ) -> None:
        self._timeline = timeline or CollaborationTimeline()
        self._default_policy: ReviewPolicy = default_policy or DefaultReviewPolicy()

        self._approvals: dict[str, CollaborationApproval] = {}
        """approval_id → CollaborationApproval"""

        self._approver_approvals: dict[str, list[str]] = {}
        """approver_session_id → list of approval_ids"""

        self._requester_approvals: dict[str, list[str]] = {}
        """requester_session_id → list of approval_ids"""

    @property
    def timeline(self) -> CollaborationTimeline:
        return self._timeline

    @property
    def total_approvals(self) -> int:
        return len(self._approvals)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_approval(
        self,
        requester_session_id: str,
        reason: str,
        artifact_references: list[ArtifactReference] | None = None,
        approver_session_id: str | None = None,
        conversation_id: str = "",
        thread_id: str = "",
        policy: ReviewPolicy | None = None,
        evidence: dict | None = None,
    ) -> CollaborationApproval:
        """Create a new CollaborationApproval governed by a RuntimeReviewPolicy."""
        if not requester_session_id:
            raise ValueError("Requester session ID must be non-empty.")

        active_policy = policy or self._default_policy
        if hasattr(active_policy, "policy_name") and callable(active_policy.policy_name):
            policy_name = active_policy.policy_name()
        else:
            policy_name = getattr(active_policy, "name", active_policy.__class__.__name__)

        refs = list(artifact_references or [])
        evidence_dict = dict(evidence or {})
        evidence_dict["policy_evaluated"] = policy_name

        approval_id = f"appr-{uuid.uuid4().hex[:8]}"

        # Evaluate policy requirement using ArtifactRecord
        from runtime.agent.models import ArtifactRecord, ArtifactType

        if refs:
            first_ref = refs[0]
            art_type_str = first_ref.artifact_type.lower()
            try:
                atype = ArtifactType(art_type_str)
            except ValueError:
                atype = ArtifactType.CUSTOM

            eval_artifact = ArtifactRecord(
                artifact_id=first_ref.artifact_id,
                artifact_type=atype,
                owner_session_id=first_ref.owner_session_id,
                owner_member_id=first_ref.owner_member_id,
                capability_id="cap-policy-eval",
                name=first_ref.artifact_id,
                references=[first_ref.workspace_path] if first_ref.workspace_path else [],
            )
        else:
            eval_artifact = ArtifactRecord(
                artifact_id=f"art-approval-{approval_id}",
                artifact_type=ArtifactType.DOCUMENTATION,
                owner_session_id=requester_session_id,
                owner_member_id="mem-unknown",
                capability_id="cap-policy-eval",
                name=reason,
            )

        requires_review = active_policy.requires_review(eval_artifact)
        evidence_dict["requires_human_review"] = requires_review

        approval = CollaborationApproval(
            approval_id=approval_id,
            conversation_id=conversation_id,
            thread_id=thread_id,
            requester_session_id=requester_session_id,
            approver_session_id=approver_session_id,
            artifact_references=refs,
            reason=reason,
            evidence=evidence_dict,
            policy_name=policy_name,
            status=ApprovalStatus.PENDING,
            outcome=None,
            requested_at=_utcnow(),
        )

        self._approvals[approval_id] = approval
        self._requester_approvals.setdefault(requester_session_id, []).append(approval_id)
        if approver_session_id:
            self._approver_approvals.setdefault(approver_session_id, []).append(approval_id)

        self._timeline.record_event(
            event_type=TimelineEventType.APPROVAL_CREATED,
            session_id=requester_session_id,
            description=(
                f"Approval request created ({approval_id}) under policy '{policy_name}': "
                f"requester='{requester_session_id}', approver='{approver_session_id or 'ANY'}'"
            ),
            payload={
                "approval_id": approval_id,
                "requester_session_id": requester_session_id,
                "approver_session_id": approver_session_id,
                "policy_name": policy_name,
                "reason": reason,
                "requires_review": requires_review,
            },
        )
        return approval

    def approve(
        self,
        approval_id: str,
        actor_session_id: str,
        reason: str = "Approved by governance",
        evidence: dict | None = None,
    ) -> CollaborationApproval:
        """Approve a pending approval request."""
        return self.submit_decision(
            approval_id=approval_id,
            status=ApprovalStatus.APPROVED,
            actor_session_id=actor_session_id,
            reason=reason,
            evidence=evidence,
        )

    def reject(
        self,
        approval_id: str,
        actor_session_id: str,
        reason: str = "Rejected by governance",
        evidence: dict | None = None,
    ) -> CollaborationApproval:
        """Reject a pending approval request."""
        return self.submit_decision(
            approval_id=approval_id,
            status=ApprovalStatus.REJECTED,
            actor_session_id=actor_session_id,
            reason=reason,
            evidence=evidence,
        )

    def request_changes(
        self,
        approval_id: str,
        actor_session_id: str,
        reason: str = "Changes requested",
        evidence: dict | None = None,
    ) -> CollaborationApproval:
        """Request changes on a pending approval request."""
        return self.submit_decision(
            approval_id=approval_id,
            status=ApprovalStatus.CHANGES_REQUESTED,
            actor_session_id=actor_session_id,
            reason=reason,
            evidence=evidence,
        )

    def submit_decision(
        self,
        approval_id: str,
        status: ApprovalStatus,
        actor_session_id: str,
        reason: str,
        evidence: dict | None = None,
    ) -> CollaborationApproval:
        """Submit an ApprovalDecision for a pending approval request (implements ApprovalCoordinatorContract)."""
        approval = self.get_approval(approval_id)
        if approval.status in (ApprovalStatus.APPROVED, ApprovalStatus.REJECTED):
            raise ValueError(f"Approval '{approval_id}' is already finalized ({approval.status.value}).")

        # Validate approver if explicitly specified
        if approval.approver_session_id and approval.approver_session_id != actor_session_id:
            raise ValueError(
                f"Actor '{actor_session_id}' is not the designated approver for approval '{approval_id}'."
            )

        dec_id = f"dec-{uuid.uuid4().hex[:8]}"
        decision = ApprovalDecision(
            decision_id=dec_id,
            approval_id=approval_id,
            status=status,
            actor_session_id=actor_session_id,
            reason=reason,
            evidence=evidence or {},
            decided_at=_utcnow(),
        )

        decided_at = _utcnow()
        merged_evidence = dict(approval.evidence)
        if evidence:
            merged_evidence.update(evidence)

        updated = CollaborationApproval(
            approval_id=approval.approval_id,
            conversation_id=approval.conversation_id,
            thread_id=approval.thread_id,
            requester_session_id=approval.requester_session_id,
            approver_session_id=approval.approver_session_id,
            artifact_references=approval.artifact_references,
            reason=approval.reason,
            evidence=merged_evidence,
            policy_name=approval.policy_name,
            status=status,
            outcome=decision,
            requested_at=approval.requested_at,
            decided_at=decided_at,
        )
        self._approvals[approval_id] = updated

        evt_type = (
            TimelineEventType.APPROVAL_APPROVED
            if status == ApprovalStatus.APPROVED
            else TimelineEventType.APPROVAL_REJECTED
        )

        self._timeline.record_event(
            event_type=evt_type,
            session_id=actor_session_id,
            description=f"Approval '{approval_id}' {status.value.upper()} by '{actor_session_id}': {reason}",
            payload={
                "approval_id": approval_id,
                "actor_session_id": actor_session_id,
                "status": status.value,
                "reason": reason,
                "decided_at": decided_at,
            },
        )
        return updated

    def get_approval(self, approval_id: str) -> CollaborationApproval:
        """Retrieve an ApprovalRequest/CollaborationApproval by ID (implements ApprovalCoordinatorContract)."""
        if approval_id not in self._approvals:
            raise KeyError(f"Approval '{approval_id}' not found.")
        return self._approvals[approval_id]

    def get_pending_approvals(self, approver_session_id: str | None = None) -> list[CollaborationApproval]:
        """Retrieve pending approval requests (optionally filtered by approver session)."""
        if approver_session_id:
            appr_ids = self._approver_approvals.get(approver_session_id, [])
            return [
                self._approvals[aid]
                for aid in appr_ids
                if aid in self._approvals and self._approvals[aid].status == ApprovalStatus.PENDING
            ]
        return [appr for appr in self._approvals.values() if appr.status == ApprovalStatus.PENDING]

    def get_all_approvals(self) -> tuple[CollaborationApproval, ...]:
        """Return a tuple of all recorded approvals."""
        return tuple(self._approvals.values())
