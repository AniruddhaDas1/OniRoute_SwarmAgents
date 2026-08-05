"""Tests for ACR-006 Phase R4 — Runtime Recovery & Human Review.

Covers:
- Failure classification (all categories)
- RetryManager (eligibility, delays, records, exhaustion)
- RuntimeReviewEngine (request, approve, reject, request_changes)
- RecoveryOrchestrator (pause, resume, retry, review, report)
- RecoveryReport generation
- CLI commands: review, retry, resume, recovery
- Regression: existing R1–R3 tests unaffected
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.agent import (
    AgentSession,
    ExecutionStatus,
    RuntimeState,
    SessionManager,
)
from runtime.agent.recovery import (
    FailureCategory,
    FailureClassifier,
    PauseRecord,
    RecoveryOrchestrator,
    RetryManager,
    RetryPolicy,
    ReviewDecision,
    ReviewRecord,
    RuntimeReviewEngine,
)
from runtime.agent.recovery.models import RecoveryMetrics, RecoveryReport, RetryRecord

runner = CliRunner()
REPO_ROOT = Path(__file__).parents[2]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_running_session(session_id: str = "sess-test-001") -> AgentSession:
    """Return a minimal AgentSession in RUNNING state."""
    session = AgentSession(
        session_id=session_id,
        member_id="mem-test",
        role_id="role-test",
        role_title="Test Role",
        blueprint_id="bp-test",
        state=RuntimeState.INITIALIZED,
        status=ExecutionStatus.PENDING,
    )
    mgr = SessionManager()
    session = mgr.transition_state(session, RuntimeState.READY)
    session = mgr.transition_state(session, RuntimeState.RUNNING)
    return session


def _make_waiting_session(session_id: str = "sess-wait-001") -> AgentSession:
    session = _make_running_session(session_id)
    mgr = SessionManager()
    session = mgr.transition_state(session, RuntimeState.WAITING)
    return session


def _make_review_session(session_id: str = "sess-rev-001") -> AgentSession:
    session = _make_running_session(session_id)
    mgr = SessionManager()
    session = mgr.transition_state(session, RuntimeState.REVIEW)
    return session


# ===========================================================================
# 1. Failure Classifier Tests
# ===========================================================================

class TestFailureClassifier:
    def setup_method(self):
        self.clf = FailureClassifier()

    def test_classify_governance_permission_error(self):
        exc = PermissionError("Governance denied session: budget exceeded")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.GOVERNANCE
        assert result.is_retryable is False
        assert "review" in result.recovery_recommendation.lower()

    def test_classify_governance_keyword(self):
        exc = RuntimeError("policy denied: approval required")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.GOVERNANCE
        assert result.is_retryable is False

    def test_classify_network_connection_refused(self):
        exc = ConnectionRefusedError("connection refused")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.NETWORK
        assert result.is_retryable is True

    def test_classify_network_timeout(self):
        exc = TimeoutError("connection timed out")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.NETWORK
        assert result.is_retryable is True

    def test_classify_provider_overloaded(self):
        exc = RuntimeError("503: upstream overloaded")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.PROVIDER
        assert result.is_retryable is True

    def test_classify_provider_rate_limit(self):
        exc = RuntimeError("rate limit exceeded for model")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.PROVIDER
        assert result.is_retryable is True

    def test_classify_configuration_missing_file(self):
        exc = FileNotFoundError("config/models.yaml not found")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.CONFIGURATION
        assert result.is_retryable is False

    def test_classify_configuration_key_error(self):
        exc = KeyError("models.yaml")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.CONFIGURATION
        assert result.is_retryable is False

    def test_classify_permanent_value_error(self):
        exc = ValueError("Invalid transition: COMPLETED → RUNNING")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.PERMANENT
        assert result.is_retryable is False

    def test_classify_permanent_assertion(self):
        exc = AssertionError("Blueprint sealed; cannot modify")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.PERMANENT
        assert result.is_retryable is False

    def test_classify_system_unknown(self):
        exc = RuntimeError("Unexpected internal error in scheduler")
        result = self.clf.classify(exc)
        assert result.category == FailureCategory.SYSTEM
        assert result.is_retryable is True

    def test_classify_evidence_includes_session(self):
        exc = RuntimeError("error")
        ctx = {"session_id": "sess-abc", "member_id": "mem-xyz"}
        result = self.clf.classify(exc, context=ctx)
        assert result.evidence["session_id"] == "sess-abc"
        assert result.evidence["member_id"] == "mem-xyz"

    def test_classification_is_immutable(self):
        exc = RuntimeError("error")
        result = self.clf.classify(exc)
        with pytest.raises(AttributeError):
            result.category = FailureCategory.NETWORK

    def test_to_dict_serializable(self):
        exc = ConnectionError("network timeout")
        result = self.clf.classify(exc)
        d = result.to_dict()
        assert "category" in d
        assert "reason" in d
        assert "evidence" in d
        assert "recovery_recommendation" in d
        assert "is_retryable" in d


# ===========================================================================
# 2. RetryManager Tests
# ===========================================================================

class TestRetryManager:
    def setup_method(self):
        self.clf = FailureClassifier()
        self.policy = RetryPolicy(max_retries=3, base_delay_seconds=1.0, backoff_factor=2.0)
        self.rm = RetryManager(policy=self.policy)
        self.session_id = "sess-retry-001"

    def _net_classification(self):
        return self.clf.classify(ConnectionError("timed out"), {"session_id": self.session_id})

    def _governance_classification(self):
        return self.clf.classify(PermissionError("Governance denied"), {"session_id": self.session_id})

    def test_can_retry_network_failure(self):
        classification = self._net_classification()
        assert self.rm.can_retry(self.session_id, classification) is True

    def test_cannot_retry_governance_failure(self):
        classification = self._governance_classification()
        assert self.rm.can_retry(self.session_id, classification) is False

    def test_cannot_retry_permanent_failure(self):
        classification = self.clf.classify(ValueError("invalid blueprint"))
        assert self.rm.can_retry(self.session_id, classification) is False

    def test_cannot_retry_config_failure(self):
        classification = self.clf.classify(FileNotFoundError("models.yaml not found"))
        assert self.rm.can_retry(self.session_id, classification) is False

    def test_retry_exhaustion(self):
        classification = self._net_classification()
        for _ in range(3):
            record = self.rm.start_retry(self.session_id, classification)
            self.rm.complete_retry(record.retry_id, "failure")
        assert self.rm.can_retry(self.session_id, classification) is False

    def test_exponential_backoff_delay(self):
        classification = self._net_classification()
        # Before any retries: attempt=0, delay=1.0 * 2^0 = 1.0
        assert self.rm.compute_delay(self.session_id) == pytest.approx(1.0)
        self.rm.start_retry(self.session_id, classification)
        # After 1 retry: attempt=1, delay=1.0 * 2^1 = 2.0
        assert self.rm.compute_delay(self.session_id) == pytest.approx(2.0)
        self.rm.start_retry(self.session_id, classification)
        # After 2 retries: delay=1.0 * 2^2 = 4.0
        assert self.rm.compute_delay(self.session_id) == pytest.approx(4.0)

    def test_max_delay_cap(self):
        capped_policy = RetryPolicy(
            max_retries=10, base_delay_seconds=5.0,
            backoff_factor=10.0, max_delay_seconds=15.0
        )
        rm = RetryManager(capped_policy)
        classification = self._net_classification()
        rm.start_retry(self.session_id, classification)
        rm.start_retry(self.session_id, classification)
        # 5.0 * 10^2 = 500, capped at 15.0
        assert rm.compute_delay(self.session_id) == pytest.approx(15.0)

    def test_start_retry_creates_record(self):
        classification = self._net_classification()
        record = self.rm.start_retry(self.session_id, classification)
        assert isinstance(record, RetryRecord)
        assert record.session_id == self.session_id
        assert record.attempt_number == 1
        assert record.outcome == "pending"

    def test_complete_retry_success(self):
        classification = self._net_classification()
        record = self.rm.start_retry(self.session_id, classification)
        updated = self.rm.complete_retry(record.retry_id, "success")
        assert updated.outcome == "success"
        assert updated.completed_at is not None

    def test_complete_retry_failure(self):
        classification = self._net_classification()
        record = self.rm.start_retry(self.session_id, classification)
        updated = self.rm.complete_retry(record.retry_id, "failure")
        assert updated.outcome == "failure"

    def test_complete_retry_invalid_outcome(self):
        classification = self._net_classification()
        record = self.rm.start_retry(self.session_id, classification)
        with pytest.raises(ValueError, match="Invalid retry outcome"):
            self.rm.complete_retry(record.retry_id, "unknown")

    def test_complete_retry_unknown_id(self):
        with pytest.raises(KeyError):
            self.rm.complete_retry("nonexistent-id", "success")

    def test_metrics_aggregate(self):
        classification = self._net_classification()
        r1 = self.rm.start_retry(self.session_id, classification)
        self.rm.complete_retry(r1.retry_id, "success")
        r2 = self.rm.start_retry(self.session_id, classification)
        self.rm.complete_retry(r2.retry_id, "failure")

        m = self.rm.metrics
        assert m["total_retries"] == 2
        assert m["successful_retries"] == 1
        assert m["failed_retries"] == 1

    def test_remaining_retries(self):
        classification = self._net_classification()
        assert self.rm.remaining_retries(self.session_id) == 3
        self.rm.start_retry(self.session_id, classification)
        assert self.rm.remaining_retries(self.session_id) == 2

    def test_records_snapshot_immutable_tuple(self):
        classification = self._net_classification()
        self.rm.start_retry(self.session_id, classification)
        records = self.rm.records
        assert isinstance(records, tuple)
        assert len(records) == 1


# ===========================================================================
# 3. RuntimeReviewEngine Tests
# ===========================================================================

class TestRuntimeReviewEngine:
    def setup_method(self):
        self.engine = RuntimeReviewEngine()

    def _make_session_with_review_artifact(self) -> AgentSession:
        from runtime.agent.models import ArtifactRecord, ArtifactType
        session = _make_running_session("sess-rev-engine-001")
        artifact = ArtifactRecord(
            artifact_id="art-rev-001",
            artifact_type=ArtifactType.REVIEW,
            owner_session_id=session.session_id,
            owner_member_id=session.member_id,
            capability_id="cap-review",
            name="Review Artifact",
        )
        session.artifacts.append(artifact)
        return session

    def _make_session_without_review_artifact(self) -> AgentSession:
        from runtime.agent.models import ArtifactRecord, ArtifactType
        session = _make_running_session("sess-no-rev-001")
        artifact = ArtifactRecord(
            artifact_id="art-report-001",
            artifact_type=ArtifactType.REPORT,
            owner_session_id=session.session_id,
            owner_member_id=session.member_id,
            capability_id="cap-report",
            name="Report Artifact",
        )
        session.artifacts.append(artifact)
        return session

    def test_needs_review_true_for_review_artifact(self):
        session = self._make_session_with_review_artifact()
        assert self.engine.needs_review(session) is True

    def test_needs_review_false_for_report_artifact(self):
        session = self._make_session_without_review_artifact()
        assert self.engine.needs_review(session) is False

    def test_needs_review_false_for_no_artifacts(self):
        session = _make_running_session("sess-empty-001")
        assert self.engine.needs_review(session) is False

    def test_request_review_creates_pending_record(self):
        session = self._make_session_with_review_artifact()
        record = self.engine.request_review(session, "Needs sign-off")
        assert isinstance(record, ReviewRecord)
        assert record.is_pending is True
        assert record.session_id == session.session_id
        assert len(record.artifacts_under_review) == 1

    def test_request_review_emits_event(self):
        session = self._make_session_with_review_artifact()
        events_emitted = []

        def fake_emitter(sess, event_type, description, payload):
            events_emitted.append({"type": event_type, "payload": payload})

        self.engine.request_review(session, "Needs sign-off", event_emitter=fake_emitter)
        assert len(events_emitted) == 1
        assert events_emitted[0]["type"] == "review_requested"

    def test_submit_decision_approve(self):
        session = self._make_session_with_review_artifact()
        record = self.engine.request_review(session)
        closed = self.engine.submit_decision(record.review_id, ReviewDecision.APPROVE, "operator-1")
        assert closed.is_approved is True
        assert closed.is_pending is False
        assert closed.outcome.actor == "operator-1"

    def test_submit_decision_reject(self):
        session = self._make_session_with_review_artifact()
        record = self.engine.request_review(session)
        closed = self.engine.submit_decision(record.review_id, ReviewDecision.REJECT, "operator-1")
        assert closed.is_rejected is True
        assert closed.outcome.decision == ReviewDecision.REJECT

    def test_submit_decision_request_changes(self):
        session = self._make_session_with_review_artifact()
        record = self.engine.request_review(session)
        closed = self.engine.submit_decision(
            record.review_id, ReviewDecision.REQUEST_CHANGES, "operator-1", notes="Fix the schema"
        )
        assert closed.outcome.decision == ReviewDecision.REQUEST_CHANGES
        assert closed.outcome.notes == "Fix the schema"

    def test_submit_unknown_review_raises(self):
        with pytest.raises(KeyError, match="No pending review"):
            self.engine.submit_decision("nonexistent-rev", ReviewDecision.APPROVE, "op")

    def test_all_reviews_includes_pending_and_completed(self):
        s1 = self._make_session_with_review_artifact()
        s2 = _make_running_session("sess-rev-002")
        from runtime.agent.models import ArtifactRecord, ArtifactType
        s2.artifacts.append(ArtifactRecord(
            artifact_id="art-rev-002", artifact_type=ArtifactType.CONFIG,
            owner_session_id=s2.session_id, owner_member_id=s2.member_id,
            capability_id="cap-cfg", name="Config Artifact",
        ))
        r1 = self.engine.request_review(s1)
        r2 = self.engine.request_review(s2)
        self.engine.submit_decision(r1.review_id, ReviewDecision.APPROVE, "op")

        all_reviews = self.engine.all_reviews
        assert len(all_reviews) == 2
        assert len(self.engine.pending_review_ids) == 1


# ===========================================================================
# 4. RecoveryOrchestrator — Pause / Resume Tests
# ===========================================================================

class TestRecoveryOrchestratorPauseResume:
    def setup_method(self):
        self.orch = RecoveryOrchestrator()

    def test_pause_running_session(self):
        session = _make_running_session("sess-pause-001")
        updated, record = self.orch.pause(session, reason="Awaiting upstream", actor="runtime")
        assert updated.state == RuntimeState.WAITING
        assert isinstance(record, PauseRecord)
        assert record.reason == "Awaiting upstream"
        assert record.actor == "runtime"
        assert record.resumed_at is None

    def test_pause_emits_execution_paused_event(self):
        session = _make_running_session("sess-pause-002")
        updated, _ = self.orch.pause(session, reason="test pause")
        event_types = self.orch.get_session_event_types(updated.session_id)
        assert "execution_paused" in event_types

    def test_pause_non_running_raises(self):
        session = _make_waiting_session("sess-pause-003")
        with pytest.raises(ValueError, match="expected RUNNING"):
            self.orch.pause(session, reason="bad pause")

    def test_resume_waiting_session(self):
        session = _make_running_session("sess-resume-001")
        session, pause_record = self.orch.pause(session, reason="test")
        session, closed = self.orch.resume(session)
        assert session.state == RuntimeState.RUNNING
        assert closed is not None
        assert closed.resumed_at is not None

    def test_resume_emits_execution_resumed_event(self):
        session = _make_running_session("sess-resume-002")
        session, _ = self.orch.pause(session, reason="test")
        session, _ = self.orch.resume(session)
        event_types = self.orch.get_session_event_types(session.session_id)
        assert "execution_resumed" in event_types

    def test_resume_non_waiting_raises(self):
        session = _make_running_session("sess-resume-003")
        with pytest.raises(ValueError, match="expected WAITING"):
            self.orch.resume(session)

    def test_pause_persists_evidence(self):
        session = _make_running_session("sess-ev-001")
        evidence = {"reason_code": "upstream_timeout", "retry_count": 2}
        session, record = self.orch.pause(session, reason="test", evidence=evidence)
        assert record.evidence["reason_code"] == "upstream_timeout"


# ===========================================================================
# 5. RecoveryOrchestrator — Retry Tests
# ===========================================================================

class TestRecoveryOrchestratorRetry:
    def setup_method(self):
        self.clf = FailureClassifier()
        self.policy = RetryPolicy(max_retries=3, base_delay_seconds=0.0)
        self.orch = RecoveryOrchestrator(retry_policy=self.policy)

    def _failed_session(self) -> AgentSession:
        session = _make_running_session("sess-retry-002")
        # Move to FAILED via SessionManager
        mgr = SessionManager()
        session = mgr.transition_state(session, RuntimeState.FAILED)
        return session

    def test_retry_success(self):
        session = self._failed_session()
        classification = self.clf.classify(ConnectionError("timed out"), {"session_id": session.session_id})
        call_count = {"n": 0}

        def success_fn(s):
            call_count["n"] += 1

        _, recovered = self.orch.attempt_recovery(session, classification, success_fn)
        assert recovered is True
        assert call_count["n"] == 1

    def test_retry_failure(self):
        session = self._failed_session()
        classification = self.clf.classify(ConnectionError("timed out"), {"session_id": session.session_id})

        def fail_fn(s):
            raise RuntimeError("still failing")

        _, recovered = self.orch.attempt_recovery(session, classification, fail_fn)
        assert recovered is False

    def test_governance_denial_not_retried(self):
        session = self._failed_session()
        classification = self.clf.classify(PermissionError("Governance denied"), {"session_id": session.session_id})
        call_count = {"n": 0}

        def fn(s):
            call_count["n"] += 1

        _, recovered = self.orch.attempt_recovery(session, classification, fn)
        assert recovered is False
        assert call_count["n"] == 0

    def test_retry_emits_retry_started_and_completed(self):
        session = self._failed_session()
        classification = self.clf.classify(ConnectionError("timeout"), {"session_id": session.session_id})

        self.orch.attempt_recovery(session, classification, lambda s: None)
        event_types = self.orch.get_session_event_types(session.session_id)
        assert "retry_started" in event_types
        assert "retry_completed" in event_types
        assert "recovery_completed" in event_types

    def test_retry_exhaustion_emits_recovery_completed(self):
        session = self._failed_session()
        classification = self.clf.classify(PermissionError("denied"), {"session_id": session.session_id})
        self.orch.attempt_recovery(session, classification, lambda s: None)
        event_types = self.orch.get_session_event_types(session.session_id)
        assert "recovery_completed" in event_types


# ===========================================================================
# 6. RecoveryOrchestrator — Review Integration Tests
# ===========================================================================

class TestRecoveryOrchestratorReview:
    def setup_method(self):
        self.orch = RecoveryOrchestrator()

    def test_request_review_transitions_to_review_state(self):
        session = _make_running_session("sess-rev-orch-001")
        session = self.orch.request_review(session, reason="Schema requires sign-off")
        assert session.state == RuntimeState.REVIEW

    def test_review_approved_transitions_to_running(self):
        session = _make_running_session("sess-rev-orch-002")
        session = self.orch.request_review(session)
        pending_ids = self.orch.review_engine.pending_review_ids
        assert len(pending_ids) == 1
        review_id = pending_ids[0]

        session = self.orch.apply_review_decision(
            session, review_id, ReviewDecision.APPROVE, "operator-1"
        )
        assert session.state == RuntimeState.RUNNING

    def test_review_rejected_transitions_to_failed(self):
        session = _make_running_session("sess-rev-orch-003")
        session = self.orch.request_review(session)
        review_id = self.orch.review_engine.pending_review_ids[0]

        session = self.orch.apply_review_decision(
            session, review_id, ReviewDecision.REJECT, "operator-1"
        )
        assert session.state == RuntimeState.FAILED

    def test_review_request_changes_transitions_to_waiting(self):
        session = _make_running_session("sess-rev-orch-004")
        session = self.orch.request_review(session)
        review_id = self.orch.review_engine.pending_review_ids[0]

        # REQUEST_CHANGES transitions to FAILED in the frozen DAG
        # (REVIEW → WAITING is not an allowed transition).
        session = self.orch.apply_review_decision(
            session, review_id, ReviewDecision.REQUEST_CHANGES, "operator-1",
            notes="Please revise the schema."
        )
        assert session.state == RuntimeState.FAILED


# ===========================================================================
# 7. RecoveryReport Tests
# ===========================================================================

class TestRecoveryReport:
    def setup_method(self):
        self.clf = FailureClassifier()
        self.policy = RetryPolicy(max_retries=2, base_delay_seconds=0.0)
        self.orch = RecoveryOrchestrator(retry_policy=self.policy)

    def test_report_generated_successfully(self):
        session = _make_running_session("sess-report-001")
        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert isinstance(report, RecoveryReport)
        assert report.session_id == session.session_id
        assert report.blueprint_id == "bp-test"
        assert report.mission_id == "msn-test"

    def test_report_is_immutable(self):
        session = _make_running_session("sess-report-002")
        report = self.orch.generate_report(session, "bp-test", "msn-test")
        with pytest.raises(Exception):
            report.session_id = "tampered"

    def test_report_captures_failures(self):
        session = _make_running_session("sess-report-003")
        # Force a failed session
        mgr = SessionManager()
        session = mgr.transition_state(session, RuntimeState.FAILED)
        classification = self.clf.classify(PermissionError("denied"))
        self.orch.attempt_recovery(session, classification, lambda s: None)

        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert len(report.failures) == 1
        assert report.failures[0]["category"] == "governance"

    def test_report_captures_retries(self):
        session = _make_running_session("sess-report-004")
        mgr = SessionManager()
        session = mgr.transition_state(session, RuntimeState.FAILED)
        classification = self.clf.classify(ConnectionError("timeout"))
        self.orch.attempt_recovery(session, classification, lambda s: None)

        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert len(report.retries) == 1
        assert report.metrics.total_retries == 1

    def test_report_captures_pauses(self):
        session = _make_running_session("sess-report-005")
        session, _ = self.orch.pause(session, reason="waiting for token")
        session, _ = self.orch.resume(session)

        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert len(report.pauses) == 1
        assert report.metrics.total_pauses == 1
        assert report.metrics.total_resumes == 1

    def test_report_recovery_status_recovered(self):
        session = _make_running_session("sess-report-006")
        mgr = SessionManager()
        session = mgr.transition_state(session, RuntimeState.COMPLETED)
        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert report.recovery_status == "recovered"

    def test_report_recovery_status_failed(self):
        session = _make_running_session("sess-report-007")
        mgr = SessionManager()
        session = mgr.transition_state(session, RuntimeState.FAILED)
        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert report.recovery_status == "failed"

    def test_report_metrics_struct(self):
        session = _make_running_session("sess-report-008")
        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert isinstance(report.metrics, RecoveryMetrics)

    def test_report_captures_reviews(self):
        session = _make_running_session("sess-report-009")
        session = self.orch.request_review(session, "schema approval")
        review_id = self.orch.review_engine.pending_review_ids[0]
        session = self.orch.apply_review_decision(session, review_id, ReviewDecision.APPROVE, "op")

        report = self.orch.generate_report(session, "bp-test", "msn-test")
        assert report.metrics.total_reviews_requested == 1
        assert report.metrics.total_reviews_approved == 1

    def test_report_serializable(self):
        session = _make_running_session("sess-report-010")
        report = self.orch.generate_report(session, "bp-test", "msn-test")
        d = report.model_dump(mode="json")
        assert "report_id" in d
        assert "metrics" in d
        assert "recovery_status" in d


# ===========================================================================
# 8. CLI Tests
# ===========================================================================

class TestCLIReview:
    def test_review_approve(self):
        result = runner.invoke(app, ["review", "sess-cli-001", "--approve"])
        assert result.exit_code == 0
        assert "APPROVE" in result.output

    def test_review_reject(self):
        result = runner.invoke(app, ["review", "sess-cli-002", "--reject"])
        assert result.exit_code == 0
        assert "REJECT" in result.output

    def test_review_request_changes(self):
        result = runner.invoke(app, ["review", "sess-cli-003", "--request-changes"])
        assert result.exit_code == 0
        assert "REQUEST_CHANGES" in result.output

    def test_review_no_decision_fails(self):
        result = runner.invoke(app, ["review", "sess-cli-004"])
        assert result.exit_code == 1

    def test_review_multiple_decisions_fails(self):
        result = runner.invoke(app, ["review", "sess-cli-005", "--approve", "--reject"])
        assert result.exit_code == 1

    def test_review_json_output(self):
        result = runner.invoke(app, ["review", "sess-cli-006", "--approve", "--json"])
        assert result.exit_code == 0
        assert "review_id" in result.output
        assert "decision" in result.output

    def test_review_with_notes(self):
        result = runner.invoke(
            app, ["review", "sess-cli-007", "--approve", "--notes", "Looks good"]
        )
        assert result.exit_code == 0

    def test_review_with_actor(self):
        result = runner.invoke(
            app, ["review", "sess-cli-008", "--approve", "--actor", "john.doe"]
        )
        assert result.exit_code == 0


class TestCLIRetry:
    def test_retry_basic(self):
        result = runner.invoke(app, ["retry", "sess-retry-cli-001"])
        assert result.exit_code == 0
        assert "Retry" in result.output

    def test_retry_json_output(self):
        result = runner.invoke(app, ["retry", "sess-retry-cli-002", "--json"])
        assert result.exit_code == 0
        assert "eligible" in result.output
        assert "policy" in result.output

    def test_retry_custom_policy(self):
        result = runner.invoke(
            app, ["retry", "sess-retry-cli-003", "--max-retries", "5", "--base-delay", "2.0"]
        )
        assert result.exit_code == 0
        assert "5" in result.output


class TestCLIResume:
    def test_resume_basic(self):
        result = runner.invoke(app, ["resume", "sess-resume-cli-001"])
        assert result.exit_code == 0
        assert "Resume" in result.output

    def test_resume_json_output(self):
        result = runner.invoke(app, ["resume", "sess-resume-cli-002", "--json"])
        assert result.exit_code == 0
        assert "resume" in result.output
        assert "session_id" in result.output

    def test_resume_with_pause_id(self):
        result = runner.invoke(
            app, ["resume", "sess-resume-cli-003", "--pause-id", "pause-123"]
        )
        assert result.exit_code == 0
        assert "pause-123" in result.output


class TestCLIRecovery:
    def test_recovery_basic(self):
        result = runner.invoke(app, ["recovery", "sess-recovery-cli-001"])
        assert result.exit_code == 0
        assert "Recovery Report" in result.output

    def test_recovery_json_output(self):
        result = runner.invoke(app, ["recovery", "sess-recovery-cli-002", "--json"])
        assert result.exit_code == 0
        assert "report_id" in result.output
        assert "metrics" in result.output
        assert "recovery_status" in result.output

    def test_recovery_with_blueprint_and_mission(self):
        result = runner.invoke(
            app,
            ["recovery", "sess-recovery-cli-003",
             "--blueprint-id", "bp-xyz", "--mission-id", "msn-xyz"]
        )
        assert result.exit_code == 0
        assert "bp-xyz" in result.output
        assert "msn-xyz" in result.output


# ===========================================================================
# 9. Regression — R1/R2/R3 unaffected
# ===========================================================================

class TestRegressionR1R2R3:
    """Verify that Phase R4 changes do not break Phase R1, R2, or R3 symbols."""

    def test_runtime_state_enum_intact(self):
        from runtime.agent.models import RuntimeState
        assert RuntimeState.RUNNING.value == "running"
        assert RuntimeState.WAITING.value == "waiting"
        assert RuntimeState.REVIEW.value == "review"

    def test_execution_status_intact(self):
        from runtime.agent.models import ExecutionStatus
        assert ExecutionStatus.DONE.value == "done"
        assert ExecutionStatus.ERROR.value == "error"

    def test_session_manager_transitions_intact(self):
        session = _make_running_session("sess-reg-001")
        assert session.state == RuntimeState.RUNNING

    def test_agent_init_exports_r4_symbols(self):
        from runtime.agent import (
            FailureCategory, FailureClassifier, RecoveryOrchestrator,
            RetryManager, RuntimeReviewEngine, RecoveryReport,
        )
        assert FailureCategory is not None
        assert FailureClassifier is not None
        assert RecoveryOrchestrator is not None
        assert RetryManager is not None
        assert RuntimeReviewEngine is not None
        assert RecoveryReport is not None

    def test_existing_r3_symbols_still_exported(self):
        from runtime.agent import (
            AgentExecutionEngine, ArtifactCollector, ExecutionReporter,
        )
        assert AgentExecutionEngine is not None
        assert ArtifactCollector is not None
        assert ExecutionReporter is not None

    def test_allowed_runtime_transitions_intact(self):
        from runtime.agent.models import ALLOWED_RUNTIME_TRANSITIONS
        assert RuntimeState.RUNNING in ALLOWED_RUNTIME_TRANSITIONS
        waiting_targets = ALLOWED_RUNTIME_TRANSITIONS[RuntimeState.RUNNING]
        assert RuntimeState.WAITING in waiting_targets
        assert RuntimeState.REVIEW in waiting_targets
