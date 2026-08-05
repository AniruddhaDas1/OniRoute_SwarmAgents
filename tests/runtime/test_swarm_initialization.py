"""Tests for Phase P3.A2 Swarm Initialization."""

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
from runtime.deployment import MissionDeploymentPlanner, MissionDeploymentPlan
from runtime.agent.models import RuntimeState, ExecutionStatus
from runtime.swarm import (
    SwarmInitializationEngine,
    RuntimeExecutionSnapshot,
    SwarmInitializationError,
    benchmark_swarm_initialization,
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
    plan_id: str = "plan-test-002",
    mission_id: str = "msn-test-002",
    project_goal: str = "Test Swarm Initialization Goal",
    project_type: str = "python",
    technology_stack: list[str] | None = None,
    required_disciplines: list[str] | None = None,
    required_deliverables: list[str] | None = None,
    repository_strategy: RepositoryStrategy = RepositoryStrategy.FEATURE_ADDITION,
) -> EngineeringExecutionPlan:
    return EngineeringExecutionPlan(
        plan_id=plan_id,
        mission_id=mission_id,
        project_goal=project_goal,
        current_project_state="EXISTING_PROJECT",
        target_project_state="UPDATED_PROJECT",
        project_type=project_type,
        technology_stack=technology_stack or ["Python"],
        repository_strategy=repository_strategy,
        required_deliverables=required_deliverables or ["Project Configuration"],
        required_disciplines=required_disciplines or ["Software Engineering"],
        high_level_milestones=[{"step": 1, "name": "Setup", "objective": "Setup project", "deliverables": []}],
        known_constraints=[],
        risks=[],
        missing_information=[],
        success_criteria=["Builds cleanly"],
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
    )


def generate_deployment_plan(registry, resolver, plan: EngineeringExecutionPlan) -> MissionDeploymentPlan:
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)
    deployment_planner = MissionDeploymentPlanner()

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)
    deployment_plan = deployment_planner.create_deployment_plan(plan, profile_report)
    return deployment_plan


def test_website_swarm_initialization(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a simple portfolio website",
        technology_stack=["HTML", "CSS", "JavaScript"],
        required_disciplines=["Frontend"],
    )
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    snapshot = swarm_engine.initialize_swarm(deployment_plan)

    assert isinstance(snapshot, RuntimeExecutionSnapshot)
    assert snapshot.deployment_plan_id == deployment_plan.plan_id
    assert snapshot.mission_id == deployment_plan.mission_id
    assert len(snapshot.sessions) > 0
    assert all(s.state == RuntimeState.READY for s in snapshot.sessions)
    assert snapshot.evidence["validation"]["all_profiles_initialized"] is True
    assert snapshot.evidence["validation"]["no_orphan_sessions"] is True


def test_saas_swarm_initialization(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a full-stack SaaS application with React, FastAPI, and PostgreSQL",
        technology_stack=["React", "FastAPI", "PostgreSQL", "Docker"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "Testing"],
    )
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    snapshot = swarm_engine.initialize_swarm(deployment_plan)

    assert isinstance(snapshot, RuntimeExecutionSnapshot)
    assert len(snapshot.sessions) >= 3
    assert len(snapshot.session_map) == len(snapshot.sessions)
    assert snapshot.budget_status.remaining_budget_usd == 50.0
    assert snapshot.budget_status.spent_budget_usd == 0.0


def test_api_swarm_initialization(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a REST API microservice with Redis and PostgreSQL",
        technology_stack=["Python", "FastAPI", "Redis", "PostgreSQL"],
        required_disciplines=["Backend", "Database", "Testing"],
    )
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    snapshot = swarm_engine.initialize_swarm(deployment_plan)

    assert isinstance(snapshot, RuntimeExecutionSnapshot)
    assert len(snapshot.wave_status) == 6
    assert snapshot.execution_cursor.execution_state == "READY"
    assert snapshot.execution_cursor.active_wave_number == 1


