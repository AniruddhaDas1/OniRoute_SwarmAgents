"""Tests for Phase P2.S1 Automatic Skill Discovery."""

from pathlib import Path
import pytest

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillSelectionReport,
    SkillCoverage,
    DiscoveredSkill,
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


def test_frontend_project_discovery(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build a modern React frontend dashboard",
        technology_stack=["React", "TypeScript", "Tailwind"],
        required_disciplines=["Frontend"],
        required_deliverables=["User Interface Pages", "UI Components"],
    )

    report = engine.discover_skills(plan)

    assert isinstance(report, SkillSelectionReport)
    assert report.execution_plan_id == plan.plan_id
    assert len(report.discovered_skills) > 0
    assert "Frontend Skills" in report.skill_categories or "Framework Skills" in report.skill_categories or len(report.discovered_skills) > 0

    # Ensure frontend skill is present
    discovered_ids = {s.skill_id for s in report.discovered_skills}
    assert any("frontend" in sid for sid in discovered_ids) or any("responsive" in sid for sid in discovered_ids)
    assert report.coverage.coverage_percent > 0.0


def test_backend_project_discovery(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build FastAPI backend with PostgreSQL",
        technology_stack=["Python", "FastAPI", "PostgreSQL"],
        required_disciplines=["Backend", "Database"],
        required_deliverables=["REST API Endpoints", "Database Schema & Migrations"],
    )

    report = engine.discover_skills(plan)

    assert isinstance(report, SkillSelectionReport)
    discovered_ids = {s.skill_id for s in report.discovered_skills}

    # Should discover backend & database skills
    assert any("backend" in sid for sid in discovered_ids) or any("database" in sid for sid in discovered_ids) or any("api" in sid for sid in discovered_ids)
    assert "Database Skills" in report.skill_categories or any("database" in sid for sid in discovered_ids)


def test_fullstack_project_discovery(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build fullstack web app",
        technology_stack=["React", "Node.js", "PostgreSQL", "Docker"],
        required_disciplines=["Frontend", "Backend", "Database", "DevOps"],
        required_deliverables=[
            "User Interface Pages",
            "REST API Endpoints",
            "Database Schema & Migrations",
            "Containerization & Deployment Scripts",
        ],
    )

    report = engine.discover_skills(plan)

    assert isinstance(report, SkillSelectionReport)
    assert report.coverage.registry_hits > 10
    assert len(report.skill_categories) >= 3
    assert report.confidence >= 0.80


def test_flutter_project_discovery(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Build mobile app using Flutter",
        project_type="flutter",
        technology_stack=["Flutter", "Dart"],
        required_disciplines=["Mobile"],
        required_deliverables=["Mobile Application Bundle"],
    )

    report = engine.discover_skills(plan)

    assert isinstance(report, SkillSelectionReport)
    assert report.execution_plan_id == plan.plan_id


def test_ai_project_discovery(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Integrate AI model agent",
        technology_stack=["Python", "OpenAI", "Gemini"],
        required_disciplines=["AI", "Backend"],
        required_deliverables=["AI Model Integration & Prompts"],
    )

    report = engine.discover_skills(plan)

    assert isinstance(report, SkillSelectionReport)
    discovered_ids = {s.skill_id for s in report.discovered_skills}
    assert any("ai" in sid for sid in discovered_ids) or any("prompt" in sid for sid in discovered_ids)
    assert "AI Skills" in report.skill_categories or any("official.ai" in sid for sid in discovered_ids)


def test_automation_project_discovery(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Automation CLI tool",
        project_type="CLI Tool",
        technology_stack=["Python", "CLI"],
        required_disciplines=["Automation"],
        required_deliverables=["Project Configuration"],
    )

    report = engine.discover_skills(plan)

    assert isinstance(report, SkillSelectionReport)
    assert report.coverage.registry_hits > 0


def test_missing_skills_detection(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        project_goal="Quantum computing legacy project",
        technology_stack=["QuantumCobol", "NonExistentFramework999"],
        required_disciplines=["QuantumEngineering"],
        required_deliverables=["Project Configuration"],
    )

    report = engine.discover_skills(plan)

    assert isinstance(report, SkillSelectionReport)
    assert "QuantumCobol" in report.coverage.missing_skills or "QuantumEngineering" in report.coverage.missing_skills
    assert report.coverage.coverage_percent < 100.0


def test_skill_coverage_metrics(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        technology_stack=["React", "Python"],
        required_disciplines=["Frontend", "Backend"],
    )

    report = engine.discover_skills(plan)

    coverage = report.coverage
    assert isinstance(coverage, SkillCoverage)
    assert coverage.registry_hits == len(report.discovered_skills)
    assert 0.0 <= coverage.coverage_percent <= 100.0
    assert len(coverage.discovered_skills) == coverage.registry_hits


def test_skill_selection_report_immutability_and_json(registry_and_resolver):
    registry, resolver = registry_and_resolver
    engine = SkillDiscoveryEngine(registry, resolver)

    plan = create_sample_plan(
        technology_stack=["React", "FastAPI"],
        required_disciplines=["Frontend", "Backend"],
    )

    report = engine.discover_skills(plan)

    # Immutability check
    with pytest.raises(Exception):
        report.report_id = "new-id"

    # JSON serialization check
    dump_dict = report.model_dump(mode="json")
    assert "report_id" in dump_dict
    assert "execution_plan_id" in dump_dict
    assert "discovered_skills" in dump_dict
    assert "coverage" in dump_dict
    assert "confidence" in dump_dict

    # Reconstruct from JSON
    reconstructed = SkillSelectionReport.model_validate(dump_dict)
    assert reconstructed.report_id == report.report_id
    assert reconstructed.execution_plan_id == report.execution_plan_id
