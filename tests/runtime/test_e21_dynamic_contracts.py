"""Tests for Phase E2.1 - Dynamic Engineering Contract Foundation."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pytest

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.workspace.plan import EngineeringExecutionPlan, RepositoryStrategy
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillBundlingEngine,
    AgentProfileBuilderEngine,
)
from runtime.contracts import (
    EngineeringContractBuilder,
    EngineeringContract,
    EngineeringContractReport,
    DeliverableContract,
    AcceptanceCriteria,
    ContractTraceability,
    ContractCoverageMetrics,
    ContractDependencyError,
    ContractCoverageError,
    ContractValidationError,
)


class _DeterminismResult:
    """Simple result wrapper for determinism testing."""
    def __init__(self, report):
        self.contract_ids = [c.contract_id for c in report.contracts]
        self.contract_count = len(report.contracts)
        self.deterministic = report.deterministic


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def registry_and_resolver():
    root = Path.cwd()
    loader = RepositoryLoader(root)
    reg = loader.load()
    res = Resolver(reg)
    return reg, res


def _make_plan(
    plan_id: str = "plan-test-001",
    mission_id: str = "msn-test-001",
    project_goal: str = "Test Project Goal",
    project_type: str = "python",
    technology_stack: list[str] | None = None,
    required_disciplines: list[str] | None = None,
    required_deliverables: list[str] | None = None,
    known_constraints: list[str] | None = None,
) -> EngineeringExecutionPlan:
    """Factory: create a deterministic EngineeringExecutionPlan."""
    return EngineeringExecutionPlan(
        plan_id=plan_id,
        mission_id=mission_id,
        project_goal=project_goal,
        current_project_state="EXISTING_PROJECT",
        target_project_state="UPDATED_PROJECT",
        project_type=project_type,
        technology_stack=technology_stack or [],
        repository_strategy=RepositoryStrategy.FEATURE_ADDITION,
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


def _build_pipeline(
    registry_and_resolver,
    plan: EngineeringExecutionPlan,
) -> Tuple:
    """Run the full upstream intelligence pipeline."""
    registry, resolver = registry_and_resolver
    discovery = SkillDiscoveryEngine(registry, resolver)
    ranking = SkillRankingEngine(registry, resolver)
    bundling = SkillBundlingEngine(registry, resolver)
    profile_builder = AgentProfileBuilderEngine(registry, resolver)
    
    selection = discovery.discover_skills(plan)
    ranked = ranking.rank_skills(selection, plan)
    bundles = bundling.bundle_skills(ranked, plan, selection)
    profiles = profile_builder.build_profiles(bundles, plan)
    return bundles, profiles


def _run_full_pipeline(registry_and_resolver, plan):
    """Run the full pipeline and return a simple result object for determinism testing."""
    bundles, profiles = _build_pipeline(registry_and_resolver, plan)
    builder = EngineeringContractBuilder()
    report = builder.build(plan, bundles, profiles)
    return _DeterminismResult(report)

# ---------------------------------------------------------------------------
# E2.1.2 / E2.1.3 - Model verification
# ---------------------------------------------------------------------------

class TestEngineeringContractModels:
    """Verify E2.1 contract model definitions."""

    def test_engineering_contract_has_required_fields(self):
        """EngineeringContract must have all E2.1.2 fields."""
        fields = EngineeringContract.model_fields
        required = [
        "contract_id", "mission_id", "project_goal", "engineering_domain",
        "agent_profile_id", "skill_bundle_id", "objective",
        "required_capabilities", "required_skills", "inputs",
        "expected_deliverables", "acceptance_criteria", "dependencies",
        "constraints", "repository_scope", "technology_context",
        "priority", "execution_order", "risk_level",
        ]
        for f in required:
            assert f in fields, f"Missing required field: {f}"

    def test_engineering_contract_is_frozen(self):
        """EngineeringContract must be immutable."""
        assert EngineeringContract.model_config.get("frozen") is True

    def test_deliverable_contract_model(self):
        """DeliverableContract must define WHAT must exist after execution."""
        dc = DeliverableContract(
            deliverable_id="del-ctr-0001-01",
            contract_id="ctr-0001",
            mission_id="msn-001",
            description="A responsive property search UI",
            deliverable_type="frontend_application",
            acceptance_criteria=["Pages render correctly"],
            verification_method="automated_test",
            estimated_complexity="MEDIUM",
            dependencies=[],
        )
        assert dc.deliverable_id == "del-ctr-0001-01"
        assert dc.contract_id == "ctr-0001"
        assert dc.mission_id == "msn-001"
        assert dc.description == "A responsive property search UI"
        assert dc.deliverable_type == "frontend_application"
        assert dc.estimated_complexity == "MEDIUM"

    def test_acceptance_criteria_model(self):
        """AcceptanceCriteria must support Given/When/Then format."""
        ac = AcceptanceCriteria(
            criteria_id="ac-ctr-0001-01",
            contract_id="ctr-0001",
            mission_id="msn-001",
            description="Given valid params When called Then returns matching results",
            category="functional",
            is_deterministic=True,
            test_reference="tests/test_search.py",
        )
        assert ac.criteria_id == "ac-ctr-0001-01"
        assert ac.category == "functional"
        assert ac.is_deterministic is True

    def test_contract_traceability_model(self):
        """ContractTraceability must link all upstream artifacts."""
        tr = ContractTraceability(
            contract_id="ctr-0001",
            mission_id="msn-001",
            intent_report_id="int-001",
            execution_plan_id="plan-001",
            skill_bundle_report_id="esbr-001",
            agent_profile_report_id="apr-001",
            allocation_report_id="alloc-001",
            source_deliverable="UI Pages",
            trace_chain=["int-001", "plan-001", "esbr-001", "apr-001", "ctr-0001"],
        )
        assert tr.contract_id == "ctr-0001"
        assert len(tr.trace_chain) == 5
        assert tr.execution_plan_id == "plan-001"

    def test_contract_coverage_metrics_model(self):
        """ContractCoverageMetrics must track coverage accounting."""
        cm = ContractCoverageMetrics(
            total_bundles=3, contracted_bundles=3, coverage_percent=100.0,
            uncovered_bundles=[], total_deliverables=6, covered_deliverables=6,
            uncovered_deliverables=[], total_disciplines=3,
            represented_disciplines=3, missing_disciplines=[],
        )
        assert cm.coverage_percent == 100.0
        assert cm.total_bundles == 3
        assert len(cm.uncovered_bundles) == 0

# ---------------------------------------------------------------------------
# E2.1.3 / E2.1.4 - Contract generation
# ---------------------------------------------------------------------------

class TestContractGeneration:
    """Test contract generation from engineering intelligence."""

    def test_single_contract_generation(self, registry_and_resolver):
        """A single-discipline plan produces at least one contract."""
        plan = _make_plan(
            project_goal="Simple Python script",
            technology_stack=["Python"],
            required_disciplines=["Software Engineering"],
        )
        bundles, profiles = _build_pipeline(registry_and_resolver, plan)
        
        builder = EngineeringContractBuilder()
        report = builder.build(plan, bundles, profiles)
        
        assert isinstance(report, EngineeringContractReport)
        assert len(report.contracts) >= 1

    def test_multi_contract_generation(self, registry_and_resolver):
        """A multi-discipline plan produces one contract per discipline."""
        plan = _make_plan(
            project_goal="Fullstack real estate website",
            technology_stack=["React", "TypeScript", "FastAPI", "PostgreSQL"],
            required_disciplines=["Frontend", "Backend", "Database"],
            required_deliverables=[
                "Responsive property search UI",
                "Property search API",
                "Property and user data models",
            ],
        )
        bundles, profiles = _build_pipeline(registry_and_resolver, plan)
        
        builder = EngineeringContractBuilder()
        report = builder.build(plan, bundles, profiles)
        
        assert isinstance(report, EngineeringContractReport)
        assert len(report.contracts) >= 3
        assert len(report.contracts) == len(bundles.bundles)

    def test_real_estate_example(self, registry_and_resolver):
        """Build a real estate website - produces contracts without generating code."""
        plan = _make_plan(
            plan_id="plan-realestate",
            mission_id="msn-realestate",
            project_goal="Build a real estate listing website with search, listings, and inquiry management",
            project_type="web",
            technology_stack=["React", "TypeScript", "Tailwind CSS", "FastAPI", "PostgreSQL", "Supabase"],
            required_disciplines=["Frontend", "Backend", "Database", "Testing"],
            required_deliverables=[
                "Responsive property search and listing UI",
                "Property search API with filtering",
                "Property, user, and inquiry data models",
                "Automated tests for property search and inquiry",
            ],
            known_constraints=["Use Supabase for authentication and database"],
        )
        bundles, profiles = _build_pipeline(registry_and_resolver, plan)
        
        builder = EngineeringContractBuilder()
        report = builder.build(plan, bundles, profiles)
        
        assert isinstance(report, EngineeringContractReport)
        assert len(report.contracts) >= 3
        assert report.deterministic is True
        for contract in report.contracts:
            assert contract.contract_id.startswith("ctr-")
            assert contract.objective


# ---------------------------------------------------------------------------
# E2.1.5 - Error handling and edge cases
# ---------------------------------------------------------------------------

class TestContractErrorHandling:
    """Test contract builder error handling."""

    def test_empty_plan_raises_error(self, registry_and_resolver):
        """Building with empty plan must fail fast."""
        plan = _make_plan(
            plan_id="plan-empty",
            mission_id="msn-empty",
            project_goal="",
            technology_stack=[],
            required_disciplines=[],
            required_deliverables=[],
        )
        bundles, profiles = _build_pipeline(registry_and_resolver, plan)
        
        builder = EngineeringContractBuilder()
        with pytest.raises(ContractValidationError):
            builder.build(plan, bundles, profiles)

    def test_determinism_same_inputs_same_output(self, registry_and_resolver):
        """Identical plans must produce identical contracts."""
        plan = _make_plan(
            plan_id="plan-det",
            mission_id="msn-det",
            project_goal="Determinism test",
            technology_stack=["Python", "FastAPI"],
            required_disciplines=["Backend"],
            required_deliverables=["REST API"],
        )
        
        result1 = _run_full_pipeline(registry_and_resolver, plan)
        result2 = _run_full_pipeline(registry_and_resolver, plan)
        
        assert result1.contract_ids == result2.contract_ids
        assert result1.contract_count == result2.contract_count
        assert result1.deterministic is True
        assert result2.deterministic is True