def test_ai_project_swarm_initialization(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build an autonomous AI agent system with PyTorch model pipelines",
        technology_stack=["Python", "PyTorch", "FastAPI"],
        required_disciplines=["AI", "Backend", "Testing"],
    )
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    snapshot = swarm_engine.initialize_swarm(deployment_plan)

    assert isinstance(snapshot, RuntimeExecutionSnapshot)
    roles = [s.role_title for s in snapshot.sessions]
    assert any("AI" in r or "Systems" in r for r in roles)


def test_large_swarm_initialization(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Large enterprise system with all disciplines",
        technology_stack=["React", "TypeScript", "FastAPI", "PostgreSQL", "Docker", "PyTorch"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "Testing", "Security", "AI", "Analytics"],
    )
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    snapshot = swarm_engine.initialize_swarm(deployment_plan)

    assert len(snapshot.sessions) >= 5
    assert len(snapshot.session_map) == len(snapshot.sessions)
    assert snapshot.evidence["validation"]["wave_integrity"] is True


def test_budget_initialization(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Budget test project")
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    snapshot = swarm_engine.initialize_swarm(deployment_plan)

    assert snapshot.budget_status.total_budget_usd == 50.0
    assert snapshot.budget_status.spent_budget_usd == 0.0
    assert snapshot.budget_status.remaining_budget_usd == 50.0
    assert snapshot.budget_status.is_exhausted is False


def test_storage_initialization(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Storage test project")
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    snapshot = swarm_engine.initialize_swarm(deployment_plan)

    assert snapshot.storage_references.sessions_root != ""
    assert snapshot.storage_references.traces_root != ""
    assert snapshot.storage_references.logs_root != ""
    assert snapshot.storage_references.history_root != ""
    assert snapshot.evidence["validation"]["storage_connected"] is True


def test_repeated_initialization_determinism(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(project_goal="Deterministic snapshot test project")
    deployment_plan = generate_deployment_plan(registry, resolver, plan)
    swarm_engine = SwarmInitializationEngine()

    bench = benchmark_swarm_initialization(swarm_engine, deployment_plan, iterations=50)

    assert bench["is_deterministic"] is True
    assert bench["unique_hash_count"] == 1
    assert bench["initialization_latency_ms"] >= 0.0


def test_empty_deployment_plan_error():
    empty_plan = MissionDeploymentPlan(
        plan_id="dep-empty",
        mission_id="msn-empty",
        execution_plan_id="plan-empty",
        agent_profiles=[],
        execution_waves=[],
        parallel_execution_groups={},
        parallel_groups=[],
        sequential_dependencies={},
        review_gates=[],
        approval_gates=[],
        human_approval_checkpoints=[],
        artifact_routes=[],
        retry_rules={"max_retries": 3, "backoff_factor": 1.5, "retryable_errors": [], "per_profile_overrides": {}},
        failure_handling={"action": "ABORT_MISSION", "max_failure_threshold": 1, "rollback_on_failure": True, "isolation_enabled": True},
        rollback_strategy={"strategy": "SNAPSHOT_RESTORE", "checkpoint_enabled": True, "rollback_target_wave": 1},
        execution_constraints=[],
        budget_allocation={"total_budget_usd": 50.0, "wave_budgets": {}, "profile_budgets": {}, "currency": "USD"},
        timeout_rules={"total_mission_timeout_seconds": 1800, "wave_timeouts": {}, "profile_timeouts": {}},
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
        deployment_hash="hash-empty",
    )
    swarm_engine = SwarmInitializationEngine()

    with pytest.raises(SwarmInitializationError):
        swarm_engine.initialize_swarm(empty_plan)


def test_cli_initialize_command():
    result = runner.invoke(app, ["initialize", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert "Runtime Execution Snapshot" in result.output
    assert "Initialized Agent Sessions" in result.output
    assert "READY" in result.output


def test_cli_initialize_json_command():
    result = runner.invoke(app, ["initialize", "--json", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert '"snapshot_id":' in result.output
    assert '"execution_uuid":' in result.output
    assert '"snapshot_hash":' in result.output
