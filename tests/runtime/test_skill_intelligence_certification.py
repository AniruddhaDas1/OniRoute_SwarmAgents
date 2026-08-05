"""Certification and Freeze Test Suite for Skill Intelligence Subsystem (Phase P2.S5)."""

import time
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
    SkillSelectionReport,
    RankedSkillReport,
    ExecutionSkillBundleReport,
    AgentProfileReport,
)


@pytest.fixture
def registry_and_resolver():
    root = Path.cwd()
    loader = RepositoryLoader(root)
    reg = loader.load()
    res = Resolver(reg)
    return reg, res


def create_sample_plan(
    plan_id: str = "plan-cert-001",
    mission_id: str = "msn-cert-001",
    project_goal: str = "Fullstack React FastAPI Certified App",
    project_type: str = "python",
    technology_stack: list[str] | None = None,
    required_disciplines: list[str] | None = None,
    required_deliverables: list[str] | None = None,
) -> EngineeringExecutionPlan:
    return EngineeringExecutionPlan(
        plan_id=plan_id,
        mission_id=mission_id,
        project_goal=project_goal,
        current_project_state="EXISTING_PROJECT",
        target_project_state="UPDATED_PROJECT",
        project_type=project_type,
        technology_stack=technology_stack or ["React", "Python", "FastAPI", "PostgreSQL", "Docker"],
        repository_strategy=RepositoryStrategy.FEATURE_ADDITION,
        required_deliverables=required_deliverables or [
            "User Interface Pages",
            "REST API Endpoints",
            "Database Schema",
            "Deployment Scripts",
        ],
        required_disciplines=required_disciplines or ["Frontend", "Backend", "Database", "DevOps"],
        high_level_milestones=[{"step": 1, "name": "Certification Setup", "objective": "Initialize", "deliverables": []}],
        known_constraints=["Security compliance"],
        risks=[],
        missing_information=[],
        success_criteria=["Subsystem certified"],
        evidence={},
        timestamp="2026-08-05T00:00:00+00:00",
    )


