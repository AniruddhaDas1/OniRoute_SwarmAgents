"""Tests for Phase P2.S2 Deterministic Skill Ranking."""

from pathlib import Path
import pytest

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillSelectionReport,
    RankedSkillReport,
    RankedSkill,
    DependencyChain,
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


def test_official_skills_ranking(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build backend microservice API",
        technology_stack=["Python", "FastAPI"],
        required_disciplines=["Backend"],
        required_deliverables=["REST API Endpoints"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    assert isinstance(ranked_report, RankedSkillReport)
    assert ranked_report.selection_report_id == selection_report.report_id
    assert ranked_report.execution_plan_id == plan.plan_id
    assert len(ranked_report.ranked_skills) > 0

    # Verify official skills are identified and score high trust
    official_skills = [s for s in ranked_report.ranked_skills if s.is_official]
    assert len(official_skills) > 0
    for s in official_skills:
        assert s.score_breakdown["registry_trust"] == 10.0


def test_community_skills_ranking(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Frontend design system",
        technology_stack=["React", "Vue", "Tailwind"],
        required_disciplines=["Frontend"],
        required_deliverables=["User Interface Pages"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    community_skills = [s for s in ranked_report.ranked_skills if not s.is_official]
    assert len(community_skills) > 0
    for s in community_skills:
        assert s.score_breakdown["registry_trust"] == 6.0


def test_mixed_registry_ranking(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Fullstack application",
        technology_stack=["React", "Python", "Docker"],
        required_disciplines=["Frontend", "Backend", "DevOps"],
        required_deliverables=["User Interface Pages", "REST API Endpoints", "Deployment Scripts"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    # Check top ranked skill
    top_skill = ranked_report.ranked_skills[0]
    assert top_skill.rank == 1
    assert top_skill.priority in (SkillPriority.CRITICAL, SkillPriority.HIGH)
    assert top_skill.score >= 70.0


def test_multiple_technologies_ranking(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Enterprise RAG AI App",
        technology_stack=["Python", "React", "PostgreSQL", "Docker", "OpenAI"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps", "AI"],
        required_deliverables=[
            "User Interface Pages",
            "REST API Endpoints",
            "Database Schema & Migrations",
            "Containerization & Deployment Scripts",
            "AI Model Integration & Prompts",
        ],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    assert len(ranked_report.priority_groups) >= 2
    assert ranked_report.evidence["total_ranked_skills"] == len(ranked_report.ranked_skills)


def test_missing_knowledge_and_packages_handling(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Simple script",
        technology_stack=["Python"],
        required_disciplines=["Software Engineering"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    for skill in ranked_report.ranked_skills:
        assert "skill_completeness" in skill.score_breakdown
        assert 0.0 <= skill.score_breakdown["skill_completeness"] <= 10.0


def test_dependency_ordering(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Complex fullstack app",
        technology_stack=["React", "Python"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    assert len(ranked_report.dependency_chains) == len(ranked_report.ranked_skills)
    assert len(ranked_report.recommended_execution_order) == len(ranked_report.ranked_skills)
    for chain in ranked_report.dependency_chains:
        assert isinstance(chain, DependencyChain)


def test_priority_grouping(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Web application",
        technology_stack=["React", "Python"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    grouped_skill_ids = set()
    for group_name, sids in ranked_report.priority_groups.items():
        assert group_name in [p.value for p in SkillPriority]
        for sid in sids:
            grouped_skill_ids.add(sid)

    all_ranked_ids = {s.skill_id for s in ranked_report.ranked_skills}
    assert grouped_skill_ids == all_ranked_ids


def test_repeated_ranking_consistency_and_immutability(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Consistent test plan",
        technology_stack=["React", "Python"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    report1 = ranking_engine.rank_skills(selection_report, plan)
    report2 = ranking_engine.rank_skills(selection_report, plan)

    # Immutability check
    with pytest.raises(Exception):
        report1.report_id = "new-id"

    # Process consistency check
    assert report1.report_id == report2.report_id
    assert [s.skill_id for s in report1.ranked_skills] == [s.skill_id for s in report2.ranked_skills]
    assert [s.score for s in report1.ranked_skills] == [s.score for s in report2.ranked_skills]
    assert report1.recommended_execution_order == report2.recommended_execution_order


def test_regression_skill_ranking(registry_and_resolver):
    registry, resolver = registry_and_resolver
    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    ranking_engine = SkillRankingEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Baseline web project",
        technology_stack=["React", "FastAPI"],
        required_disciplines=["Frontend", "Backend"],
    )

    selection_report = discovery_engine.discover_skills(plan)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    # Validate JSON serialization and deserialization
    json_data = ranked_report.model_dump(mode="json")
    reconstructed = RankedSkillReport.model_validate(json_data)

    assert reconstructed.report_id == ranked_report.report_id
    assert reconstructed.confidence == ranked_report.confidence
    assert len(reconstructed.ranked_skills) == len(ranked_report.ranked_skills)
