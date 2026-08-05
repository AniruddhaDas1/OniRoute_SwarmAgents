"""Tests for ACR-003 Phase W4 — Workspace Runtime Integration.

Covers:
- Persistent execution history (persisted to .oniroute/history/)
- Persistent traces (persisted to .oniroute/traces/)
- Persistent reports (persisted to .oniroute/reports/)
- Workspace logs (persisted to .oniroute/logs/)
- Workspace sessions (persisted to .oniroute/sessions/)
- Runtime integration (engine auto-init, end-to-end, fallback)
- Engine safety (no writes to engine root)
- Regression (backward-compatible in-memory behaviour)
- CLI inspection commands (history, traces, reports, sessions)
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from cli.main import _session_engines
from runtime.context.storage import WorkspaceContextStorage
from runtime.execution.engine import WorkflowEngine
from runtime.execution.history import ExecutionHistory
from runtime.execution.events import EventBus
from runtime.execution.models import ExecutionResult
from runtime.execution.state import ExecutionStatus
from runtime.governance.auditing import AuditEngine
from runtime.governance.models import AuditRecord, GovernanceRequest, PolicyResult, Decision
from runtime.loader import RepositoryLoader
from runtime.optimization.engine import OptimizationEngine
from runtime.optimization.models import OptimizationRequest
from runtime.workspace import (
    ArtifactCategory,
    EngineWriteViolation,
    ExecutionContext,
    ExecutionHistoryStorage,
    LogStorage,
    ProjectType,
    ReportStorage,
    SessionStorage,
    TraceStorage,
    TrustLevel,
    ValidationState,
    WorkspaceLifecycle,
    WorkspaceManager,
    WorkspaceMetadata,
    WorkspaceStatus,
    WorkspaceStorage,
    assert_no_engine_write,
)

ROOT = Path(__file__).parents[2]
runner = CliRunner()


# ── test helpers ─────────────────────────────────────────────────────

def _make_workspace_metadata(tmp_path: Path, engine_root: Path = ROOT) -> WorkspaceMetadata:
    """Build a WorkspaceMetadata with a separate engine root and temp workspace."""
    oniroute = tmp_path / ".oniroute"
    return WorkspaceMetadata(
        workspace_id=f"ws-{abs(hash(str(tmp_path))) % 1000000:06d}",
        name=tmp_path.name,
        workspace_root=tmp_path,
        engine_root=engine_root,
        project_type=ProjectType.PYTHON,
        lifecycle=WorkspaceLifecycle.ACTIVE,
        status=WorkspaceStatus.VALID,
        created=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        owner=None,
        artifact_root=oniroute / "artifacts",
        session_root=oniroute / "sessions",
        logs_root=oniroute / "logs",
        memory_root=oniroute / "memory",
        configuration_root=oniroute / "config",
        plans_root=oniroute / "plans",
        history_root=oniroute / "history",
        traces_root=oniroute / "traces",
        generated_root=oniroute / "generated",
        temporary_root=oniroute / "temporary",
        reports_root=oniroute / "reports",
        approvals_root=oniroute / "approvals",
        cache_root=oniroute / "cache",
        context_root=oniroute / "context",
        knowledge_root=oniroute / "knowledge",
        runtime_root=oniroute / "runtime",
        locks_root=oniroute / "locks",
    )


def _make_workspace_engine(tmp_path: Path) -> tuple[WorkflowEngine, WorkspaceMetadata]:
    """Create a WorkspaceEngine bound to a temp workspace separate from the engine root."""
    meta = _make_workspace_metadata(tmp_path)
    engine = WorkflowEngine(RepositoryLoader(ROOT).load(), workspace_metadata=meta)
    return engine, meta


# ═══════════════════════════════════════════════════════════════════════
# PERSISTENT EXECUTION HISTORY
# ═══════════════════════════════════════════════════════════════════════

class TestPersistentHistory:
    """Tests that execution results are persisted to .oniroute/history/."""

    def test_history_persisted_after_run(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        history_dir = meta.history_root
        assert history_dir.is_dir()
        json_files = list(history_dir.glob("*.json"))
        assert len(json_files) == 1
        record = json.loads(json_files[0].read_text(encoding="utf-8"))
        assert record["workflow_id"] == "rest-api-design"
        assert record["status"] == "Completed"

    def test_history_load_all(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        storage = ExecutionHistoryStorage(meta)
        records = storage.load_all()
        assert len(records) == 1
        assert records[0]["workflow_id"] == "rest-api-design"

    def test_history_count(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        storage = ExecutionHistoryStorage(meta)

        assert storage.count() == 0
        engine.run("rest-api-design")
        assert storage.count() == 1

    def test_history_workspace_scoped(self, tmp_path: Path):
        """History directory must be inside workspace root and outside engine root."""
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        history_dir = meta.history_root
        assert history_dir.resolve().is_relative_to(meta.workspace_root.resolve())
        assert history_dir.resolve() != meta.engine_root.resolve()


# ═══════════════════════════════════════════════════════════════════════
# PERSISTENT TRACES
# ═══════════════════════════════════════════════════════════════════════

class TestPersistentTraces:
    """Tests that trace events are persisted to .oniroute/traces/."""

    def test_trace_persisted_after_run(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        traces_dir = meta.traces_root
        assert traces_dir.is_dir()
        trace_files = list(traces_dir.glob("*.jsonl"))
        assert len(trace_files) == 1
        lines = trace_files[0].read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 3  # WorkflowStarted, steps, WorkflowCompleted
        events = [json.loads(line) for line in lines]
        types = [e["type"] for e in events]
        assert types[0] == "WorkflowStarted"
        assert types[-1] == "WorkflowCompleted"

    def test_trace_read_all(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        trace_storage = TraceStorage(meta)
        trace_ids = trace_storage.list_traces()
        assert len(trace_ids) == 1
        events = trace_storage.read_trace(trace_ids[0])
        assert len(events) >= 3

    def test_trace_count(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        trace_storage = TraceStorage(meta)

        assert trace_storage.count() == 0
        engine.run("rest-api-design")
        assert trace_storage.count() == 1

    def test_trace_workspace_scoped(self, tmp_path: Path):
        """Trace directory must be inside workspace root and outside engine root."""
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        traces_dir = meta.traces_root
        assert traces_dir.resolve().is_relative_to(meta.workspace_root.resolve())
        assert traces_dir.resolve() != meta.engine_root.resolve()


# ═══════════════════════════════════════════════════════════════════════
# PERSISTENT REPORTS
# ═══════════════════════════════════════════════════════════════════════

class TestPersistentReports:
    """Tests that optimization, planning, and audit reports are persisted."""

    def test_optimization_report_persisted(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        reports = ReportStorage(meta)
        assert reports.count() >= 1
        opt_reports = reports.load_reports_by_type("optimization")
        assert len(opt_reports) >= 1

    def test_planning_report_persisted(self, tmp_path: Path):
        """The execution plan should be persisted to .oniroute/plans/."""
        engine, meta = _make_workspace_engine(tmp_path)
        result = engine.run("rest-api-design")

        plans_dir = meta.plans_root
        assert plans_dir.is_dir()
        plan_files = list(plans_dir.glob("*.json"))
        assert len(plan_files) == 1
        content = json.loads(plan_files[0].read_text(encoding="utf-8"))
        assert content["workflow_id"] == result.workflow_id
        assert len(content["steps"]) == 5

    def test_audit_report_persisted(self, tmp_path: Path):
        """Audit records created via AuditEngine should persist to workspace reports."""
        meta = _make_workspace_metadata(tmp_path)
        report_storage = ReportStorage(meta)
        audit = AuditEngine(report_storage=report_storage)
        request = GovernanceRequest(kind="workflow", workflow="test-wf")
        result = PolicyResult(decision=Decision.ALLOW, reasons=("none",))
        audit.record(request, result, "Evaluated")

        reports = report_storage.load_reports_by_type("audit")
        assert len(reports) == 1
        assert reports[0]["data"]["outcome"] == "Evaluated"

    def test_reports_count(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        reports = ReportStorage(meta)
        assert reports.count() >= 1


# ═══════════════════════════════════════════════════════════════════════
# WORKSPACE LOGS
# ═══════════════════════════════════════════════════════════════════════

class TestWorkspaceLogs:
    """Tests that execution logs are persisted to .oniroute/logs/."""

    def test_log_written_on_run(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        log_path = meta.logs_root / "oniroute.log"
        assert log_path.is_file()

    def test_log_read(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        logs = LogStorage(meta)
        entries = logs.read_logs()
        assert len(entries) >= 2  # start + completion
        levels = [e["level"] for e in entries]
        assert "INFO" in levels

    def test_log_count(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        logs = LogStorage(meta)

        assert logs.count() == 0
        engine.run("rest-api-design")
        assert logs.count() >= 2

    def test_log_archive(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        logs = LogStorage(meta)
        archived = logs.archive()
        assert archived.exists()
        assert not logs.log_path.exists()


# ═══════════════════════════════════════════════════════════════════════
# WORKSPACE SESSIONS
# ═══════════════════════════════════════════════════════════════════════

class TestWorkspaceSessions:
    """Tests that sessions are created in .oniroute/sessions/."""

    def test_session_created_on_run(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        sessions = SessionStorage(meta)
        assert sessions.session_count() >= 1

    def test_session_manifest(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        sessions = SessionStorage(meta)
        session_ids = sessions.list_sessions()
        assert len(session_ids) >= 1
        manifest = session_ids[0] + "/manifest.yaml"
        assert (meta.session_root / manifest).is_file()

    def test_session_list(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        sessions = SessionStorage(meta)

        assert sessions.session_count() == 0
        engine.run("rest-api-design")
        assert sessions.session_count() >= 1

    def test_session_metadata(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        sessions = SessionStorage(meta)
        session_ids = sessions.list_sessions()
        for sid in session_ids:
            import yaml
            manifest = yaml.safe_load(
                (sessions.sessions_root / sid / "manifest.yaml").read_text(encoding="utf-8")
            )
            assert manifest["session_id"] == sid
            assert "created" in manifest
            assert manifest["status"] == "open"


# ═══════════════════════════════════════════════════════════════════════
# RUNTIME INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

class TestRuntimeIntegration:
    """Tests for engine auto-initialization and end-to-end persistence."""

    def test_engine_auto_init_storage(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        assert engine._workspace_storage is not None
        assert engine._history_storage is not None
        assert engine._trace_storage is not None
        assert engine._log_storage is not None
        assert engine._session_storage is not None
        assert engine._artifact_router is not None
        assert engine._report_storage is not None

    def test_engine_in_memory_fallback(self):
        """When no workspace metadata is supplied, the engine uses in-memory storage."""
        engine = WorkflowEngine(RepositoryLoader(ROOT).load())
        assert engine._workspace_storage is None
        assert engine._history_storage is None
        assert engine._trace_storage is None
        assert engine._log_storage is None

    def test_execution_persisted_end_to_end(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        result = engine.run("rest-api-design")

        assert result.status == ExecutionStatus.COMPLETED
        # History persisted
        assert ExecutionHistoryStorage(meta).count() == 1
        # Traces persisted
        assert TraceStorage(meta).count() == 1
        # Logs persisted
        assert LogStorage(meta).count() >= 2
        # Sessions persisted
        assert SessionStorage(meta).session_count() >= 1
        # Artifacts persisted (execution reports route to reports/ via ArtifactRouter)
        assert WorkspaceStorage(meta).count_entries("reports") >= 6
        # Plans persisted
        assert WorkspaceStorage(meta).count_entries("plans") >= 1
        # Reports persisted
        assert ReportStorage(meta).count() >= 1

    def test_multiple_executions_accumulate_history(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")
        engine.run("rest-api-design")

        history = ExecutionHistoryStorage(meta)
        assert history.count() == 2

    def test_workspace_yaml_written(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        ws_yaml = meta.workspace_root / ".oniroute" / "workspace.yaml"
        assert ws_yaml.is_file()
        storage = WorkspaceStorage(meta)
        loaded = storage.read_workspace_yaml()
        assert loaded is not None
        assert loaded.workspace_id == meta.workspace_id


# ═══════════════════════════════════════════════════════════════════════
# ENGINE SAFETY
# ═══════════════════════════════════════════════════════════════════════

class TestEngineSafety:
    """Tests that no runtime writes touch the Engine Root."""

    def test_no_engine_write_history(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        # Walk the engine root and ensure no .oniroute files appeared inside it
        engine_oniroute = meta.engine_root / ".oniroute"
        if engine_oniroute.exists():
            files = list(engine_oniroute.rglob("*"))
            assert len(files) == 0, f"Engine root was written to: {files}"

    def test_no_engine_write_traces(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        traces = list(meta.engine_root.rglob("*.jsonl"))
        oniroute_traces = [f for f in traces if ".oniroute" in str(f)]
        assert len(oniroute_traces) == 0, f"Traces written to engine root: {oniroute_traces}"

    def test_no_engine_write_logs(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        engine_logs = meta.engine_root / ".oniroute" / "logs"
        assert not engine_logs.exists()

    def test_no_engine_write_artifacts(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        engine_artifacts = meta.engine_root / ".oniroute" / "artifacts"
        assert not engine_artifacts.exists()

    def test_no_engine_write_sessions(self, tmp_path: Path):
        engine, meta = _make_workspace_engine(tmp_path)
        engine.run("rest-api-design")

        engine_sessions = meta.engine_root / ".oniroute" / "sessions"
        assert not engine_sessions.exists()

    def test_boundary_enforced(self, tmp_path: Path):
        """Engine Root is permanently read-only: writes targeting it must be blocked."""
        from runtime.workspace import assert_outside_engine
        from runtime.workspace.exceptions import WorkspaceBoundaryViolation

        meta = _make_workspace_metadata(tmp_path)

        # assert_outside_engine must reject paths inside the engine root
        with pytest.raises(EngineWriteViolation):
            assert_outside_engine(
                meta.engine_root / "forbidden.txt",
                meta.engine_root,
            )

        # assert_no_engine_write must reject paths inside the engine root
        # (workspace boundary check fires first when the path escapes workspace)
        with pytest.raises((EngineWriteViolation, WorkspaceBoundaryViolation)):
            assert_no_engine_write(
                meta.engine_root / "forbidden.txt",
                meta.workspace_root,
                meta.engine_root,
            )


# ═══════════════════════════════════════════════════════════════════════
# REGRESSION
# ═══════════════════════════════════════════════════════════════════════

class TestRegression:
    """Tests ensuring existing in-memory behaviour is preserved."""

    def test_deterministic_planning(self):
        engine = WorkflowEngine(RepositoryLoader(ROOT).load())
        first = engine.plan("rest-api-design")
        second = engine.plan("rest-api-design")
        assert first == second
        assert [step.execution_order for step in first.steps] == [1, 2, 3, 4, 5]

    def test_in_memory_history_backward_compat(self):
        engine = WorkflowEngine(RepositoryLoader(ROOT).load())
        result = engine.run("rest-api-design")
        assert len(engine.history.all()) == 1
        records = engine.history.all()
        assert records[0].execution_id == result.execution_id

    def test_in_memory_events_backward_compat(self):
        engine = WorkflowEngine(RepositoryLoader(ROOT).load())
        engine.run("rest-api-design")
        assert engine.events.events[0].type == "WorkflowStarted"
        assert engine.events.events[-1].type == "WorkflowCompleted"

    def test_no_workspace_makes_in_memory_engine(self):
        """Without workspace metadata, engine must not have storage components."""
        engine = WorkflowEngine(RepositoryLoader(ROOT).load())
        assert engine._workspace_storage is None
        assert isinstance(engine.history, ExecutionHistory)
        assert isinstance(engine.events, EventBus)
        assert engine.history.all() == ()

    def test_execution_result_unchanged_with_workspace(self, tmp_path: Path):
        """Execution result structure must be identical regardless of workspace storage."""
        engine_ws, _ = _make_workspace_engine(tmp_path)
        result_ws = engine_ws.run("rest-api-design")

        engine_mem = WorkflowEngine(RepositoryLoader(ROOT).load())
        result_mem = engine_mem.run("rest-api-design")

        assert result_ws.status == result_mem.status
        assert len(result_ws.artifacts) == len(result_mem.artifacts)
        assert len(result_ws.plan.steps) == len(result_mem.plan.steps)
        assert [step.status for step in result_ws.plan.steps] == [
            step.status for step in result_mem.plan.steps
        ]

    def test_existing_tests_still_pass(self):
        """Smoke test: the engine runs without errors in in-memory mode."""
        engine = WorkflowEngine(RepositoryLoader(ROOT).load())
        result = engine.run("rest-api-design")
        assert result.status == ExecutionStatus.COMPLETED
        assert len(result.artifacts) == 6
        assert any(
            step.ai_trace and step.ai_trace["approval"] == "Dry Run"
            for step in result.plan.steps
        )


# ═══════════════════════════════════════════════════════════════════════
# CLI INSPECTION COMMANDS
# ═══════════════════════════════════════════════════════════════════════

class TestCLIRuntimeCommands:
    """Tests for oniroute history, traces, reports, sessions CLI commands."""

    @pytest.fixture(autouse=True)
    def _clear_engine_cache(self):
        _session_engines.clear()
        yield
        _session_engines.clear()

    def _run_and_inspect(self, tmp_path: Path) -> None:
        """Run a workflow in a workspace and then inspect via CLI."""
        ws = tmp_path / "user_workspace"
        ws.mkdir()
        result = runner.invoke(
            app,
            ["run", "workflow", "rest-api-design",
             "--repository-root", str(ROOT),
             "--workspace", str(ws)],
        )
        assert result.exit_code == 0, result.output
        return ws

    def test_cli_history_reads_workspace(self, tmp_path: Path):
        self._run_and_inspect(tmp_path)
        ws = tmp_path / "user_workspace"
        result = runner.invoke(
            app,
            ["history", "--repository-root", str(ROOT), "--workspace", str(ws)],
        )
        assert result.exit_code == 0, result.output
        assert "rest-api-design" in result.output

    def test_cli_traces_reads_workspace(self, tmp_path: Path):
        self._run_and_inspect(tmp_path)
        ws = tmp_path / "user_workspace"
        result = runner.invoke(
            app,
            ["traces", "--repository-root", str(ROOT), "--workspace", str(ws)],
        )
        assert result.exit_code == 0, result.output
        assert str(ws.name) in result.output or "Execution" in result.output

    def test_cli_reports_reads_workspace(self, tmp_path: Path):
        self._run_and_inspect(tmp_path)
        ws = tmp_path / "user_workspace"
        result = runner.invoke(
            app,
            ["reports", "--repository-root", str(ROOT), "--workspace", str(ws)],
        )
        assert result.exit_code == 0, result.output

    def test_cli_sessions_reads_workspace(self, tmp_path: Path):
        self._run_and_inspect(tmp_path)
        ws = tmp_path / "user_workspace"
        result = runner.invoke(
            app,
            ["sessions", "--repository-root", str(ROOT), "--workspace", str(ws)],
        )
        assert result.exit_code == 0, result.output

    def test_cli_workspace_shows_runtime_stats(self, tmp_path: Path):
        self._run_and_inspect(tmp_path)
        ws = tmp_path / "user_workspace"
        result = runner.invoke(
            app,
            ["workspace", "--repository-root", str(ROOT), "--workspace", str(ws)],
        )
        assert result.exit_code == 0, result.output
        assert "Runtime Statistics" in result.output
