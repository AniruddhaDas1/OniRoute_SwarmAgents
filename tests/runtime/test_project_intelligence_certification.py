"""Certification and Integration test suite for Project Intelligence (Phase P1.I5)."""

from __future__ import annotations

import time
from pathlib import Path
from typer.testing import CliRunner

from cli.main import app
from runtime.intent import IntentAnalyzer, IntentReport
from runtime.mission import MissionIntake, MissionResolver
from runtime.workspace import (
    EngineeringExecutionPlan,
    EngineeringPlanGenerator,
    RepositoryContext,
    RepositoryIntelligence,
    WorkspaceContext,
    WorkspaceIntelligence,
)

runner = CliRunner()


def test_end_to_end_project_intelligence_pipeline(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('name = "cert-app"\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')", encoding="utf-8")

    # Stage 1: Intent Analysis
    raw_prompt = "Build a luxury real estate website with Next.js, FastAPI, PostgreSQL, and Supabase Auth"
    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=tmp_path)
    assert isinstance(intent_report, IntentReport)
    assert intent_report.confidence_score >= 0.80

    # Stage 2: Workspace Intelligence
    ws_intel = WorkspaceIntelligence()
    ws_ctx = ws_intel.analyze_workspace(cwd=tmp_path)
    assert isinstance(ws_ctx, WorkspaceContext)
    assert ws_ctx.workspace_root.resolve() == tmp_path.resolve()

    # Stage 3: Repository Intelligence (consumes WorkspaceContext)
    repo_intel = RepositoryIntelligence()
    repo_ctx = repo_intel.analyze_repository(ws_ctx)
    assert isinstance(repo_ctx, RepositoryContext)
    assert repo_ctx.repository_root.resolve() == tmp_path.resolve()
    assert "src/main.py" in repo_ctx.entry_points

    # Stage 4: Engineering Execution Plan (consumes IntentReport, WorkspaceContext, RepositoryContext)
    plan_gen = EngineeringPlanGenerator()
    plan = plan_gen.generate_plan(intent_report, ws_ctx, repo_ctx)
    assert isinstance(plan, EngineeringExecutionPlan)
    assert "Frontend" in plan.required_disciplines
    assert "Backend" in plan.required_disciplines
    assert "Database" in plan.required_disciplines
    assert "Security" in plan.required_disciplines


def test_serialization_and_deserialization(tmp_path: Path):
    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    intent_report = IntentAnalyzer().analyze("Build CRM web app", explicit_workspace=tmp_path)
    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    # Validate JSON dump & reload
    intent_json = intent_report.model_dump_json()
    reconstructed_intent = IntentReport.model_validate_json(intent_json)
    assert reconstructed_intent.intent_id == intent_report.intent_id

    ws_json = ws_ctx.model_dump_json()
    reconstructed_ws = WorkspaceContext.model_validate_json(ws_json)
    assert reconstructed_ws.workspace_id == ws_ctx.workspace_id

    repo_json = repo_ctx.model_dump_json()
    reconstructed_repo = RepositoryContext.model_validate_json(repo_json)
    assert reconstructed_repo.repository_id == repo_ctx.repository_id

    plan_json = plan.model_dump_json()
    reconstructed_plan = EngineeringExecutionPlan.model_validate_json(plan_json)
    assert reconstructed_plan.plan_id == plan.plan_id


def test_performance_latency(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('name = "perf-app"\n', encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('perf')", encoding="utf-8")

    start_time = time.perf_counter()

    intent_report = IntentAnalyzer().analyze("Build a Next.js and FastAPI app", explicit_workspace=tmp_path)
    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    total_latency_ms = (time.perf_counter() - start_time) * 1000.0

    assert plan is not None
    assert total_latency_ms < 200.0  # Pipeline should execute well within 200ms limit


def test_cli_subcommands_certification():
    r_intent = runner.invoke(app, ["intent", "Build CRM", "--json"])
    assert r_intent.exit_code == 0
    assert '"primary_intent":' in r_intent.output

    r_ws = runner.invoke(app, ["workspace-context", "--json"])
    assert r_ws.exit_code == 0
    assert '"workspace_id":' in r_ws.output

    r_repo = runner.invoke(app, ["repository", "--json"])
    assert r_repo.exit_code == 0
    assert '"repository_id":' in r_repo.output

    r_plan = runner.invoke(app, ["plan", "Build CRM", "--json"])
    assert r_plan.exit_code == 0
    assert '"plan_id":' in r_plan.output


def test_mission_intake_backwards_compatibility(tmp_path: Path):
    intent_report = IntentAnalyzer().analyze("Build CRM", explicit_workspace=tmp_path)
    ws_ctx = WorkspaceIntelligence().analyze_workspace(cwd=tmp_path)
    repo_ctx = RepositoryIntelligence().analyze_repository(ws_ctx)
    plan = EngineeringPlanGenerator().generate_plan(intent_report, ws_ctx, repo_ctx)

    intake = MissionIntake()
    req = intake.process_intake(
        "Build CRM",
        explicit_workspace=tmp_path,
        parameters={
            "intent_report": intent_report.model_dump(mode="json"),
            "workspace_context": ws_ctx.model_dump(mode="json"),
            "repository_context": repo_ctx.model_dump(mode="json"),
            "engineering_execution_plan": plan.model_dump(mode="json"),
        },
    )
    assert req.parameters.get("engineering_execution_plan") is not None

    resolver = MissionResolver()
    mission = resolver.resolve_mission(req)
    assert mission.request.parameters.get("engineering_execution_plan") is not None
