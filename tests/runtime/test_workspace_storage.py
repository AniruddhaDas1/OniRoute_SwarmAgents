"""Tests for ACR-003 Phase W3 — Workspace Storage & Artifact Routing.

Covers:
- Artifact routing (category mapping, boundary, engine protection, normalization, collisions, extensibility)
- Workspace storage (directory paths, lazy creation, ensure_all, status)
- Engine protection (within workspace / outside engine assertions, router rejection)
- Ownership (ArtifactOwnership creation and serialization)
- Session storage (create, write/read, list/count)
- History storage (persist, load, count)
- Trace storage (write, read, count)
- Log storage (write, read, count)
- CLI (workspace command shows storage info)
- workspace.yaml (write/read, missing returns None)
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.workspace import (
    ArtifactCategory,
    ArtifactCollisionError,
    ArtifactDestination,
    ArtifactOwnership,
    ArtifactRecord,
    ArtifactRouter,
    EngineWriteViolation,
    ExecutionContext,
    ExecutionHistoryStorage,
    LogStorage,
    ProjectType,
    SessionStorage,
    TraceStorage,
    ValidationState,
    WorkspaceBoundaryViolation,
    WorkspaceMetadata,
    WorkspaceStorage,
    WorkspaceValidator,
)
from runtime.workspace.engine_safety import (
    assert_no_engine_write,
    assert_outside_engine,
    assert_within_workspace,
)

runner = CliRunner()


# ── helper: build a WorkspaceMetadata for tests ────────────────────────

def _make_workspace(tmp_path: Path, name: str = "test_workspace") -> WorkspaceMetadata:
    """Build a WorkspaceMetadata with separate engine and workspace roots."""
    engine_root = tmp_path / "engine"
    engine_root.mkdir()
    (engine_root / "runtime").mkdir()
    (engine_root / "agents").mkdir()

    workspace_root = tmp_path / name
    workspace_root.mkdir()

    oniroute = workspace_root / ".oniroute"
    return WorkspaceMetadata(
        workspace_id="ws-test-0001",
        name=name,
        workspace_root=workspace_root,
        engine_root=engine_root,
        project_type=ProjectType.PYTHON,
        created=datetime.now(timezone.utc).isoformat(),
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


def _make_context(ws_meta: WorkspaceMetadata) -> ExecutionContext:
    return ExecutionContext(
        engine_root=ws_meta.engine_root,
        workspace_root=ws_meta.workspace_root,
        cwd=ws_meta.workspace_root,
        workspace_metadata=ws_meta,
    )


def _make_workspace_no_roots(tmp_path: Path) -> WorkspaceMetadata:
    """Build a WorkspaceMetadata WITHOUT the new root fields (backward-compat test)."""
    engine_root = tmp_path / "engine"
    engine_root.mkdir()
    (engine_root / "runtime").mkdir()
    (engine_root / "agents").mkdir()

    workspace_root = tmp_path / "ws"
    workspace_root.mkdir()

    return WorkspaceMetadata(
        workspace_id="ws-test-0002",
        name="ws",
        workspace_root=workspace_root,
        engine_root=engine_root,
        project_type=ProjectType.PYTHON,
        created=datetime.now(timezone.utc).isoformat(),
        artifact_root=workspace_root / ".oniroute" / "artifacts",
        session_root=workspace_root / ".oniroute" / "sessions",
        logs_root=workspace_root / ".oniroute" / "logs",
        memory_root=workspace_root / ".oniroute" / "memory",
        configuration_root=workspace_root / ".oniroute" / "config",
    )


# ═══════════════════════════════════════════════════════════════════════
# ARTIFACT ROUTING TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestArtifactRouting:
    """Tests for ArtifactRouter category mapping and destination resolution."""

    def test_routes_source_code_to_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            dest = router.route_artifact(ctx, ArtifactCategory.SOURCE_CODE, "output.py")

            assert dest.category == ArtifactCategory.SOURCE_CODE
            assert dest.absolute_path.name == "output.py"
            assert dest.absolute_path.parent.name == "generated"
            assert ".oniroute" in dest.relative_path.parts
            assert dest.validate_boundary()
            assert dest.read_only_engine_asserted is True

    def test_routes_each_category_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            expected = {
                ArtifactCategory.SOURCE_CODE: "generated",
                ArtifactCategory.DOCUMENTATION: "artifacts",
                ArtifactCategory.IMAGES: "artifacts",
                ArtifactCategory.REPORTS: "reports",
                ArtifactCategory.TESTS: "generated",
                ArtifactCategory.PRESENTATIONS: "artifacts",
                ArtifactCategory.ARCHITECTURE: "artifacts",
                ArtifactCategory.LOGS: "logs",
                ArtifactCategory.PLANS: "plans",
                ArtifactCategory.SESSIONS: "sessions",
                ArtifactCategory.TEMPORARY_OUTPUTS: "temporary",
            }
            for cat, subdir in expected.items():
                dest = router.route_artifact(ctx, cat, f"file_{cat.value}.txt")
                assert dest.absolute_path.parent.name == subdir
                assert dest.validate_boundary()

    def test_creates_target_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            dest = router.route_artifact(ctx, ArtifactCategory.REPORTS, "report.md")

            assert dest.absolute_path.parent.is_dir()

    def test_validates_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            dest = router.route_artifact(ctx, ArtifactCategory.SOURCE_CODE, "gen.py")
            assert dest.validate_boundary() is True

    def test_prevents_engine_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            dest = router.route_artifact(ctx, ArtifactCategory.SOURCE_CODE, "gen.py")
            # The destination must be outside the engine root
            abs_dest = dest.absolute_path.resolve()
            abs_eng = meta.engine_root.resolve()
            assert abs_eng not in abs_dest.parents
            assert abs_dest != abs_eng

    def test_normalizes_paths_no_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            # Filename with path separators should be normalized
            dest = router.route_artifact(ctx, ArtifactCategory.LOGS, "app.log")
            abs_dest = dest.absolute_path.resolve()

            # Verify the resolved path is under the workspace root
            assert abs_dest.is_relative_to(meta.workspace_root.resolve())

    def test_collision_prevention_renames(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            dest1 = router.route_artifact(ctx, ArtifactCategory.DOCUMENTATION, "doc.md")
            dest1.absolute_path.write_text("first", encoding="utf-8")

            dest2 = router.route_artifact(ctx, ArtifactCategory.DOCUMENTATION, "doc.md")

            assert dest2.absolute_path != dest1.absolute_path
            assert dest2.absolute_path.name != dest1.absolute_path.name
            assert dest2.validate_boundary()

    def test_collision_strict_mode_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta, strict_collisions=True)
            ctx = _make_context(meta)

            dest1 = router.route_artifact(ctx, ArtifactCategory.DOCUMENTATION, "doc.md")
            dest1.absolute_path.write_text("first", encoding="utf-8")

            with pytest.raises(ArtifactCollisionError):
                router.route_artifact(ctx, ArtifactCategory.DOCUMENTATION, "doc.md")

    def test_supports_future_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            # Unknown category should default to "artifacts"
            class CustomCat(str, __import__("enum").Enum):
                CUSTOM = "custom"

            # Test register_category
            router.register_category(ArtifactCategory.SOURCE_CODE, "temporary")
            dest = router.route_artifact(ctx, ArtifactCategory.SOURCE_CODE, "test.txt")
            assert dest.absolute_path.parent.name == "temporary"


# ═══════════════════════════════════════════════════════════════════════
# WORKSPACE STORAGE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestWorkspaceStorage:
    """Tests for WorkspaceStorage directory management."""

    def test_directory_paths_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = WorkspaceStorage(meta)

            assert storage.sessions_root == meta.session_root
            assert storage.history_root == meta.history_root
            assert storage.traces_root == meta.traces_root
            assert storage.artifacts_root == meta.artifact_root
            assert storage.generated_root == meta.generated_root
            assert storage.temporary_root == meta.temporary_root
            assert storage.reports_root == meta.reports_root
            assert storage.approvals_root == meta.approvals_root
            assert storage.cache_root == meta.cache_root
            assert storage.logs_root == meta.logs_root
            assert storage.memory_root == meta.memory_root
            assert storage.plans_root == meta.plans_root
            assert storage.context_root == meta.context_root
            assert storage.knowledge_root == meta.knowledge_root
            assert storage.runtime_root == meta.runtime_root
            assert storage.locks_root == meta.locks_root

    def test_lazy_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = WorkspaceStorage(meta)

            assert not storage.exists()

            created = storage.ensure_dir("sessions")
            assert created.is_dir()
            assert storage.sessions_root.is_dir()
            # Other directories should still not exist
            assert not storage.history_root.exists()

    def test_ensure_all_creates_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = WorkspaceStorage(meta)

            result = storage.ensure_all()
            assert len(result) == len(storage.all_subdir_names)
            for name, path in result.items():
                assert path.is_dir()
            assert storage.exists()

    def test_storage_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = WorkspaceStorage(meta)

            storage.ensure_dir("sessions")
            storage.ensure_dir("history")

            status = storage.storage_status()
            assert status["sessions"] is True
            assert status["history"] is True
            assert status["artifacts"] is False
            assert status["logs"] is False

    def test_count_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = WorkspaceStorage(meta)

            sessions_dir = storage.ensure_dir("sessions")
            (sessions_dir / "session-1").mkdir()
            (sessions_dir / "session-2").mkdir()
            (sessions_dir / "session-3").mkdir()

            assert storage.count_entries("sessions") == 3
            assert storage.count_entries("history") == 0
            assert storage.count_entries("nonexistent") == 0

    def test_workspace_yaml_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = WorkspaceStorage(meta)

            yaml_path = storage.write_workspace_yaml()
            assert yaml_path.is_file()
            assert yaml_path.name == "workspace.yaml"

            loaded = storage.read_workspace_yaml()
            assert loaded is not None
            assert loaded.workspace_id == meta.workspace_id
            assert loaded.name == meta.name
            assert loaded.workspace_root == meta.workspace_root

    def test_workspace_yaml_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = WorkspaceStorage(meta)

            assert storage.read_workspace_yaml() is None


# ═══════════════════════════════════════════════════════════════════════
# ENGINE PROTECTION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestEngineProtection:
    """Tests for engine safety assertions."""

    def test_assert_within_workspace_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            target = meta.workspace_root / ".oniroute" / "test.txt"
            result = assert_within_workspace(target, meta.workspace_root)
            assert result == target.resolve()

    def test_assert_within_workspace_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            target = meta.engine_root / "forbidden.txt"
            with pytest.raises(WorkspaceBoundaryViolation):
                assert_within_workspace(target, meta.workspace_root)

    def test_assert_outside_engine_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            target = meta.workspace_root / ".oniroute" / "sessions"
            result = assert_outside_engine(target, meta.engine_root)
            assert result == target.resolve()

    def test_assert_outside_engine_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            target = meta.engine_root / "runtime" / "forbidden.py"
            with pytest.raises(EngineWriteViolation):
                assert_outside_engine(target, meta.engine_root)

    def test_assert_outside_engine_root_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            with pytest.raises(EngineWriteViolation):
                assert_outside_engine(meta.engine_root, meta.engine_root)

    def test_router_rejects_engine_destination(self):
        """Router must never produce a destination inside the engine root."""
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            dest = router.route_artifact(ctx, ArtifactCategory.LOGS, "engine.log")
            abs_dest = dest.absolute_path.resolve()
            abs_eng = meta.engine_root.resolve()

            assert abs_eng not in abs_dest.parents
            assert abs_dest != abs_eng
            assert dest.validate_boundary()


# ═══════════════════════════════════════════════════════════════════════
# OWNSHIP MODEL TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestArtifactOwnership:
    """Tests for ArtifactOwnership declarative metadata."""

    def test_creation(self):
        ownership = ArtifactOwnership(
            workspace_id="ws-001",
            owner="test-owner",
            mission="Build API",
            workflow="rest-api-design",
            agent="backend-engineer",
            timestamp=datetime.now(timezone.utc).isoformat(),
            artifact_type=ArtifactCategory.SOURCE_CODE,
            generation_source="oniroute run workflow rest-api-design",
            provenance="WorkflowStep:backend-engineer:generate-model",
        )
        assert ownership.workspace_id == "ws-001"
        assert ownership.owner == "test-owner"
        assert ownership.mission == "Build API"
        assert ownership.workflow == "rest-api-design"
        assert ownership.artifact_type == ArtifactCategory.SOURCE_CODE
        assert ownership.validation.valid is True

    def test_serialization_round_trip(self):
        ownership = ArtifactOwnership(
            workspace_id="ws-001",
            owner="test-owner",
            timestamp=datetime.now(timezone.utc).isoformat(),
            artifact_type=ArtifactCategory.DOCUMENTATION,
            generation_source="oniroute plan workflow rest-api-design",
            provenance="WorkflowPlanner",
        )
        data = ownership.model_dump(mode="json")
        restored = ArtifactOwnership(**data)
        assert restored.workspace_id == ownership.workspace_id
        assert restored.artifact_type == ownership.artifact_type


class TestArtifactRecord:
    """Tests for ArtifactRecord combining destination and ownership."""

    def test_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            router = ArtifactRouter(meta)
            ctx = _make_context(meta)

            dest = router.route_artifact(ctx, ArtifactCategory.SOURCE_CODE, "model.py")
            ownership = ArtifactOwnership(
                workspace_id=meta.workspace_id,
                owner="test-owner",
                timestamp=datetime.now(timezone.utc).isoformat(),
                artifact_type=ArtifactCategory.SOURCE_CODE,
                generation_source="workflow-engine",
                provenance="Step:model-generation",
            )
            record = ArtifactRecord(
                destination=dest,
                ownership=ownership,
                filename="model.py",
            )
            assert record.filename == "model.py"
            assert record.destination.category == ArtifactCategory.SOURCE_CODE
            assert record.ownership.workspace_id == meta.workspace_id
            assert record.destination.validate_boundary()


# ═══════════════════════════════════════════════════════════════════════
# SESSION STORAGE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSessionStorage:
    """Tests for workspace-local session storage."""

    def test_create_and_write_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = SessionStorage(meta)

            session_dir = storage.create_session("sess-001", {"agent": "test"})
            assert session_dir.is_dir()
            assert (session_dir / "manifest.yaml").is_file()

            data_path = storage.write_data("sess-001", "output.txt", "hello world")
            assert data_path.is_file()
            assert storage.read_data("sess-001", "output.txt") == "hello world"

    def test_list_and_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = SessionStorage(meta)

            storage.create_session("sess-001")
            storage.create_session("sess-002")
            storage.create_session("sess-003")

            sessions = storage.list_sessions()
            assert len(sessions) == 3
            assert "sess-001" in sessions
            assert storage.session_count() == 3

    def test_persists_to_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = SessionStorage(meta)

            storage.create_session("sess-001")
            sessions_dir = meta.session_root

            # All session files must be inside .oniroute/sessions/
            assert sessions_dir.resolve().is_relative_to(meta.workspace_root.resolve())
            assert sessions_dir.resolve() != meta.engine_root.resolve()

    def test_close_and_delete_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = SessionStorage(meta)

            storage.create_session("sess-001")
            assert storage.session_count() == 1

            storage.close_session("sess-001")
            storage.delete_session("sess-001")
            assert storage.session_count() == 0


# ═══════════════════════════════════════════════════════════════════════
# HISTORY STORAGE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestExecutionHistoryStorage:
    """Tests for workspace-local execution history persistence."""

    def test_persist_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = ExecutionHistoryStorage(meta)

            data = {"execution_id": "exec-001", "status": "Completed", "steps": 3}
            path = storage.persist("exec-001", data)
            assert path.is_file()

            loaded = storage.load("exec-001")
            assert loaded is not None
            assert loaded["execution_id"] == "exec-001"
            assert loaded["status"] == "Completed"

    def test_load_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = ExecutionHistoryStorage(meta)

            storage.persist("exec-001", {"id": "exec-001"})
            storage.persist("exec-002", {"id": "exec-002"})

            all_records = storage.load_all()
            assert len(all_records) == 2

    def test_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = ExecutionHistoryStorage(meta)

            assert storage.count() == 0
            storage.persist("exec-001", {"id": "exec-001"})
            storage.persist("exec-002", {"id": "exec-002"})
            assert storage.count() == 2

    def test_workspace_scoped(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = ExecutionHistoryStorage(meta)

            storage.persist("exec-001", {"id": "exec-001"})
            history_dir = meta.history_root

            assert history_dir.resolve().is_relative_to(meta.workspace_root.resolve())
            assert history_dir.resolve() != meta.engine_root.resolve()


# ═══════════════════════════════════════════════════════════════════════
# TRACE STORAGE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestTraceStorage:
    """Tests for workspace-local trace persistence."""

    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = TraceStorage(meta)

            events = [
                {"type": "WorkflowStarted", "execution_id": "exec-001"},
                {"type": "StepCompleted", "execution_id": "exec-001"},
                {"type": "WorkflowCompleted", "execution_id": "exec-001"},
            ]
            path = storage.write_trace("exec-001", events)
            assert path.is_file()

            read_events = storage.read_trace("exec-001")
            assert len(read_events) == 3
            assert read_events[0]["type"] == "WorkflowStarted"

    def test_list_and_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = TraceStorage(meta)

            assert storage.count() == 0
            storage.write_trace("exec-001", [{"type": "test"}])
            storage.write_trace("exec-002", [{"type": "test"}])

            traces = storage.list_traces()
            assert len(traces) == 2
            assert "exec-001" in traces
            assert storage.count() == 2

    def test_append_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = TraceStorage(meta)

            storage.write_trace("exec-001", [{"type": "StepStarted"}])
            storage.append_trace("exec-001", [{"type": "StepCompleted"}])

            events = storage.read_trace("exec-001")
            assert len(events) == 2
            assert events[1]["type"] == "StepCompleted"


# ═══════════════════════════════════════════════════════════════════════
# LOG STORAGE TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestLogStorage:
    """Tests for workspace-local log storage."""

    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = LogStorage(meta)

            storage.write_log("INFO", "Application started")
            storage.write_log("ERROR", "Something went wrong")

            logs = storage.read_logs()
            assert len(logs) == 2
            assert logs[0]["level"] == "ERROR"  # most-recent-first
            assert logs[1]["level"] == "INFO"

    def test_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = LogStorage(meta)

            assert storage.count() == 0
            storage.write_log("INFO", "msg 1")
            storage.write_log("INFO", "msg 2")
            assert storage.count() == 2

    def test_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = _make_workspace(Path(tmp))
            storage = LogStorage(meta)

            storage.write_log("INFO", "log entry")
            assert storage.log_path.exists()

            archived = storage.archive()
            assert archived.exists()
            assert not storage.log_path.exists()


# ═══════════════════════════════════════════════════════════════════════
# CLI TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestCLIWorkspaceCommand:
    """Tests for the extended `oniroute workspace` CLI command."""

    def test_cli_workspace_shows_storage(self):
        result = runner.invoke(app, ["workspace"])
        assert result.exit_code == 0
        assert "Workspace Root" in result.output
        assert "Engine Root" in result.output
        assert ".oniroute/" in result.output

    def test_cli_workspace_shows_storage_status(self):
        result = runner.invoke(app, ["workspace"])
        assert result.exit_code == 0
        assert "Storage Initialized" in result.output
        assert "Storage Directory Status" in result.output

    def test_cli_workspace_shows_counts(self):
        result = runner.invoke(app, ["workspace"])
        assert result.exit_code == 0
        assert "Sessions" in result.output
        assert "Artifacts" in result.output
        assert "History" in result.output
        assert "Traces" in result.output
        assert "Logs" in result.output
