"""Unit & Integration tests for Engineering Execution Plan (Phase P1.I4)."""

from __future__ import annotations

import pytest
from pathlib import Path
from typer.testing import CliRunner

from cli.main import app
from runtime.intent import IntentAnalyzer
from runtime.workspace import (
    EngineeringExecutionPlan,
    EngineeringPlanGenerator,
    RepositoryContext,
    RepositoryIntelligence,
    RepositoryStrategy,
    WorkspaceIntelligence,
)

runner = CliRunner()


def test_plan_immutability(tmp_path: Path):
    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze("Build a Next.js web application", explicit_workspace=tmp_path)

    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    assert isinstance(plan, EngineeringExecutionPlan)
    with pytest.raises(Exception):
        plan.project_goal = "Modified Goal"  # type: ignore


def test_new_project_strategy_planning(tmp_path: Path):
    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze("Build a luxury real estate website using Next.js and Supabase", explicit_workspace=tmp_path)

    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    assert plan.repository_strategy == RepositoryStrategy.NEW_PROJECT
    assert "Frontend" in plan.required_disciplines
    assert "Database" in plan.required_disciplines
    assert "User Interface Pages" in plan.required_deliverables
    assert len(plan.high_level_milestones) == 5


def test_existing_project_feature_addition(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "existing-app"}', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("console.log('existing');", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze("Add payment checkout feature using Stripe", explicit_workspace=tmp_path)

    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    assert plan.repository_strategy == RepositoryStrategy.FEATURE_ADDITION
    assert "Frontend" in plan.required_disciplines or "Backend" in plan.required_disciplines


def test_bug_fix_strategy(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('name = "py-app"', encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze("Fix memory leak bug in authentication handler", explicit_workspace=tmp_path)

    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    assert plan.repository_strategy == RepositoryStrategy.BUG_FIX


def test_refactor_strategy(tmp_path: Path):
    (tmp_path / "go.mod").write_text("module example.com/app", encoding="utf-8")
    (tmp_path / "main.go").write_text("package main", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze("Refactor database query performance", explicit_workspace=tmp_path)

    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    assert plan.repository_strategy == RepositoryStrategy.REFACTOR_EXISTING


def test_documentation_strategy(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Doc App", encoding="utf-8")

    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze("Update API documentation and README", explicit_workspace=tmp_path)

    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    assert plan.repository_strategy == RepositoryStrategy.DOCUMENTATION
    assert "Documentation" in plan.required_disciplines


def test_multiple_disciplines_planning(tmp_path: Path):
    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze(
        "Build a full-stack SaaS with Next.js, FastAPI, PostgreSQL, Supabase Auth, Docker, and Flutter app",
        explicit_workspace=tmp_path
    )

    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    assert "Frontend" in plan.required_disciplines
    assert "Backend" in plan.required_disciplines
    assert "Database" in plan.required_disciplines
    assert "Security" in plan.required_disciplines
    assert "DevOps" in plan.required_disciplines
    assert "Mobile" in plan.required_disciplines


def test_cli_plan_command():
    result = runner.invoke(app, ["plan", "Build CRM web app"])
    assert result.exit_code == 0
    assert "Engineering Execution Plan:" in result.output
    assert "Repository Strategy" in result.output


def test_cli_plan_command_json():
    result = runner.invoke(app, ["plan", "Build CRM web app", "--json"])
    assert result.exit_code == 0
    assert '"plan_id":' in result.output
    assert '"required_disciplines":' in result.output
