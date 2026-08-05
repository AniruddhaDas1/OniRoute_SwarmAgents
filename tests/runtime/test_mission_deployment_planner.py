"""Tests for Phase P3.A1 Mission Deployment Planner."""

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
    AgentProfileReport,
)
from runtime.deployment import (
    MissionDeploymentPlanner,
    MissionDeploymentPlan,
    ExecutionWave,
    ParallelGroup,
    ReviewGate,
    ApprovalGate,
    ArtifactRoute,
    DeploymentPlanningError,
    CyclicDependencyError,
    benchmark_deployment_planner,
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
    plan_id: str = "plan-test-001",
    mission_id: str = "msn-test-001",
    project_goal: str = "Test Project Goal",
    project_type: str = "python",
    technology_stack: list[str] | None = None,
    required_disciplines: list[str] | None = None,
    required_deliverables: list[str] | None = None,
    repository_strategy: RepositoryStrategy = RepositoryStrategy.FEATURE_ADDITION,
    known_constraints: list[str] | None = None,
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
        known_constraints=known_constraints or [],
        risks=[],
        missing_information=[],
        success_criteria=["Builds cleanly"],
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
    )


def generate_profile_report(registry, resolver, plan: EngineeringExecutionPlan) -> AgentProfileReport:
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)
    return profile_report


def test_simple_website_deployment_plan(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a simple static portfolio website",
        technology_stack=["HTML", "CSS", "JavaScript"],
        required_disciplines=["Frontend"],
        required_deliverables=["Static HTML Pages", "Stylesheets"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    deployment_plan = planner.create_deployment_plan(plan, profile_report)

    assert isinstance(deployment_plan, MissionDeploymentPlan)
    assert deployment_plan.execution_plan_id == plan.plan_id
    assert deployment_plan.mission_id == plan.mission_id
    assert len(deployment_plan.execution_waves) == 6
    assert len(deployment_plan.agent_profiles) > 0
    assert deployment_plan.evidence["validation"]["no_cyclic_execution"] is True
    assert deployment_plan.evidence["validation"]["every_profile_scheduled"] is True
    assert deployment_plan.deployment_hash != ""


def test_fullstack_saas_deployment_plan(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a full-stack SaaS application with React, FastAPI, and PostgreSQL",
        technology_stack=["React", "TypeScript", "FastAPI", "PostgreSQL", "Docker"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "Testing", "Security"],
        required_deliverables=["UI Dashboard", "REST API", "Database Schema", "Docker Container", "Test Suite"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    deployment_plan = planner.create_deployment_plan(plan, profile_report)

    assert isinstance(deployment_plan, MissionDeploymentPlan)
    assert len(deployment_plan.agent_profiles) >= 3
    assert len(deployment_plan.parallel_groups) > 0
    assert len(deployment_plan.review_gates) > 0
    assert len(deployment_plan.approval_gates) > 0
    assert len(deployment_plan.artifact_routes) > 0
    assert deployment_plan.budget_allocation.total_budget_usd == 50.0


def test_api_deployment_plan(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build a scalable microservices REST API with OpenAPI specifications",
        technology_stack=["Python", "FastAPI", "Redis", "PostgreSQL"],
        required_disciplines=["Backend", "Database", "Integration", "Testing"],
        required_deliverables=["API Endpoints", "OpenAPI Spec", "Database Models"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    deployment_plan = planner.create_deployment_plan(plan, profile_report)

    assert isinstance(deployment_plan, MissionDeploymentPlan)
    assert len(deployment_plan.artifact_routes) > 0
    val = deployment_plan.evidence["validation"]
    assert val["valid_artifact_routing"] is True
    assert val["valid_review_path"] is True


def test_ai_project_deployment_plan(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build an autonomous AI agent system with LLM inference pipelines",
        technology_stack=["Python", "PyTorch", "Transformers", "FastAPI"],
        required_disciplines=["AI", "Backend", "Testing", "Documentation"],
        required_deliverables=["Inference Engine", "Model Pipeline", "API Wrapper"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    deployment_plan = planner.create_deployment_plan(plan, profile_report)

    assert isinstance(deployment_plan, MissionDeploymentPlan)
    roles = [p.agent_role for p in deployment_plan.agent_profiles]
    assert any("AI" in r or "Systems" in r for r in roles)


def test_parallel_and_sequential_execution_groups(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Build multi-tier web application",
        technology_stack=["React", "FastAPI", "PostgreSQL"],
        required_disciplines=["Frontend", "Backend", "Database"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    deployment_plan = planner.create_deployment_plan(plan, profile_report)

    assert isinstance(deployment_plan.parallel_execution_groups, dict)
    assert len(deployment_plan.parallel_groups) > 0
    assert isinstance(deployment_plan.sequential_dependencies, dict)


def test_review_and_approval_gates(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Secure financial transaction service",
        technology_stack=["Python", "FastAPI", "PostgreSQL"],
        required_disciplines=["Backend", "Security", "Testing"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    deployment_plan = planner.create_deployment_plan(plan, profile_report)

    assert len(deployment_plan.review_gates) >= 2
    assert len(deployment_plan.approval_gates) >= 2
    assert any(ag.required_approver == "LEAD_ARCHITECT" for ag in deployment_plan.approval_gates)
    assert any(ag.required_approver == "HUMAN_OPERATOR" for ag in deployment_plan.approval_gates)


def test_failure_policies_and_retry_rules(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Mission-critical workflow service",
        technology_stack=["Python"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    deployment_plan = planner.create_deployment_plan(plan, profile_report)

    assert deployment_plan.retry_rules.max_retries == 3
    assert deployment_plan.failure_handling.action == "ABORT_MISSION"
    assert deployment_plan.rollback_strategy.strategy == "SNAPSHOT_RESTORE"
    assert deployment_plan.timeout_rules.total_mission_timeout_seconds > 0


def test_performance_benchmarking_and_determinism(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan(
        project_goal="Deterministic benchmark application",
        technology_stack=["React", "FastAPI", "PostgreSQL"],
    )
    profile_report = generate_profile_report(registry, resolver, plan)
    planner = MissionDeploymentPlanner()

    results = benchmark_deployment_planner(planner, plan, profile_report, iterations=50)

    assert results["is_deterministic"] is True
    assert results["unique_hash_count"] == 1
    assert results["planning_latency_ms"] >= 0.0
    assert results["repeat_avg_latency_ms"] >= 0.0


def test_empty_profile_report_error(registry_and_resolver):
    _, resolver = registry_and_resolver
    plan = create_sample_plan()
    empty_report = AgentProfileReport(
        report_id="apr-empty",
        execution_plan_id=plan.plan_id,
        bundle_report_id="esbr-empty",
        profiles=[],
        bundle_mapping={},
        dependency_graph={},
        recommended_profile_ordering=[],
        coverage={"required_skills": [], "discovered_skills": [], "missing_skills": [], "coverage_percent": 100.0, "registry_hits": 0},
        validation={},
        confidence=1.0,
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
    )
    planner = MissionDeploymentPlanner()

    with pytest.raises(DeploymentPlanningError):
        planner.create_deployment_plan(plan, empty_report)


def test_cli_deployment_command():
    result = runner.invoke(app, ["deployment", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert "Mission Deployment Plan" in result.output
    assert "Execution Waves" in result.output
    assert "Artifact Flow Routes" in result.output


def test_cli_deployment_json_command():
    result = runner.invoke(app, ["deployment", "--json", "Build React FastAPI application"])
    assert result.exit_code == 0
    assert '"plan_id":' in result.output
    assert '"execution_waves":' in result.output
    assert '"deployment_hash":' in result.output
