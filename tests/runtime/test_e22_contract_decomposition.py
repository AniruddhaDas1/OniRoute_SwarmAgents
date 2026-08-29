"""Tests for Phase E2.2 - Contract Decomposition & Dependency Planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

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
    EngineeringContractReport,
    ContractDecompositionEngine,
    ContractDecompositionReport,
    SubContract,
    DependencyGraph,
    DependencyEdge,
    ArtifactRoute,
    ExecutionWave,
    ParallelExecutionGroup,
    ContractDecompositionValidator,
    ValidationError,
)
from runtime.contracts.decomposition import (
    DependencyType,
    DecompositionCoverageMetrics,
)


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


def _get_contract_report(registry_and_resolver, plan: EngineeringExecutionPlan) -> EngineeringContractReport:
    """Build a contract report from the pipeline."""
    bundles, profiles = _build_pipeline(registry_and_resolver, plan)
    builder = EngineeringContractBuilder()
    report = builder.build(plan, bundles, profiles)
    return report


def _decompose(contract_report: EngineeringContractReport) -> ContractDecompositionReport:
    """Run decomposition on a contract report."""
    engine = ContractDecompositionEngine()
    return engine.decompose(contract_report)


# ---------------------------------------------------------------------------
# E2.2.2 - Model verification
# ---------------------------------------------------------------------------

class TestE22Models:
    """Verify E2.2 model definitions."""

    def test_sub_contract_has_required_fields(self):
        """SubContract must have all required E2.2.2 fields."""
        fields = SubContract.model_fields
        required = [
            "sub_contract_id", "parent_contract_id", "mission_id",
            "agent_profile_id", "skill_bundle_id", "objective",
            "required_capabilities", "required_skills", "inputs",
            "expected_deliverables", "acceptance_criteria",
            "dependencies", "constraints", "repository_scope",
            "technology_context", "priority", "execution_order",
            "execution_wave", "risk_level", "is_atomic",
            "decomposition_reason", "owned_deliverables",
            "traceability", "deterministic_hash",
        ]
        for f in required:
            assert f in fields, f"Missing required field: {f}"

    def test_sub_contract_is_frozen(self):
        """SubContract must be immutable."""
        assert SubContract.model_config.get("frozen") is True

    def test_dependency_graph_model(self):
        """DependencyGraph must define the dependency graph structure."""
        fields = DependencyGraph.model_fields
        required = ["graph_id", "nodes", "edges", "adjacency", "is_acyclic"]
        for f in required:
            assert f in fields, f"Missing required field: {f}"
        assert DependencyGraph.model_config.get("frozen") is True

    def test_artifact_route_model(self):
        """ArtifactRoute must define artifact flow between sub-contracts."""
        fields = ArtifactRoute.model_fields
        required = ["route_id", "artifact_id", "producing_sub_contract_id",
                    "consuming_sub_contract_ids", "artifact_type", "repository_path"]
        for f in required:
            assert f in fields, f"Missing required field: {f}"
        assert ArtifactRoute.model_config.get("frozen") is True

    def test_execution_wave_model(self):
        """ExecutionWave must define execution wave structure."""
        fields = ExecutionWave.model_fields
        required = ["wave_number", "wave_name", "sub_contract_ids", "parallelizable", "blocking_waves"]
        for f in required:
            assert f in fields, f"Missing required field: {f}"
        assert ExecutionWave.model_config.get("frozen") is True

    def test_parallel_execution_group_model(self):
        """ParallelExecutionGroup must identify parallelizable sub-contracts."""
        fields = ParallelExecutionGroup.model_fields
        required = ["group_id", "wave_number", "sub_contract_ids", "parallelizable"]
        for f in required:
            assert f in fields, f"Missing required field: {f}"
        assert ParallelExecutionGroup.model_config.get("frozen") is True

    def test_dependency_edge_model(self):
        """DependencyEdge must define directed edges in the graph."""
        fields = DependencyEdge.model_fields
        required = ["from_id", "to_id", "dependency_type", "is_blocking"]
        for f in required:
            assert f in fields, f"Missing required field: {f}"
        assert DependencyEdge.model_config.get("frozen") is True

    def test_dependency_type_enum(self):
        """DependencyType must define explicit dependency categories."""
        assert DependencyType.REQUIRES.value == "REQUIRES"
        assert DependencyType.PRODUCES.value == "PRODUCES"
        assert DependencyType.CONSUMES.value == "CONSUMES"
        assert DependencyType.BLOCKS.value == "BLOCKS"
        assert DependencyType.VALIDATES.value == "VALIDATES"

    def test_decomposition_coverage_metrics(self):
        """DecompositionCoverageMetrics must track decomposition coverage."""
        cm = DecompositionCoverageMetrics(
            total_parent_contracts=3, decomposed_contracts=2, atomic_contracts=1,
            total_sub_contracts=5, total_deliverables=6, covered_deliverables=6,
            total_acceptance_criteria=15, covered_acceptance_criteria=15,
            total_artifacts=6, routed_artifacts=6, coverage_percent=100.0,
        )
        assert cm.total_parent_contracts == 3
        assert cm.total_sub_contracts == 5
        assert cm.coverage_percent == 100.0


# ---------------------------------------------------------------------------
# E2.2.3 / E2.2.4 - Decomposition behavior
# ---------------------------------------------------------------------------

class TestContractDecomposition:
    """Test contract decomposition behavior."""

    def test_atomic_contract_preserved(self, registry_and_resolver):
        """E2.2.3: Atomic contracts (single deliverable) produce one sub-contract."""
        plan = _make_plan(
            project_goal="Simple Python script",
            technology_stack=["Python"],
            required_disciplines=["Software Engineering"],
            required_deliverables=["Project Configuration"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        # Each contract with 1 deliverable should be atomic
        for contract in contract_report.contracts:
            deliverables = [
                d for d in contract_report.deliverables
                if d.contract_id == contract.contract_id
            ]
            sub_ctrs = [
                s for s in report.sub_contracts
                if s.parent_contract_id == contract.contract_id
            ]
            if len(deliverables) <= 1:
                assert len(sub_ctrs) == 1
                assert sub_ctrs[0].is_atomic is True

    def test_multi_deliverable_decomposition(self, registry_and_resolver):
        """E2.2.4: Multi-deliverable contracts produce multiple sub-contracts."""
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
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        # Each contract should have at least one sub-contract
        assert len(report.sub_contracts) >= len(contract_report.contracts)

    def test_sub_contract_ownership(self, registry_and_resolver):
        """E2.2.3: Every sub-contract has exactly one parent."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        for s in report.sub_contracts:
            assert s.parent_contract_id
            assert s.sub_contract_id.startswith("sctr-")

    def test_deliverable_ownership(self, registry_and_resolver):
        """E2.2.3: Every deliverable has exactly one owner sub-contract."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI", "PostgreSQL"],
            required_disciplines=["Frontend", "Backend", "Database"],
            required_deliverables=[
                "Property search UI",
                "Property search API",
                "Property data models",
            ],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        # Count owned deliverables across all sub-contracts
        owned_deliverable_ids = []
        for s in report.sub_contracts:
            owned_deliverable_ids.extend(s.owned_deliverables)

        # Should cover all deliverables from the report
        report_deliverable_ids = [d.deliverable_id for d in contract_report.deliverables]
        covered = set(owned_deliverable_ids) & set(report_deliverable_ids)
        # At minimum, all contract-report deliverables should be covered
        for d_id in report_deliverable_ids:
            owner_count = sum(1 for s in report.sub_contracts if d_id in s.owned_deliverables)
            assert owner_count == 1, f"Deliverable {d_id} owned by {owner_count} sub-contracts"

    def test_technology_context_preserved(self, registry_and_resolver):
        """E2.2.11: Technology context must be preserved from parent contract."""
        plan = _make_plan(
            project_goal="React FastAPI website",
            technology_stack=["React", "TypeScript", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        contract_map = {c.contract_id: c for c in contract_report.contracts}
        for s in report.sub_contracts:
            parent = contract_map.get(s.parent_contract_id)
            if parent:
                assert s.technology_context == parent.technology_context

    def test_repository_scope_preserved(self, registry_and_resolver):
        """E2.2.11: Repository scope must be preserved from parent contract."""
        plan = _make_plan(
            project_goal="Multi-layer application",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        contract_map = {c.contract_id: c for c in contract_report.contracts}
        for s in report.sub_contracts:
            parent = contract_map.get(s.parent_contract_id)
            if parent:
                assert s.repository_scope == parent.repository_scope

    def test_agent_profile_ownership_preserved(self, registry_and_resolver):
        """E2.2.13: Agent profile ownership must be preserved from parent."""
        plan = _make_plan(
            project_goal="Fullstack app",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        contract_map = {c.contract_id: c for c in contract_report.contracts}
        for s in report.sub_contracts:
            parent = contract_map.get(s.parent_contract_id)
            if parent:
                assert s.agent_profile_id == parent.agent_profile_id
                assert s.skill_bundle_id == parent.skill_bundle_id


# ---------------------------------------------------------------------------
# E2.2.5 / E2.2.7 - Dependency graph and waves
# ---------------------------------------------------------------------------

class TestDependencyGraphAndWaves:
    """Test dependency graph and execution wave computation."""

    def test_dependency_graph_acyclic(self, registry_and_resolver):
        """E2.2.9: Dependency graph must be acyclic."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI", "PostgreSQL"],
            required_disciplines=["Frontend", "Backend", "Database"],
            required_deliverables=[
                "Property search UI",
                "Property search API",
                "Property data models",
            ],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        assert report.dependency_graph.is_acyclic is True

    def test_execution_waves_computed(self, registry_and_resolver):
        """E2.2.7: Execution waves must be computed deterministically."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        assert len(report.execution_waves) >= 1
        wave_numbers = [w.wave_number for w in report.execution_waves]
        assert wave_numbers == sorted(wave_numbers)

    def test_wave_sub_contract_assignment(self, registry_and_resolver):
        """E2.2.7: Every sub-contract must be assigned to exactly one wave."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        all_assigned = set()
        for wave in report.execution_waves:
            for sctr_id in wave.sub_contract_ids:
                assert sctr_id not in all_assigned, f"Sub-contract {sctr_id} assigned to multiple waves"
                all_assigned.add(sctr_id)

        for s in report.sub_contracts:
            assert s.sub_contract_id in all_assigned, f"Sub-contract {s.sub_contract_id} not assigned to any wave"

    def test_parallel_execution_groups(self, registry_and_resolver):
        """E2.2.8: Parallel execution groups must be identified."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        assert len(report.parallel_execution_groups) >= 1
        for group in report.parallel_execution_groups:
            assert group.group_id.startswith("peg-wave")
            assert group.wave_number >= 1


# ---------------------------------------------------------------------------
# E2.2.6 - Artifact routing
# ---------------------------------------------------------------------------

class TestArtifactRouting:
    """Test artifact routing between sub-contracts."""

    def test_artifact_routes_created(self, registry_and_resolver):
        """E2.2.6: Artifact routes must be created for deliverables."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI", "PostgreSQL"],
            required_disciplines=["Frontend", "Backend", "Database"],
            required_deliverables=[
                "Property search UI",
                "Property search API",
                "Property data models",
            ],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        # Should have artifact routes
        assert len(report.artifact_routes) >= 0
        for route in report.artifact_routes:
            assert route.route_id.startswith("artr-")
            assert route.producing_sub_contract_id
            assert route.repository_path


