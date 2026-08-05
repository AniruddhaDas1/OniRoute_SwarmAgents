"""Tests for Phase P3.A3 Autonomous Execution."""

from pathlib import Path
import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillBundlingEngine,
    AgentProfileBuilderEngine,
)
from runtime.deployment import MissionDeploymentPlanner
from runtime.agent.models import RuntimeState, ExecutionStatus
from runtime.swarm import (
    SwarmInitializationEngine,
    AutonomousExecutionEngine,
    ExecutionTaskQueue,
    RuntimeExecutionSnapshot,
    SwarmExecutionResult,
    SwarmInitializationError,
    benchmark_autonomous_execution,
)


runner = CliRunner()


@pytest.fixture
def registry_and_resolver():
    root = Path.cwd()
    loader = RepositoryLoader(root)
    reg = loader.load()
    res = Resolver(reg)
    return reg, res


def create_sample_plan(
    plan_id: str = "plan-exec-003",
    mission_id: str = "msn-exec-003",
    project_goal: str = "Test Autonomous Execution Goal",
    project_type: str = "python",
    technology_stack: list[str] | None = None,
    required_disciplines: list[str] | None = None,
) -> EngineeringExecutionPlan:
    return EngineeringExecutionPlan(
        plan_id=plan_id,
        mission_id=mission_id,
        project_goal=project_goal,
        current_project_state="EXISTING_PROJECT",
        target_project_state="UPDATED_PROJECT",
        project_type=project_type,
        technology_stack=technology_stack or ["Python"],
        repository_strategy=RepositoryStrategy.FEATURE_ADDITION,
        required_deliverables=["Project Configuration"],
        required_disciplines=required_disciplines or ["Software Engineering"],
        high_level_milestones=[{"step": 1, "name": "Setup", "objective": "Setup project", "deliverables": []}],
        known_constraints=[],
        risks=[],
        missing_information=[],
        success_criteria=["Builds cleanly"],
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
    )


def generate_initial_snapshot(registry, resolver, plan: EngineeringExecutionPlan) -> RuntimeExecutionSnapshot:
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)
    deployment_planner = MissionDeploymentPlanner()
    swarm_init_engine = SwarmInitializationEngine()

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)
    deployment_plan = deployment_planner.create_deployment_plan(plan, profile_report)
    return swarm_init_engine.initialize_swarm(deployment_plan)


def test_website_autonomous_execution(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a simple portfolio website",
        technology_stack=["HTML", "CSS", "JavaScript"],
        required_disciplines=["Frontend"],
    )
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    exec_engine = AutonomousExecutionEngine()

    updated_snapshot, results = exec_engine.execute_swarm(init_snapshot)

    assert isinstance(updated_snapshot, RuntimeExecutionSnapshot)
    assert len(results) > 0
    assert updated_snapshot.execution_cursor.execution_state == "COMPLETED"
    assert updated_snapshot.execution_cursor.is_completed is True
    assert all(r.execution_status == ExecutionStatus.DONE for r in results)
    assert all(s.state == RuntimeState.COMPLETED for s in updated_snapshot.sessions)


def test_saas_autonomous_execution(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a full-stack SaaS application with React, FastAPI, and PostgreSQL",
        technology_stack=["React", "FastAPI", "PostgreSQL", "Docker"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "Testing"],
    )
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    exec_engine = AutonomousExecutionEngine()

    updated_snapshot, results = exec_engine.execute_swarm(init_snapshot)

    assert len(results) >= 3
    assert updated_snapshot.budget_status.spent_budget_usd > 0.0
    assert updated_snapshot.budget_status.remaining_budget_usd < 50.0
    assert sum(r.consumed_tokens for r in results) > 1000


def test_api_autonomous_execution(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a REST API microservice with Redis and PostgreSQL",
        technology_stack=["Python", "FastAPI", "Redis", "PostgreSQL"],
        required_disciplines=["Backend", "Database", "Testing"],
    )
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    exec_engine = AutonomousExecutionEngine()

    updated_snapshot, results = exec_engine.execute_swarm(init_snapshot)

    assert len(results) >= 3
    for r in results:
        assert isinstance(r, SwarmExecutionResult)
        assert len(r.produced_artifacts) > 0
        assert r.consumed_tokens > 0


