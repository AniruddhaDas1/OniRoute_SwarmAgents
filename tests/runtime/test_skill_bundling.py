"""Tests for Phase P2.S3 Execution Skill Bundling."""

from pathlib import Path
import pytest

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillBundlingEngine,
    SkillSelectionReport,
    RankedSkillReport,
    ExecutionSkillBundleReport,
    ExecutionSkillBundle,
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


def test_frontend_bundle_assembly(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build a React frontend UI",
        technology_stack=["React", "TypeScript", "Tailwind"],
        required_disciplines=["Frontend"],
        required_deliverables=["User Interface Pages"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    assert isinstance(bundle_report, ExecutionSkillBundleReport)
    frontend_bundles = [b for b in bundle_report.bundles if b.engineering_discipline == "Frontend"]
    assert len(frontend_bundles) > 0
    frontend_b = frontend_bundles[0]
    assert isinstance(frontend_b, ExecutionSkillBundle)
    assert len(frontend_b.ranked_skills) > 0


def test_backend_bundle_assembly(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build FastAPI REST microservice",
        technology_stack=["Python", "FastAPI", "PostgreSQL"],
        required_disciplines=["Backend", "Database"],
        required_deliverables=["REST API Endpoints", "Database Schema"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    backend_bundles = [b for b in bundle_report.bundles if b.engineering_discipline in ("Backend", "Database")]
    assert len(backend_bundles) >= 1
    total_skills = sum(len(b.ranked_skills) for b in bundle_report.bundles)
    assert total_skills == len(ranked_report.ranked_skills)


def test_fullstack_project_bundling(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Fullstack Web App",
        technology_stack=["React", "Python", "PostgreSQL", "Docker"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps"],
        required_deliverables=["User Interface Pages", "REST API Endpoints", "Database Schema", "Deployment Scripts"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    assert len(bundle_report.bundles) >= 3
    disciplines = {b.engineering_discipline for b in bundle_report.bundles}
    assert "Frontend" in disciplines or "Backend" in disciplines


def test_ai_project_bundling(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Integrate AI model agent",
        technology_stack=["Python", "OpenAI", "Gemini"],
        required_disciplines=["AI", "Backend"],
        required_deliverables=["AI Model Integration & Prompts"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    ai_bundles = [b for b in bundle_report.bundles if b.engineering_discipline == "AI"]
    assert len(ai_bundles) > 0
    assert len(ai_bundles[0].ranked_skills) > 0


def test_mixed_technologies_bundling(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Enterprise multi-stack system",
        technology_stack=["React", "FastAPI", "PostgreSQL", "Docker", "OpenAI"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "AI"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    assert len(bundle_report.bundle_ordering) == len(bundle_report.bundles)
    assert len(bundle_report.bundle_dependencies) == len(bundle_report.bundles)


def test_dependency_bundles_integrity(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Fullstack app with dependencies",
        technology_stack=["React", "Python"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    validation_meta = bundle_report.evidence.get("validation", {})
    assert validation_meta.get("no_orphan_skills") is True
    assert validation_meta.get("no_duplicate_skills") is True


def test_coverage_validation_and_no_orphan_skills(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Baseline web project",
        technology_stack=["React", "FastAPI"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    # Verify skill counts match exactly (no orphans, no duplicates)
    total_skills_in_bundles = sum(len(b.ranked_skills) for b in bundle_report.bundles)
    assert total_skills_in_bundles == len(ranked_report.ranked_skills)

    # All skill IDs present in exactly one bundle
    all_bundled_sids = []
    for b in bundle_report.bundles:
        for s in b.ranked_skills:
            all_bundled_sids.append(s.skill_id)

    assert len(all_bundled_sids) == len(set(all_bundled_sids))


def test_regression_skill_bundling(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)
    bundling_engine = SkillBundlingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Baseline web project",
        technology_stack=["React", "FastAPI"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)
    report1 = bundling_engine.bundle_skills(ranked_report, plan, selection_report)
    report2 = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    # Immutability check
    with pytest.raises(Exception):
        report1.report_id = "new-id"

    # Determinism check
    assert report1.report_id == report2.report_id
    assert report1.bundle_ordering == report2.bundle_ordering

    # JSON serialization check
    json_data = report1.model_dump(mode="json")
    reconstructed = ExecutionSkillBundleReport.model_validate(json_data)
    assert reconstructed.report_id == report1.report_id
    assert len(reconstructed.bundles) == len(report1.bundles)
