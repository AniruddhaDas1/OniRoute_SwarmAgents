"""Unit tests for Mission Control (Phase P6.D3).

Tests pause, resume, cancel, retry, recovery, concurrent missions,
inspection, and CLI command regression.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from runtime.control.models import (
    ConcurrentMissionRegistry,
    MissionControlCommand,
    MissionControlResult,
    MissionHistoryEntry,
    MissionInspection,
)
from runtime.control.engine import MissionControlEngine


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace with .oniroute structure."""
    oniroute = tmp_path / ".oniroute"
    oniroute.mkdir()
    (oniroute / "sessions").mkdir()
    (oniroute / "traces").mkdir()
    (oniroute / "logs").mkdir()
    (oniroute / "history").mkdir()
    return tmp_path


@pytest.fixture
def engine(tmp_workspace: Path) -> MissionControlEngine:
    """Create a MissionControlEngine with temporary workspace."""
    # Clear shared state between tests
    MissionControlEngine._mission_states.clear()
    MissionControlEngine._mission_metadata.clear()
    return MissionControlEngine(workspace_root=tmp_workspace)


# ── Model Tests ───────────────────────────────────────────────────────────

def test_mission_control_command_model():
    """Test MissionControlCommand immutable schema."""
    cmd = MissionControlCommand(
        command_id="cmd-000001",
        action="PAUSE",
        mission_id="msn-test-001",
        session_id="sess-001",
        issued_by="cli",
        reason="user wants to check progress",
        payload={},
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert cmd.command_id == "cmd-000001"
    assert cmd.action == "PAUSE"
    assert cmd.mission_id == "msn-test-001"
    assert cmd.issued_by == "cli"

    with pytest.raises(Exception):
        cmd.action = "RESUME"  # Frozen model


def test_mission_control_result_model():
    """Test MissionControlResult immutable schema."""
    result = MissionControlResult(
        command_id="cmd-000001",
        action="PAUSE",
        mission_id="msn-test-001",
        success=True,
        previous_state="RUNNING",
        current_state="PAUSED",
        message="Mission paused.",
        latency_ms=1.5,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert result.success is True
    assert result.previous_state == "RUNNING"
    assert result.current_state == "PAUSED"


def test_mission_inspection_model():
    """Test MissionInspection immutable schema."""
    inspection = MissionInspection(
        mission_id="msn-test-001",
        session_id="sess-001",
        status="RUNNING",
        current_stage="ENGINEERING",
        current_agent="Backend Engineer",
        current_contract="ctr-001",
        files_created=["src/main.py"],
        files_modified=[],
        quality_score=9.5,
        token_usage={"total_tokens": 5000},
        estimated_cost_usd=0.015,
        active_mcp_tools=["BridgeForce"],
        remaining_contracts=3,
        progress_percentage=45.0,
        production_ready=False,
        elapsed_time_ms=12000.0,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    assert inspection.current_agent == "Backend Engineer"
    assert inspection.remaining_contracts == 3
    assert len(inspection.files_created) == 1


def test_mission_history_entry_model():
    """Test MissionHistoryEntry immutable schema."""
    entry = MissionHistoryEntry(
        mission_id="msn-test-001",
        session_id="sess-001",
        request_text="build a real estate website",
        status="COMPLETED",
        primary_intent="CREATE",
        quality_score=9.7,
        production_ready=True,
        files_created_count=15,
        files_modified_count=3,
        total_cost_usd=0.05,
        elapsed_time_ms=45000.0,
        workspace_root="/tmp/test",
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:01:00+00:00",
    )
    assert entry.production_ready is True
    assert entry.files_created_count == 15


# ── Pause / Resume / Cancel / Retry Tests ─────────────────────────────────

def test_pause_mission(engine: MissionControlEngine):
    """Test pausing a running mission."""
    result = engine.issue_command("PAUSE", "msn-test-001")
    assert result.success is True
    assert result.current_state == "PAUSED"
    assert "paused" in result.message.lower()


def test_resume_mission(engine: MissionControlEngine):
    """Test resuming a paused mission."""
    engine.issue_command("PAUSE", "msn-test-001")
    result = engine.issue_command("RESUME", "msn-test-001")
    assert result.success is True
    assert result.current_state == "RUNNING"
    assert "resumed" in result.message.lower()


def test_cancel_mission(engine: MissionControlEngine):
    """Test cancelling a running mission."""
    result = engine.issue_command("CANCEL", "msn-test-001", reason="no longer needed")
    assert result.success is True
    assert result.current_state == "CANCELLED"
    assert "cancelled" in result.message.lower()


def test_cancel_completed_mission_fails(engine: MissionControlEngine):
    """Test that cancelling a completed mission fails."""
    engine._set_mission_state("msn-test-001", "COMPLETED")
    result = engine.issue_command("CANCEL", "msn-test-001")
    assert result.success is False
    assert "cannot be cancelled" in result.message.lower()


def test_retry_failed_mission(engine: MissionControlEngine):
    """Test retrying a failed mission."""
    engine._set_mission_state("msn-test-001", "FAILED")
    result = engine.issue_command("RETRY", "msn-test-001")
    assert result.success is True
    assert result.current_state == "RUNNING"
    assert "retry" in result.message.lower()


def test_retry_running_mission_fails(engine: MissionControlEngine):
    """Test that retrying a running mission fails."""
    result = engine.issue_command("RETRY", "msn-test-001")
    assert result.success is False
    assert "cannot be retried" in result.message.lower()


# ── Recovery Test ─────────────────────────────────────────────────────────

def test_session_recovery(engine: MissionControlEngine):
    """Test recovering a session after crash."""
    result = engine.recover_session("sess-crash-001")
    assert result.success is True
    assert result.current_state in ("RUNNING", "COMPLETED", "FAILED")
    assert "recovered" in result.message.lower() or "completed" in result.message.lower()


# ── Concurrent Missions Test ─────────────────────────────────────────────

def test_concurrent_missions(engine: MissionControlEngine):
    """Test concurrent mission registry tracking."""
    engine._set_mission_state("msn-001", "RUNNING")
    engine._set_mission_state("msn-002", "RUNNING")
    engine._set_mission_state("msn-003", "PAUSED")
    engine._set_mission_state("msn-004", "COMPLETED")

    registry = engine.get_concurrent_registry()
    assert registry.total_active == 2
    assert registry.total_paused == 1
    assert registry.total_completed == 1
    assert "msn-003" in registry.paused_missions


# ── Inspection Test ───────────────────────────────────────────────────────

def test_inspect_mission(engine: MissionControlEngine):
    """Test mission inspection returns valid contract."""
    inspection = engine.inspect_mission("msn-test-001")
    assert inspection.mission_id == "msn-test-001"
    assert isinstance(inspection.files_created, list)
    assert isinstance(inspection.token_usage, dict)
    assert isinstance(inspection.active_mcp_tools, list)
    assert inspection.timestamp != ""


# ── Mission Logs Test ─────────────────────────────────────────────────────

def test_get_mission_logs(engine: MissionControlEngine):
    """Test mission log retrieval."""
    logs = engine.get_mission_logs("msn-test-001")
    assert isinstance(logs, list)


# ── Approve / Reject Review Tests ─────────────────────────────────────────

def test_approve_review(engine: MissionControlEngine):
    """Test approving a waiting review."""
    result = engine.issue_command(
        "APPROVE_REVIEW", "msn-test-001",
        payload={"review_id": "rev-001"}
    )
    assert result.success is True
    assert "approved" in result.message.lower()


def test_reject_review(engine: MissionControlEngine):
    """Test rejecting a review."""
    result = engine.issue_command(
        "REJECT_REVIEW", "msn-test-001",
        reason="security vulnerability found",
        payload={"review_id": "rev-002", "rejection_reason": "security vulnerability"}
    )
    assert result.success is True
    assert "rejected" in result.message.lower()


# ── CLI Regression Test ───────────────────────────────────────────────────

def test_cli_pause_resume_cancel_commands(capsys):
    """Test that pause, resume, cancel, inspect, logs CLI commands are registered."""
    from cli.main import REGISTERED_CLI_COMMANDS
    assert "pause" in REGISTERED_CLI_COMMANDS
    assert "resume" in REGISTERED_CLI_COMMANDS
    assert "cancel" in REGISTERED_CLI_COMMANDS
    assert "inspect" in REGISTERED_CLI_COMMANDS
    assert "logs" in REGISTERED_CLI_COMMANDS
    assert "status" in REGISTERED_CLI_COMMANDS
    assert "watch" in REGISTERED_CLI_COMMANDS


# ── Performance Tests ─────────────────────────────────────────────────────

def test_pause_latency(engine: MissionControlEngine):
    """Test that pause command executes under 50ms."""
    result = engine.issue_command("PAUSE", "msn-perf-001")
    assert result.latency_ms < 50.0


def test_resume_latency(engine: MissionControlEngine):
    """Test that resume command executes under 50ms."""
    engine.issue_command("PAUSE", "msn-perf-002")
    result = engine.issue_command("RESUME", "msn-perf-002")
    assert result.latency_ms < 50.0


def test_inspection_latency(engine: MissionControlEngine):
    """Test that inspection executes under 100ms."""
    import time
    start = time.perf_counter()
    engine.inspect_mission("msn-perf-003")
    latency = (time.perf_counter() - start) * 1000.0
    assert latency < 100.0


def test_mission_switching_latency(engine: MissionControlEngine):
    """Test that switching between missions is fast."""
    import time
    engine._set_mission_state("msn-switch-001", "RUNNING")
    engine._set_mission_state("msn-switch-002", "PAUSED")

    start = time.perf_counter()
    engine.inspect_mission("msn-switch-001")
    engine.inspect_mission("msn-switch-002")
    latency = (time.perf_counter() - start) * 1000.0
    assert latency < 200.0
