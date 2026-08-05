"""Unit & Integration tests for Repository Intelligence Engine (Phase P1.I3)."""

from __future__ import annotations

import pytest
from pathlib import Path
from typer.testing import CliRunner

from cli.main import app
from runtime.workspace import (
    RepositoryContext,
    RepositoryIntelligence,
    WorkspaceIntelligence,
)

runner = CliRunner()


def test_repository_context_immutability(tmp_path: Path):
    ws_intel = WorkspaceIntelligence()
    ws_ctx = ws_intel.analyze_workspace(cwd=tmp_path)
    repo_intel = RepositoryIntelligence()
    repo_ctx = repo_intel.analyze_repository(ws_ctx)

    assert isinstance(repo_ctx, RepositoryContext)
    with pytest.raises(Exception):  # Frozen Pydantic model raises FrozenInstanceError
        repo_ctx.project_layout = "custom"  # type: ignore


def test_node_repository_intelligence(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "node-app", "scripts": {"start": "node index.js"}}', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("console.log('hello');", encoding="utf-8")
    (tmp_path / "next.config.js").write_text("module.exports = {};", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert repo_ctx.project_layout == "src_layout"
    assert "package.json" in repo_ctx.configuration_files
    assert "next.config.js" in repo_ctx.entry_points or "src/index.ts" in repo_ctx.entry_points
    assert repo_ctx.detected_roots.get("source_root") == str(tmp_path / "src")


def test_python_repository_intelligence(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('name = "py-app"\n', encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_dummy(): pass", encoding="utf-8")
    (tmp_path / "README.md").write_text("# PyApp Documentation", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert repo_ctx.test_presence is True
    assert repo_ctx.test_summary.get("test_file_count") == 1
    assert "main.py" in repo_ctx.entry_points
    assert "README.md" in repo_ctx.documentation_files
    assert repo_ctx.detected_roots.get("test_root") == str(tmp_path / "tests")


def test_flutter_repository_intelligence(tmp_path: Path):
    (tmp_path / "pubspec.yaml").write_text("name: flutter_app\n", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "main.dart").write_text("void main() {}", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.png").write_bytes(b"PNGDATA")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert repo_ctx.project_layout == "src_layout"
    assert repo_ctx.detected_roots.get("source_root") == str(tmp_path / "lib")
    assert repo_ctx.asset_summary.get("total_assets") >= 1
    assert repo_ctx.asset_summary.get(".png") == 1


def test_go_repository_intelligence(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example.com/goapp\n", encoding="utf-8")
    (tmp_path / "cmd" / "server").mkdir(parents=True)
    (tmp_path / "cmd" / "server" / "main.go").write_text("package main\nfunc main() {}", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert repo_ctx.detected_roots.get("source_root") == str(tmp_path / "cmd")
    assert "cmd/server/main.go" in repo_ctx.entry_points


def test_rust_repository_intelligence(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "rust_app"\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text("fn main() {}", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert repo_ctx.detected_roots.get("source_root") == str(tmp_path / "src")
    assert "src/main.rs" in repo_ctx.entry_points


def test_java_repository_intelligence(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project><artifactId>java-app</artifactId></project>", encoding="utf-8")
    (tmp_path / "src" / "main" / "java").mkdir(parents=True)
    (tmp_path / "src" / "main" / "java" / "Application.java").write_text("public class Application {}", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert "pom.xml" in repo_ctx.configuration_files
    assert "src/main/java/Application.java" in repo_ctx.entry_points


def test_dotnet_repository_intelligence(tmp_path: Path):
    (tmp_path / "App.csproj").write_text("<Project></Project>", encoding="utf-8")
    (tmp_path / "Program.cs").write_text("class Program {}", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert "Program.cs" in repo_ctx.entry_points
    assert "App.csproj" in repo_ctx.configuration_files


def test_monorepo_repository_intelligence(tmp_path: Path):
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n", encoding="utf-8")
    (tmp_path / "packages" / "app-a").mkdir(parents=True)
    (tmp_path / "packages" / "app-a" / "package.json").write_text('{"name": "app-a"}', encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert repo_ctx.project_layout == "monorepo"


def test_ignored_paths_filtering(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.js").write_text("ignored", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("ignored", encoding="utf-8")
    (tmp_path / "valid.py").write_text("print('valid')", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)

    assert repo_ctx.repository_size.get("file_count") == 1
    assert "node_modules/ignored.js" not in repo_ctx.entry_points


def test_cli_repository_command():
    result = runner.invoke(app, ["repository"])
    assert result.exit_code == 0
    assert "Repository Intelligence:" in result.output
    assert "Layout Pattern" in result.output


def test_cli_repository_command_json():
    result = runner.invoke(app, ["repository", "--json"])
    assert result.exit_code == 0
    assert '"repository_id":' in result.output
    assert '"directory_topology":' in result.output