def test_skill_intelligence_pipeline_integrity(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan()

    disc_engine = SkillDiscoveryEngine(registry, resolver)
    rank_engine = SkillRankingEngine(registry, resolver)
    bundle_engine = SkillBundlingEngine(registry, resolver)
    profile_engine = AgentProfileBuilderEngine(registry, resolver)

    # 1. Discovery
    sel_report = disc_engine.discover_skills(plan)
    assert isinstance(sel_report, SkillSelectionReport)
    assert sel_report.execution_plan_id == plan.plan_id

    # 2. Ranking
    rank_report = rank_engine.rank_skills(sel_report, plan)
    assert isinstance(rank_report, RankedSkillReport)
    assert rank_report.selection_report_id == sel_report.report_id
    assert rank_report.execution_plan_id == plan.plan_id

    # 3. Bundling
    bundle_report = bundle_engine.bundle_skills(rank_report, plan, sel_report)
    assert isinstance(bundle_report, ExecutionSkillBundleReport)
    assert bundle_report.ranked_report_id == rank_report.report_id
    assert bundle_report.selection_report_id == sel_report.report_id
    assert bundle_report.execution_plan_id == plan.plan_id

    # 4. Profiles
    profile_report = profile_engine.build_profiles(bundle_report, plan)
    assert isinstance(profile_report, AgentProfileReport)
    assert profile_report.bundle_report_id == bundle_report.report_id
    assert profile_report.execution_plan_id == plan.plan_id


def test_skill_intelligence_contract_immutability(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan()

    sel_report = SkillDiscoveryEngine(registry, resolver).discover_skills(plan)
    rank_report = SkillRankingEngine(registry, resolver).rank_skills(sel_report, plan)
    bundle_report = SkillBundlingEngine(registry, resolver).bundle_skills(rank_report, plan, sel_report)
    profile_report = AgentProfileBuilderEngine(registry, resolver).build_profiles(bundle_report, plan)

    with pytest.raises(Exception):
        sel_report.report_id = "mutated"

    with pytest.raises(Exception):
        rank_report.report_id = "mutated"

    with pytest.raises(Exception):
        bundle_report.report_id = "mutated"

    with pytest.raises(Exception):
        profile_report.report_id = "mutated"


def test_skill_intelligence_serialization_roundtrip(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan()

    sel = SkillDiscoveryEngine(registry, resolver).discover_skills(plan)
    rnk = SkillRankingEngine(registry, resolver).rank_skills(sel, plan)
    bnd = SkillBundlingEngine(registry, resolver).bundle_skills(rnk, plan, sel)
    prf = AgentProfileBuilderEngine(registry, resolver).build_profiles(bnd, plan)

    re_sel = SkillSelectionReport.model_validate(sel.model_dump(mode="json"))
    re_rnk = RankedSkillReport.model_validate(rnk.model_dump(mode="json"))
    re_bnd = ExecutionSkillBundleReport.model_validate(bnd.model_dump(mode="json"))
    re_prf = AgentProfileReport.model_validate(prf.model_dump(mode="json"))

    assert re_sel.report_id == sel.report_id
    assert re_rnk.report_id == rnk.report_id
    assert re_bnd.report_id == bnd.report_id
    assert re_prf.report_id == prf.report_id


def test_skill_intelligence_process_invariance_and_determinism(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan()

    disc = SkillDiscoveryEngine(registry, resolver)
    rnk_eng = SkillRankingEngine(registry, resolver)
    bnd_eng = SkillBundlingEngine(registry, resolver)
    prf_eng = AgentProfileBuilderEngine(registry, resolver)

    sel1 = disc.discover_skills(plan)
    rnk1 = rnk_eng.rank_skills(sel1, plan)
    bnd1 = bnd_eng.bundle_skills(rnk1, plan, sel1)
    prf1 = prf_eng.build_profiles(bnd1, plan)

    sel2 = disc.discover_skills(plan)
    rnk2 = rnk_eng.rank_skills(sel2, plan)
    bnd2 = bnd_eng.bundle_skills(rnk2, plan, sel2)
    prf2 = prf_eng.build_profiles(bnd2, plan)

    assert sel1.report_id == sel2.report_id
    assert rnk1.report_id == rnk2.report_id
    assert bnd1.report_id == bnd2.report_id
    assert prf1.report_id == prf2.report_id

    assert [p.profile_id for p in prf1.profiles] == [p.profile_id for p in prf2.profiles]


def test_skill_intelligence_reference_integrity(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan()

    sel = SkillDiscoveryEngine(registry, resolver).discover_skills(plan)
    rnk = SkillRankingEngine(registry, resolver).rank_skills(sel, plan)
    bnd = SkillBundlingEngine(registry, resolver).bundle_skills(rnk, plan, sel)
    prf = AgentProfileBuilderEngine(registry, resolver).build_profiles(bnd, plan)

    # 1. No orphan skills
    total_bundled_skills = sum(len(b.ranked_skills) for b in bnd.bundles)
    assert total_bundled_skills == len(rnk.ranked_skills)

    # 2. No duplicate skills
    all_sids = [s.skill_id for b in bnd.bundles for s in b.ranked_skills]
    assert len(all_sids) == len(set(all_sids))

    # 3. No orphan bundles
    all_bundle_ids = {b.bundle_id for b in bnd.bundles}
    assigned_bundle_ids = set(prf.bundle_mapping.keys())
    assert all_bundle_ids == assigned_bundle_ids

    # 4. Dependency graph integrity
    assert prf.validation["dependency_integrity"] is True


def test_skill_intelligence_performance_benchmarks(registry_and_resolver):
    registry, resolver = registry_and_resolver
    plan = create_sample_plan()

    disc = SkillDiscoveryEngine(registry, resolver)
    rnk_eng = SkillRankingEngine(registry, resolver)
    bnd_eng = SkillBundlingEngine(registry, resolver)
    prf_eng = AgentProfileBuilderEngine(registry, resolver)

    # Warm-up run
    _ = prf_eng.build_profiles(bnd_eng.bundle_skills(rnk_eng.rank_skills(disc.discover_skills(plan), plan), plan, disc.discover_skills(plan)), plan)

    t0 = time.perf_counter()
    sel = disc.discover_skills(plan)
    t1 = time.perf_counter()
    rnk = rnk_eng.rank_skills(sel, plan)
    t2 = time.perf_counter()
    bnd = bnd_eng.bundle_skills(rnk, plan, sel)
    t3 = time.perf_counter()
    prf = prf_eng.build_profiles(bnd, plan)
    t4 = time.perf_counter()

    discovery_ms = (t1 - t0) * 1000
    ranking_ms = (t2 - t1) * 1000
    bundling_ms = (t3 - t2) * 1000
    profile_ms = (t4 - t3) * 1000
    total_ms = (t4 - t0) * 1000

    # Ensure total pipeline latency is under 500ms
    assert total_ms < 500.0
    assert len(prf.profiles) > 0

