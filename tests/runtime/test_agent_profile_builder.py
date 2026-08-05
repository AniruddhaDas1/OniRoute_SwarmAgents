"""Tests for Phase P2.S4 Agent Profile Builder."""

from pathlib import Path
import pytest

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillBundlingEngine,
    AgentProfileBuilderEngine,
    AgentProfileReport,
    AgentProfile,
    SkillPriority,
)


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
        technology_stack=technology_stack or [],
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


def test_single_bundle_profile_synthesis(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Simple script",
        technology_stack=["Python"],
        required_disciplines=["Software Engineering"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)

    assert isinstance(profile_report, AgentProfileReport)
    assert len(profile_report.profiles) > 0
    assert profile_report.bundle_report_id == bundle_report.report_id
    assert profile_report.execution_plan_id == plan.plan_id


def test_frontend_profile_synthesis(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build a React frontend UI",
        technology_stack=["React", "TypeScript", "Tailwind"],
        required_disciplines=["Frontend"],
        required_deliverables=["User Interface Pages"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)

    frontend_profiles = [p for p in profile_report.profiles if p.primary_discipline == "Frontend"]
    assert len(frontend_profiles) > 0
    f_prof = frontend_profiles[0]
    assert isinstance(f_prof, AgentProfile)
    assert f_prof.agent_role == "Frontend Engineer"
    assert len(f_prof.assigned_bundle_references) == 1


def test_backend_profile_synthesis(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build FastAPI backend microservice",
        technology_stack=["Python", "FastAPI", "PostgreSQL"],
        required_disciplines=["Backend", "Database"],
        required_deliverables=["REST API Endpoints", "Database Schema"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)

    backend_profiles = [p for p in profile_report.profiles if p.primary_discipline in ("Backend", "Database")]
    assert len(backend_profiles) >= 1
    assert profile_report.validation["every_bundle_assigned"] is True


def test_fullstack_project_profiles(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Fullstack Web Application",
        technology_stack=["React", "Python", "PostgreSQL", "Docker"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps"],
        required_deliverables=["User Interface Pages", "REST API Endpoints", "Database Schema", "Deployment Scripts"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)

    assert len(profile_report.profiles) >= 3
    assert len(profile_report.recommended_profile_ordering) == len(profile_report.profiles)
    roles = {p.agent_role for p in profile_report.profiles}
    assert any("Frontend" in r for r in roles) or any("Backend" in r for r in roles)


def test_multiple_bundles_mapping_validation(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Complex system",
        technology_stack=["React", "Python", "Docker", "OpenAI"],
        required_disciplines=["Frontend", "Backend", "DevOps", "AI"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)

    val = profile_report.validation
    assert val["every_bundle_assigned"] is True
    assert val["no_orphan_bundles"] is True
    assert val["no_duplicate_bundle_ownership"] is True
    assert val["dependency_integrity"] is True


def test_dependency_validation(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Fullstack app with dependencies",
        technology_stack=["React", "Python"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)

    assert isinstance(profile_report.dependency_graph, dict)
    assert len(profile_report.dependency_graph) == len(profile_report.profiles)


def test_coverage_validation(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Baseline web project",
        technology_stack=["React", "FastAPI"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    profile_report = builder_engine.build_profiles(bundle_report, plan)

    assert profile_report.coverage.coverage_percent == bundle_report.coverage.coverage_percent
    assert profile_report.confidence > 0.0


def test_regression_agent_profile_builder(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)
    builder_engine = AgentProfileBuilderEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Baseline web project",
        technology_stack=["React", "FastAPI"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    report1 = builder_engine.build_profiles(bundle_report, plan)
    report2 = builder_engine.build_profiles(bundle_report, plan)

    # Immutability check
    with pytest.raises(Exception):
        report1.report_id = "new-id"

    # Determinism check
    assert report1.report_id == report2.report_id
    assert report1.recommended_profile_ordering == report2.recommended_profile_ordering

    # JSON serialization check
    json_data = report1.model_dump(mode="json")
    reconstructed = AgentProfileReport.model_validate(json_data)
    assert reconstructed.report_id == report1.report_id
    assert len(reconstructed.profiles) == len(report1.profiles)
