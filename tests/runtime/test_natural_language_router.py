"""Tests for Natural Language Router Subsystem (Phase P6.D1)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.router import NaturalLanguageRouter, RouterExecutionResult, SmartDefaults


def test_natural_language_router_end_to_end(tmp_path: Path):
    """Verify NaturalLanguageRouter executes the end-to-end pipeline automatically."""
    ws_root = tmp_path / "workspace_nlr_e2e"
    ws_root.mkdir(parents=True, exist_ok=True)

    router = NaturalLanguageRouter()
    result = router.route_and_execute("build a real estate website", workspace_path=ws_root)

    assert isinstance(result, RouterExecutionResult)
    assert result.request_text == "build a real estate website"
    assert isinstance(result.smart_defaults, SmartDefaults)
    assert result.smart_defaults.project_type == "typescript"
    assert result.smart_defaults.framework == "Next.js"
    assert result.production_ready is True
    assert result.total_files_created > 0
    assert result.quality_score > 0.0


def test_smart_defaults_resolution():
    """Verify smart defaults resolution logic for various prompts."""
    router = NaturalLanguageRouter()

    defaults_ts = router._resolve_smart_defaults(None, "build a SaaS CRM website")
    assert defaults_ts.project_type == "typescript"
    assert defaults_ts.database == "PostgreSQL"

    defaults_py = router._resolve_smart_defaults(None, "create a fastapi backend microservice")
    assert defaults_py.project_type == "python"
    assert defaults_py.framework == "FastAPI"

    defaults_go = router._resolve_smart_defaults(None, "build a go gin app")
    assert defaults_go.project_type == "go"
    assert defaults_go.framework == "Gin Gonic"


def test_low_confidence_prompt_callback(tmp_path: Path):
    """Verify prompt callback is triggered when confidence is below threshold."""
    ws_root = tmp_path / "workspace_nlr_callback"
    ws_root.mkdir(parents=True, exist_ok=True)

    router = NaturalLanguageRouter(confidence_threshold=0.99)
    callback_called = []

    def mock_callback(question: str, options: list[str]) -> str:
        callback_called.append((question, options))
        return "Full-Stack SaaS"

    result = router.route_and_execute(
        "build something vague", workspace_path=ws_root, prompt_callback=mock_callback
    )

    assert len(callback_called) == 1
    assert result.production_ready is True


def test_cli_build_command(tmp_path: Path):
    """Verify oniroute build CLI command execution."""
    runner = CliRunner()
    ws_root = tmp_path / "workspace_cli_build"
    ws_root.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["build", "real-estate", "website", "--workspace", str(ws_root)])
    assert result.exit_code == 0
    assert "Project Generated & Certified Production-Ready" in result.output


def test_cli_create_command_json(tmp_path: Path):
    """Verify oniroute create --json CLI command execution."""
    runner = CliRunner()
    ws_root = tmp_path / "workspace_cli_create_json"
    ws_root.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["create", "SaaS", "CRM", "--workspace", str(ws_root), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["production_ready"] is True
    assert "smart_defaults" in data
