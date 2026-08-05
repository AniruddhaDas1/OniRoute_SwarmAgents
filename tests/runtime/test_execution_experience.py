"""Tests for Execution Experience Subsystem (Phase P6.D2)."""

from __future__ import annotations

import time
from pathlib import Path
import pytest
from rich.console import Console
from typer.testing import CliRunner

from cli.main import app
from runtime.experience import (
    ExecutionEventStream,
    ExecutionRenderer,
    PresentationAdapter,
    SessionRecoveryWatcher,
    SessionStatusReport,
    StreamEvent,
)


def test_event_stream_publish_subscribe():
    """Verify ExecutionEventStream publish, subscribe, unsubscribe, and history."""
    stream = ExecutionEventStream()
    received_events: list[StreamEvent] = []

    sub_id = stream.subscribe(lambda evt: received_events.append(evt))

    evt = stream.publish_event(
        event_type="AGENT_STARTED",
        mission_id="msn-test001",
        agent_role="Frontend Engineer",
        task_description="Building UI components",
        progress_percentage=25.0,
    )

    assert len(received_events) == 1
    assert received_events[0].event_id == evt.event_id
    assert received_events[0].agent_role == "Frontend Engineer"

    # Test unsubscribe
    assert stream.unsubscribe(sub_id) is True
    stream.publish_event("AGENT_FINISHED", mission_id="msn-test001")
    assert len(received_events) == 1  # Unsubscribed, so no new event added

    # Test history retrieval
    history = stream.get_history("msn-test001")
    assert len(history) == 2


def test_presentation_adapter_channel_formatting():
    """Verify PresentationAdapter formats StreamEvents for cli, vscode, web, and api channels."""
    stream = ExecutionEventStream()
    adapter = PresentationAdapter(stream=stream)

    evt = StreamEvent(
        event_id="evt-1001",
        event_type="MISSION_STARTED",
        mission_id="msn-1001",
        stage_name="ENGINEERING",
        agent_role="Lead Architect",
        task_description="Planning architecture",
        progress_percentage=10.0,
        quality_score=9.5,
        timestamp="2026-08-06T00:00:00Z",
    )

    formatted_cli = adapter.format_event_for_channel(evt, "cli")
    assert formatted_cli["channel"] == "cli-renderer"

    formatted_vscode = adapter.format_event_for_channel(evt, "vscode")
    assert formatted_vscode["channel"] == "vscode-extension"
    assert formatted_vscode["eventType"] == "MISSION_STARTED"

    formatted_web = adapter.format_event_for_channel(evt, "web")
    assert formatted_web["data"]["missionId"] == "msn-1001"

    formatted_api = adapter.format_event_for_channel(evt, "api")
    assert formatted_api["status"] == "success"

    broadcast = adapter.broadcast_to_adapters(evt)
    assert "cli" in broadcast and "vscode" in broadcast and "web" in broadcast and "api" in broadcast


def test_execution_renderer():
    """Verify ExecutionRenderer renders events without exceptions."""
    console = Console(record=True)
    renderer = ExecutionRenderer(console=console)

    evt_start = StreamEvent(
        event_id="evt-2001",
        event_type="MISSION_STARTED",
        mission_id="msn-2001",
        task_description="Build real estate website",
        timestamp="2026-08-06T00:00:00Z",
    )
    renderer.render_event(evt_start)

    evt_agent = StreamEvent(
        event_id="evt-2002",
        event_type="AGENT_STARTED",
        mission_id="msn-2001",
        agent_role="Backend Developer",
        task_description="Creating REST API routes",
        timestamp="2026-08-06T00:00:00Z",
    )
    renderer.render_event(evt_agent)

    evt_complete = StreamEvent(
        event_id="evt-2003",
        event_type="MISSION_COMPLETED",
        mission_id="msn-2001",
        progress_percentage=100.0,
        quality_score=9.9,
        production_ready=True,
        timestamp="2026-08-06T00:00:00Z",
    )
    renderer.render_event(evt_complete)

    output = console.export_text()
    assert "Mission Started" in output
    assert "Backend Developer" in output
    assert "Mission Execution Completed" in output


def test_session_recovery_watcher(tmp_path: Path):
    """Verify SessionRecoveryWatcher status report and trace watching."""
    ws_root = tmp_path / "workspace_watcher"
    ws_root.mkdir(parents=True, exist_ok=True)

    watcher = SessionRecoveryWatcher(workspace_root=ws_root)
    status_report = watcher.get_session_status("sess-test-001")

    assert isinstance(status_report, SessionStatusReport)
    assert status_report.session_id == "sess-test-001"
    assert status_report.status in ("COMPLETED", "RUNNING")


def test_cli_status_command(tmp_path: Path):
    """Verify oniroute status CLI command execution."""
    runner = CliRunner()
    ws_root = tmp_path / "workspace_cli_status"
    ws_root.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["status", "--workspace", str(ws_root)])
    assert result.exit_code == 0
    assert "OniRoute Session Status" in result.output

    result_json = runner.invoke(app, ["status", "--workspace", str(ws_root), "--json"])
    assert result_json.exit_code == 0
    assert "session_id" in result_json.output


def test_cli_watch_command(tmp_path: Path):
    """Verify oniroute watch CLI command execution."""
    runner = CliRunner()
    ws_root = tmp_path / "workspace_cli_watch"
    ws_root.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["watch", "--workspace", str(ws_root)])
    assert result.exit_code == 0
    assert "Watching Execution Stream" in result.output


def test_performance_streaming_throughput():
    """Verify streaming throughput latency is < 1.0 ms per event."""
    stream = ExecutionEventStream()
    adapter = PresentationAdapter(stream=stream)

    start_time = time.perf_counter()
    count = 500
    for i in range(count):
        evt = stream.publish_event("AGENT_STARTED", mission_id="msn-bench", agent_role="Dev", progress_percentage=float(i % 100))
        adapter.format_event_for_channel(evt, "cli")

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    latency_per_event_ms = elapsed_ms / count

    assert latency_per_event_ms < 1.0  # Must be fast and lightweight