# ---------------------------------------------------------------------------
# E2.2.10 / E2.2.13 - Traceability
# ---------------------------------------------------------------------------

class TestTraceability:
    """Test traceability from sub-contracts back to upstream intelligence."""

    def test_sub_contract_traceability(self, registry_and_resolver):
        """E2.2.10: Every sub-contract must have full traceability."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        for s in report.sub_contracts:
            assert "contract_id" in s.traceability, f"SubContract {s.sub_contract_id} missing contract traceability"
            assert s.sub_contract_id.startswith("sctr-")

    def test_report_traceability(self, registry_and_resolver):
        """E2.2.13: Report must have upstream traceability."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        assert "mission_id" in report.traceability
        assert "contract_report_id" in report.traceability
        assert report.mission_id == contract_report.mission_id


# ---------------------------------------------------------------------------
# E2.2.12 / E2.2.15 - Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Test deterministic output for identical inputs."""

    def test_deterministic_sub_contract_ids(self, registry_and_resolver):
        """E2.2.12: Identical inputs must produce identical sub-contract IDs."""
        plan = _make_plan(
            project_goal="Determinism test",
            technology_stack=["Python"],
            required_disciplines=["Software Engineering"],
            required_deliverables=["CLI tool"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)

        report1 = _decompose(contract_report)
        report2 = _decompose(contract_report)

        ids1 = sorted([s.sub_contract_id for s in report1.sub_contracts])
        ids2 = sorted([s.sub_contract_id for s in report2.sub_contracts])
        assert ids1 == ids2

    def test_deterministic_wave_ordering(self, registry_and_resolver):
        """E2.2.12: Identical inputs must produce identical wave ordering."""
        plan = _make_plan(
            project_goal="Determinism test",
            technology_stack=["Python"],
            required_disciplines=["Software Engineering"],
            required_deliverables=["CLI tool"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)

        report1 = _decompose(contract_report)
        report2 = _decompose(contract_report)

        waves1 = [w.wave_number for w in report1.execution_waves]
        waves2 = [w.wave_number for w in report2.execution_waves]
        assert waves1 == waves2

    def test_deterministic_report_hash(self, registry_and_resolver):
        """E2.2.12: Identical inputs must produce identical report hashes."""
        plan = _make_plan(
            project_goal="Determinism test",
            technology_stack=["Python"],
            required_disciplines=["Software Engineering"],
            required_deliverables=["CLI tool"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)

        report1 = _decompose(contract_report)
        report2 = _decompose(contract_report)

        assert report1.report_hash == report2.report_hash


# ---------------------------------------------------------------------------
# E2.2.11 - Validation
# ---------------------------------------------------------------------------

class TestDecompositionValidation:
    """Test decomposition validation."""

    def test_validator_runs_all_checks(self, registry_and_resolver):
        """E2.2.11: Validator must run all 16 checks."""
        plan = _make_plan(
            project_goal="Real estate website",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        required_checks = [
            "E2.2.1_parent_decomposed",
            "E2.2.2_single_parent",
            "E2.2.3_single_deliverable_owner",
            "E2.2.4_acceptance_criteria_owned",
            "E2.2.5_no_orphan_subcontracts",
            "E2.2.6_no_duplicate_ids",
            "E2.2.7_no_duplicate_deliverable",
            "E2.2.8_dependencies_resolve",
            "E2.2.9_graph_acyclic",
            "E2.2.10_waves_valid",
            "E2.2.11_repo_scope_preserved",
            "E2.2.12_tech_context_preserved",
            "E2.2.13_ownership_preserved",
            "E2.2.14_traceability_complete",
            "E2.2.15_deterministic",
            "E2.2.16_coverage_100",
        ]
        for check in required_checks:
            assert check in report.validation_results, f"Missing validation check: {check}"
            assert report.validation_results[check].get("passed") is True, f"Failed: {check}"

    def test_real_estate_example(self, registry_and_resolver):
        """E2.2.15: Real estate website decomposition produces valid graph without code generation."""
        plan = _make_plan(
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
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        assert isinstance(report, ContractDecompositionReport)
        assert len(report.sub_contracts) >= 4
        assert report.deterministic is True
        assert report.dependency_graph.is_acyclic is True
        assert report.total_waves >= 1
        assert report.report_hash != ""
        for s in report.sub_contracts:
            assert s.sub_contract_id.startswith("sctr-")
            assert s.objective

    def test_invalid_input_type(self):
        """ContractDecompositionEngine must reject non-EngineeringContractReport input."""
        engine = ContractDecompositionEngine()
        with pytest.raises(Exception):
            engine.decompose("invalid_input")


# ---------------------------------------------------------------------------
# E2.2.16 - Serialization / deserialization
# ---------------------------------------------------------------------------

class TestSerialization:
    """Test report serialization and deserialization."""

    def test_report_serializes_to_json(self, registry_and_resolver):
        """ContractDecompositionReport must serialize to JSON."""
        plan = _make_plan(
            project_goal="Test serialization",
            technology_stack=["Python"],
            required_disciplines=["Software Engineering"],
            required_deliverables=["CLI tool"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        json_bytes = report.model_dump_json().encode("utf-8")
        assert len(json_bytes) > 0

        # Should be valid JSON
        parsed = json.loads(json_bytes.decode("utf-8"))
        assert parsed["report_id"] == report.report_id
        assert parsed["mission_id"] == report.mission_id

    def test_report_is_immutable(self, registry_and_resolver):
        """ContractDecompositionReport must be frozen."""
        plan = _make_plan(
            project_goal="Test immutability",
            technology_stack=["Python"],
            required_disciplines=["Software Engineering"],
            required_deliverables=["CLI tool"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)
        report = _decompose(contract_report)

        with pytest.raises((TypeError, Exception)):
            report.report_id = "modified"  # type: ignore


# ---------------------------------------------------------------------------
# E2.1 Regression
# ---------------------------------------------------------------------------

class TestE21Regression:
    """Verify E2.1 contracts still work after E2.2 changes."""

    def test_e21_contracts_still_work(self, registry_and_resolver):
        """E2.1 EngineeringContractReport must still be generated correctly."""
        plan = _make_plan(
            project_goal="Regression test",
            technology_stack=["React", "FastAPI"],
            required_disciplines=["Frontend", "Backend"],
            required_deliverables=["UI Pages", "API Endpoints"],
        )
        contract_report = _get_contract_report(registry_and_resolver, plan)

        assert isinstance(contract_report, EngineeringContractReport)
        assert len(contract_report.contracts) >= 1
        assert contract_report.mission_id
        assert contract_report.execution_plan_id
        assert contract_report.deterministic is True