def test_ai_project_autonomous_execution(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build an autonomous AI agent system with PyTorch model pipelines",
        technology_stack=["Python", "PyTorch", "FastAPI"],
        required_disciplines=["AI", "Backend", "Testing"],
    )
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    exec_engine = AutonomousExecutionEngine()

    updated_snapshot, results = exec_engine.execute_swarm(init_snapshot)

    ai_results = [r for r in results if r.profile_id and "ai" in r.profile_id]
    assert len(ai_results) >= 1
    assert ai_results[0].execution_status == ExecutionStatus.DONE


def test_parallel_task_execution(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Parallel execution test project",
        technology_stack=["React", "TypeScript", "FastAPI", "PostgreSQL", "Docker", "PyTorch"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "Testing", "Security", "AI", "Analytics"],
    )
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    queue = ExecutionTaskQueue.from_snapshot(init_snapshot)

    wave_6_tasks = queue.get_tasks_for_wave(6)
    assert len(wave_6_tasks) >= 2


def test_budget_exhaustion(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Budget exhaustion test project")
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    exec_engine = AutonomousExecutionEngine()

    # Pass strict low budget threshold to trigger budget exhaustion
    updated_snapshot, results = exec_engine.execute_swarm(init_snapshot, max_budget_usd=0.005)

    assert updated_snapshot.budget_status.is_exhausted is True
    assert updated_snapshot.execution_cursor.execution_state == "FAILED"


def test_task_failure_and_rollback(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Task failure test project")
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    exec_engine = AutonomousExecutionEngine()

    first_pid = list(init_snapshot.session_map.keys())[0]
    updated_snapshot, results = exec_engine.execute_swarm(init_snapshot, force_failure_profile_id=first_pid)

    assert updated_snapshot.execution_cursor.execution_state == "FAILED"
    failed_results = [r for r in results if r.execution_status == ExecutionStatus.ERROR]
    assert len(failed_results) == 1
    assert failed_results[0].profile_id == first_pid


def test_repeated_execution_determinism(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Deterministic execution test project")
    init_snapshot = generate_initial_snapshot(registry, resolver, plan)
    exec_engine = AutonomousExecutionEngine()

    bench = benchmark_autonomous_execution(exec_engine, init_snapshot, iterations=20)

    assert bench["is_deterministic"] is True
    assert bench["unique_hash_count"] == 1
    assert bench["tokens_per_sec"] >= 0.0


def test_empty_snapshot_execution_error():
    empty_snapshot = RuntimeExecutionSnapshot(
        snapshot_id="snap-empty",
        mission_id="msn-empty",
        deployment_plan_id="dep-empty",
        execution_uuid="exec-uuid-empty",
        wave_status={},
        session_map={},
        sessions=[],
        execution_cursor={"active_wave_number": 1, "execution_state": "READY"},
        execution_context={},
        budget_status={"total_budget_usd": 50.0, "spent_budget_usd": 0.0, "remaining_budget_usd": 50.0},
        retry_status={"total_retries_attempted": 0},
        checkpoint_status={"current_checkpoint_id": "chk-w1-init-empty"},
        event_bus_references={"bus_id": "bus-empty"},
        storage_references={
            "workspace_root": "/tmp",
            "sessions_root": "/tmp/sessions",
            "traces_root": "/tmp/traces",
            "logs_root": "/tmp/logs",
            "history_root": "/tmp/history",
            "reports_root": "/tmp/reports",
            "artifacts_root": "/tmp/artifacts",
        },
        workspace_references={
            "workspace_id": "ws-empty",
            "workspace_root": "/tmp",
            "engine_root": "/tmp",
            "is_engine_read_only": False,
            "project_type": "python",
        },
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
        snapshot_hash="hash-empty",
    )
    exec_engine = AutonomousExecutionEngine()

    with pytest.raises(SwarmInitializationError):
        exec_engine.execute_swarm(empty_snapshot)



def test_cli_execute_command():
    result = runner.invoke(app, ["execute", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert "Autonomous Execution Complete" in result.output
    assert "Task Execution Results" in result.output
    assert "done" in result.output


def test_cli_execute_json_command():
    result = runner.invoke(app, ["execute", "--json", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert '"snapshot":' in result.output
    assert '"execution_results":' in result.output
    assert '"consumed_tokens":' in result.output
