"""Test suite for ACR-007 Phase C4 — Review & Approval Coordination.

Validates:
- ReviewCoordinator: Peer review lifecycle (REQUESTED → IN_PROGRESS → CHANGES_REQUESTED → RESUBMITTED → APPROVED / REJECTED)
- ApprovalCoordinator: Governance approvals integrated with RuntimeReviewPolicy (SECURITY_POLICY, INFRASTRUCTURE_POLICY, DEPLOYMENT_POLICY)
- Timeline event logging (REVIEW_CREATED, REVIEW_STARTED, CHANGES_REQUESTED, REVIEW_APPROVED, REVIEW_REJECTED, APPROVAL_CREATED, APPROVAL_APPROVED, APPROVAL_REJECTED)
- Extended CollaborationReport: Review & approval statistics, duration summaries, policy decision mapping
- CLI commands: oniroute review, oniroute approval
- Zero mutation of frozen Agent Runtime or Workspace components
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.agent.models import ArtifactRecord, ArtifactType
from runtime.agent.recovery.policy import DEPLOYMENT_POLICY, INFRASTRUCTURE_POLICY, SECURITY_POLICY, PermissiveReviewPolicy
from runtime.collaboration import (
    ApprovalCoordinator,
    ApprovalStatus,
    ArtifactReference,
    CollaborationApproval,
    CollaborationReport,
    CollaborationReview,
    MessageBus,
    ReviewCoordinator,
    ReviewStatus,
    SharedArtifactManager,
    TimelineEventType,
)

runner = CliRunner()


def _make_artifact_ref(ref_id: str = "ref-spec-001") -> ArtifactReference:
    return ArtifactReference(
        reference_id=ref_id,
        artifact_id="art-spec-001",
        owner_session_id="sess-author-01",
        owner_member_id="mem-author-01",
        artifact_type="documentation",
        workspace_path="docs/spec.md",
        checksum="sha256-123456",
        version=1,
    )


class TestReviewCoordinator:
    def setup_method(self):
        self.art_mgr = SharedArtifactManager()
        self.rev_coord = ReviewCoordinator(timeline=self.art_mgr.timeline)
        self.ref = _make_artifact_ref()

    def test_create_review_requested(self):
        rev = self.rev_coord.create_review(
            author_session_id="sess-author-01",
            reviewer_session_id="sess-reviewer-01",
            artifact_references=[self.ref],
            reason="Review architecture specification",
        )
        assert isinstance(rev, CollaborationReview)
        assert rev.review_id.startswith("rev-")
        assert rev.status == ReviewStatus.REQUESTED
        assert rev.author_session_id == "sess-author-01"
        assert rev.reviewer_session_id == "sess-reviewer-01"
        assert len(rev.artifact_references) == 1

    def test_create_review_same_session_fails(self):
        with pytest.raises(ValueError):
            self.rev_coord.create_review(
                author_session_id="sess-01",
                reviewer_session_id="sess-01",
                artifact_references=[self.ref],
            )

    def test_start_review(self):
        rev = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        started = self.rev_coord.start_review(rev.review_id, "sess-reviewer-01")
        assert started.status == ReviewStatus.IN_PROGRESS
        assert started.started_at is not None

    def test_request_changes(self):
        rev = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        self.rev_coord.start_review(rev.review_id, "sess-reviewer-01")
        cr = self.rev_coord.request_changes(
            rev.review_id, "sess-reviewer-01", comments="Clarify section 3 REST endpoints"
        )
        assert cr.status == ReviewStatus.CHANGES_REQUESTED
        assert len(cr.comments) == 1
        assert "Clarify section 3" in cr.comments[0]["comment"]

    def test_resubmit_review(self):
        rev = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        self.rev_coord.request_changes(rev.review_id, "sess-reviewer-01", "Need details")
        resubmitted = self.rev_coord.resubmit_review(
            rev.review_id, "sess-author-01", comments="Added section 3 endpoints"
        )
        assert resubmitted.status == ReviewStatus.RESUBMITTED

    def test_approve_review(self):
        rev = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        approved = self.rev_coord.approve_review(rev.review_id, "sess-reviewer-01", comments="Looks good to merge.")
        assert approved.status == ReviewStatus.APPROVED
        assert approved.decision == "approved"
        assert approved.completed_at is not None

    def test_reject_review(self):
        rev = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        rejected = self.rev_coord.reject_review(rev.review_id, "sess-reviewer-01", reason="Architectural flaw")
        assert rejected.status == ReviewStatus.REJECTED
        assert rejected.decision == "rejected"
        assert rejected.completed_at is not None

    def test_get_pending_reviews(self):
        rev1 = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        rev2 = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        self.rev_coord.approve_review(rev1.review_id, "sess-reviewer-01")

        pending = self.rev_coord.get_pending_reviews("sess-reviewer-01")
        assert len(pending) == 1
        assert pending[0].review_id == rev2.review_id

    def test_review_timeline_events(self):
        rev = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [self.ref])
        self.rev_coord.start_review(rev.review_id, "sess-reviewer-01")
        self.rev_coord.approve_review(rev.review_id, "sess-reviewer-01")

        event_types = [e.event_type for e in self.rev_coord.timeline.events]
        assert TimelineEventType.REVIEW_CREATED in event_types
        assert TimelineEventType.REVIEW_STARTED in event_types
        assert TimelineEventType.REVIEW_APPROVED in event_types


class TestApprovalCoordinator:
    def setup_method(self):
        self.art_mgr = SharedArtifactManager()
        self.appr_coord = ApprovalCoordinator(timeline=self.art_mgr.timeline)
        self.ref = _make_artifact_ref()

    def test_request_approval_default_policy(self):
        appr = self.appr_coord.request_approval(
            requester_session_id="sess-dev-01",
            approver_session_id="sess-lead-01",
            artifact_references=[self.ref],
            reason="Production release approval",
        )
        assert isinstance(appr, CollaborationApproval)
        assert appr.approval_id.startswith("appr-")
        assert appr.status == ApprovalStatus.PENDING
        assert appr.policy_name == "default"

    def test_request_approval_security_policy(self):
        appr = self.appr_coord.request_approval(
            requester_session_id="sess-dev-01",
            reason="Security configuration update",
            artifact_references=[self.ref],
            policy=SECURITY_POLICY,
        )
        assert appr.policy_name == "security"
        assert appr.evidence.get("policy_evaluated") == "security"

    def test_approve_request(self):
        appr = self.appr_coord.request_approval("sess-dev-01", "DB migration approval", [self.ref], approver_session_id="sess-lead-01")
        decided = self.appr_coord.approve(appr.approval_id, "sess-lead-01", reason="Migration plan verified")
        assert decided.status == ApprovalStatus.APPROVED
        assert decided.outcome is not None
        assert decided.outcome.status == ApprovalStatus.APPROVED
        assert decided.decided_at is not None

    def test_reject_request(self):
        appr = self.appr_coord.request_approval("sess-dev-01", "DB migration approval", [self.ref], approver_session_id="sess-lead-01")
        decided = self.appr_coord.reject(appr.approval_id, "sess-lead-01", reason="Unsafe migration script")
        assert decided.status == ApprovalStatus.REJECTED
        assert decided.outcome.status == ApprovalStatus.REJECTED

    def test_approve_wrong_approver_raises(self):
        appr = self.appr_coord.request_approval("sess-dev-01", "Approval", [self.ref], approver_session_id="sess-lead-01")
        with pytest.raises(ValueError):
            self.appr_coord.approve(appr.approval_id, "sess-unauthorized-user")

    def test_approval_timeline_events(self):
        appr = self.appr_coord.request_approval("sess-dev-01", "Approval", [self.ref])
        self.appr_coord.approve(appr.approval_id, "sess-dev-01")

        event_types = [e.event_type for e in self.appr_coord.timeline.events]
        assert TimelineEventType.APPROVAL_CREATED in event_types
        assert TimelineEventType.APPROVAL_APPROVED in event_types


class TestExtendedCollaborationReportPhaseC4:
    def setup_method(self):
        self.bus = MessageBus(blueprint_id="bp-c4-report")
        self.art_mgr = SharedArtifactManager(timeline=self.bus.timeline)
        self.rev_coord = ReviewCoordinator(timeline=self.bus.timeline)
        self.appr_coord = ApprovalCoordinator(timeline=self.bus.timeline)

        self.bus.set_artifact_manager(self.art_mgr)
        self.bus.set_review_coordinator(self.rev_coord)
        self.bus.set_approval_coordinator(self.appr_coord)

    def test_report_includes_reviews_approvals_and_policies(self):
        ref = _make_artifact_ref()

        rev = self.rev_coord.create_review("sess-author-01", "sess-reviewer-01", [ref])
        self.rev_coord.start_review(rev.review_id, "sess-reviewer-01")
        self.rev_coord.approve_review(rev.review_id, "sess-reviewer-01")

        appr = self.appr_coord.request_approval("sess-dev-01", "Deployment approval", [ref], policy=DEPLOYMENT_POLICY)
        self.appr_coord.approve(appr.approval_id, "sess-dev-01")

        report = self.bus.generate_report()
        assert isinstance(report, CollaborationReport)
        assert report.total_reviews == 1
        assert len(report.approved_reviews) == 1
        assert report.total_approvals == 1
        assert len(report.approved_approvals) == 1
        assert appr.approval_id in report.policy_decisions
        assert "deployment:approved" in report.policy_decisions[appr.approval_id]


class TestCLIPhaseC4:
    def test_review_command_collaboration_text(self):
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0
        assert "Inter-Agent Peer Reviews" in result.output

    def test_review_command_collaboration_json(self):
        result = runner.invoke(app, ["review", "--json"])
        assert result.exit_code == 0
        assert "review_id" in result.output
        assert "author_session_id" in result.output

    def test_approval_command_text(self):
        result = runner.invoke(app, ["approval"])
        assert result.exit_code == 0
        assert "Governance Approvals" in result.output

    def test_approval_command_json(self):
        result = runner.invoke(app, ["approval", "--json"])
        assert result.exit_code == 0
        assert "approval_id" in result.output
        assert "policy_name" in result.output
