"""Unit & Integration tests for Workspace Intelligence Engine (Phase P1.I2)."""

from __future__ import annotations

import pytest
from pathlib import Path
from typer.testing import CliRunner

from cli.main import app
from runtime.workspace import (
    ProjectType,
    WorkspaceContext,
    WorkspaceIntelligence,
    WorkspaceState,
)

runner = CliRunner()


def test_empty_workspace_detection(tmp_path: Path):
    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert isinstance(ctx, WorkspaceContext)
    assert ctx.workspace_state == WorkspaceState.EMPTY
    assert ctx.project_type == ProjectType.EMPTY
    assert len(ctx.detected_manifests) == 0


def test_python_project_detection(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('name = "test_py"\nrequires-python = ">=3.12"\n', encoding="utf-8")
    (tmp_path / "src").mkdir()

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.EXISTING_PROJECT
    assert ctx.project_type == ProjectType.PYTHON
    assert ctx.primary_language == "Python"
    assert ctx.build_tool == "pip"
    assert ctx.package_manager == "pip"
    assert "pyproject.toml" in ctx.detected_manifests


def test_node_project_detection(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "test-node", "dependencies": {"express": "^4.0.0"}}', encoding="utf-8")
    (tmp_path / "src").mkdir()

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.EXISTING_PROJECT
    assert ctx.project_type == ProjectType.NODE
    assert ctx.primary_language == "JavaScript/TypeScript"
    assert ctx.build_tool == "npm"
    assert "package.json" in ctx.detected_manifests


def test_flutter_project_detection(tmp_path: Path):
    (tmp_path / "pubspec.yaml").write_text("name: test_flutter\n", encoding="utf-8")
    (tmp_path / "lib").mkdir()

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.EXISTING_PROJECT
    assert ctx.project_type == ProjectType.FLUTTER
    assert ctx.primary_language == "Dart"
    assert ctx.framework_hint == "Flutter"
    assert ctx.build_tool == "flutter"
    assert ctx.package_manager == "pub"
    assert "pubspec.yaml" in ctx.detected_manifests


def test_go_project_detection(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example.com/testgo\n\ngo 1.22\n", encoding="utf-8")
    (tmp_path / "cmd").mkdir()

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.EXISTING_PROJECT
    assert ctx.project_type == ProjectType.GO
    assert ctx.primary_language == "Go"
    assert ctx.build_tool == "go"
    assert "go.mod" in ctx.detected_manifests


def test_rust_project_detection(tmp_path: Path):
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "test_rust"\nversion = "0.1.0"\n', encoding="utf-8")
    (tmp_path / "src").mkdir()

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.EXISTING_PROJECT
    assert ctx.project_type == ProjectType.RUST
    assert ctx.primary_language == "Rust"
    assert ctx.build_tool == "cargo"
    assert "Cargo.toml" in ctx.detected_manifests


def test_java_project_detection(tmp_path: Path):
    (tmp_path / "pom.xml").write_text("<project><artifactId>test-java</artifactId></project>", encoding="utf-8")
    (tmp_path / "src").mkdir()

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.EXISTING_PROJECT
    assert ctx.project_type == ProjectType.JAVA
    assert ctx.primary_language == "Java"
    assert ctx.build_tool == "maven"
    assert "pom.xml" in ctx.detected_manifests


def test_dotnet_project_detection(tmp_path: Path):
    (tmp_path / "TestApp.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk"></Project>', encoding="utf-8")
    (tmp_path / "src").mkdir()

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.EXISTING_PROJECT
    assert ctx.project_type == ProjectType.DOTNET
    assert ctx.primary_language == "C#"
    assert ctx.framework_hint == ".NET"
    assert ctx.build_tool == "dotnet"
    assert "TestApp.csproj" in ctx.detected_manifests


def test_monorepo_project_detection(tmp_path: Path):
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name": "root-monorepo"}', encoding="utf-8")
    (tmp_path / "packages" / "pkg-a").mkdir(parents=True)
    (tmp_path / "packages" / "pkg-a" / "package.json").write_text('{"name": "pkg-a"}', encoding="utf-8")

    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    assert ctx.workspace_state == WorkspaceState.MONOREPO
    assert "pnpm-workspace.yaml" in ctx.detected_manifests


def test_workspace_immutability(tmp_path: Path):
    intel = WorkspaceIntelligence()
    ctx = intel.analyze_workspace(cwd=tmp_path)

    with pytest.raises(Exception):  # Frozen Pydantic model raises FrozenInstanceError
        ctx.primary_language = "Python"  # type: ignore


def test_cli_workspace_context_command():
    result = runner.invoke(app, ["workspace-context"])
    assert result.exit_code == 0
    assert "Workspace Context:" in result.output
    assert "Workspace Root" in result.output


def test_cli_workspace_context_command_json():
    result = runner.invoke(app, ["workspace-context", "--json"])
    assert result.exit_code == 0
    assert '"workspace_id":' in result.output
    assert '"detected_manifests":' in result.output
