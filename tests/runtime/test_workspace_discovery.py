"""Unit tests for OniRoute Workspace Discovery and Project Detection (ACR-003 Phase W2)."""

from pathlib import Path
import tempfile

from typer.testing import CliRunner

from cli.main import app
from runtime.workspace import (
    DiscoveryPriority,
    EngineResolver,
    ProjectDetector,
    ProjectType,
    WorkspaceManager,
    WorkspaceResolver,
    WorkspaceStatus,
    WorkspaceValidator,
)

runner = CliRunner()


def test_embedded_engine_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        parent_dir = tmp_path / "outer_project"
        parent_dir.mkdir()

        # Create embedded OniRoute_SwarmAgents folder
        embedded_engine = parent_dir / "OniRoute_SwarmAgents"
        embedded_engine.mkdir()
        (embedded_engine / "runtime").mkdir()
        (embedded_engine / "agents").mkdir()
        (embedded_engine / "oniroute.engine").touch()

        # Target project inside parent_dir
        work_dir = parent_dir / "my_workspace"
        work_dir.mkdir()

        resolver = EngineResolver()
        resolved_engine = resolver.resolve_engine_root(work_dir)

        assert resolved_engine.resolve() == embedded_engine.resolve()


def test_parent_engine_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Create engine in top directory
        top_engine = tmp_path / "engine_dir"
        top_engine.mkdir()
        (top_engine / "runtime").mkdir()
        (top_engine / "agents").mkdir()
        (top_engine / ".oniroute_engine").touch()

        # Create nested workspace inside top_engine parent
        nested_sub = top_engine / "nested" / "deep_workspace"
        nested_sub.mkdir(parents=True)

        resolver = EngineResolver()
        resolved = resolver.resolve_engine_root(nested_sub)

        assert resolved.resolve() == top_engine.resolve()


def test_current_directory_workspace_discovery():
    with tempfile.TemporaryDirectory() as tmp_dir:
        ws_path = Path(tmp_dir) / "python_app"
        ws_path.mkdir()
        (ws_path / "pyproject.toml").write_text('[project]\nname = "my-test-app"\n', encoding="utf-8")

        resolver = WorkspaceResolver()
        metadata = resolver.resolve_workspace(cwd=ws_path)

        assert metadata.workspace_root.resolve() == ws_path.resolve()
        assert metadata.project_type == ProjectType.PYTHON
        assert metadata.name == "my-test-app"
        assert metadata.discovery_method == DiscoveryPriority.CURRENT_WORKING_DIRECTORY


def test_project_detection_supported_manifests():
    detector = ProjectDetector()

    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)

        # Python
        py_dir = base / "py"
        py_dir.mkdir()
        (py_dir / "pyproject.toml").write_text('[project]\nname = "py-app"\n', encoding="utf-8")
        assert detector.detect_project(py_dir).project_type == ProjectType.PYTHON

        # Node
        node_dir = base / "node"
        node_dir.mkdir()
        (node_dir / "package.json").write_text('{"name": "node-app"}', encoding="utf-8")
        assert detector.detect_project(node_dir).project_type == ProjectType.NODE

        # Next.js
        next_dir = base / "next"
        next_dir.mkdir()
        (next_dir / "package.json").write_text('{"name": "next-app", "dependencies": {"next": "14.0.0"}}', encoding="utf-8")
        assert detector.detect_project(next_dir).project_type == ProjectType.NEXTJS

        # React
        react_dir = base / "react"
        react_dir.mkdir()
        (react_dir / "package.json").write_text('{"name": "react-app", "dependencies": {"react": "18.0.0"}}', encoding="utf-8")
        assert detector.detect_project(react_dir).project_type == ProjectType.REACT

        # Vue
        vue_dir = base / "vue"
        vue_dir.mkdir()
        (vue_dir / "package.json").write_text('{"name": "vue-app", "dependencies": {"vue": "3.0.0"}}', encoding="utf-8")
        assert detector.detect_project(vue_dir).project_type == ProjectType.VUE

        # Go
        go_dir = base / "go"
        go_dir.mkdir()
        (go_dir / "go.mod").write_text("module example.com/goapp\n\ngo 1.22\n", encoding="utf-8")
        assert detector.detect_project(go_dir).project_type == ProjectType.GO

        # Rust
        rust_dir = base / "rust"
        rust_dir.mkdir()
        (rust_dir / "Cargo.toml").write_text('[package]\nname = "rust-app"\nversion = "0.1.0"\n', encoding="utf-8")
        assert detector.detect_project(rust_dir).project_type == ProjectType.RUST

        # Java
        java_dir = base / "java"
        java_dir.mkdir()
        (java_dir / "pom.xml").write_text("<project><artifactId>java-app</artifactId></project>", encoding="utf-8")
        assert detector.detect_project(java_dir).project_type == ProjectType.JAVA


def test_empty_workspace_detection():
    detector = ProjectDetector()

    with tempfile.TemporaryDirectory() as tmp_dir:
        empty_dir = Path(tmp_dir) / "empty_ws"
        empty_dir.mkdir()

        meta = detector.detect_project(empty_dir)
        assert meta.is_empty is True
        assert meta.project_type == ProjectType.EMPTY


def test_workspace_validation():
    validator = WorkspaceValidator()

    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        eng_dir = base / "engine"
        eng_dir.mkdir()
        ws_dir = base / "workspace"
        ws_dir.mkdir()

        state = validator.validate(workspace_root=ws_dir, engine_root=eng_dir)
        assert state.valid is True

        # Test collision validation (Engine == Workspace)
        collision_state = validator.validate(workspace_root=eng_dir, engine_root=eng_dir)
        assert collision_state.valid is False
        assert any(issue.code == "ENGINE_WORKSPACE_COLLISION" for issue in collision_state.issues)


def test_read_only_engine_enforcement():
    manager = WorkspaceManager()

    with tempfile.TemporaryDirectory() as tmp_dir:
        base = Path(tmp_dir)
        eng_dir = base / "engine"
        eng_dir.mkdir()
        (eng_dir / "runtime").mkdir()
        (eng_dir / "agents").mkdir()

        ws_dir = base / "workspace"
        ws_dir.mkdir()
        (ws_dir / "pyproject.toml").write_text('[project]\nname = "my-app"\n', encoding="utf-8")

        ctx = manager.create_context(cwd=ws_dir)
        assert ctx.is_engine_read_only()
        assert ctx.engine_root != ctx.workspace_root


def test_cli_workspace_command():
    result = runner.invoke(app, ["workspace"])
    assert result.exit_code == 0
    assert "Workspace Root" in result.output
    assert "Engine Root" in result.output
    assert "Project Type" in result.output
    assert "Discovery Method" in result.output
    assert "Validation Status" in result.output


def test_cli_doctor_command_extended():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Workspace" in result.output
    assert "Engine" in result.output
    assert "Project" in result.output
    assert "Read-only Engine" in result.output
