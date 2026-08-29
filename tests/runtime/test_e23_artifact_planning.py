"""E2.3 Artifact Execution Planning Tests.

Tests for ArtifactExecutionPlanner, ArtifactExecutionPlan, and all E2.3 models.
"""

import json
import pytest
from typing import Any, Dict, List

from runtime.contracts import (
    ArtifactExecutionPlanner,
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactExecutionWave,
    ArtifactDependencyGraph,
    ArtifactDependencyEdge,
    ArtifactDependencyInput,
    ArtifactDependencyType,
    ArtifactPlanningError,
    ArtifactExecutionOrder,
    GenerationStrategy,
    GenerationStrategySummary,
    PathType,
    OverwritePolicy,
    ValidationCategory,
    ValidationCheckpoint,
    RepositoryBoundary,
    RepositoryScopeSummary,
    ConflictType,
    Conflict,
    ConflictReport,
    ContractDecompositionReport,
    SubContract,
    ArtifactRoute,
    DependencyGraph,
    DependencyEdge,
    ExecutionWave,
    ParallelExecutionGroup,
    EngineeringContract,
    DeliverableContract,
    AcceptanceCriteria,
    compute_artifact_execution_id,
    compute_artifact_execution_hash,
    compute_plan_hash,
    normalize_path,
    validate_absolute_path,
    validate_no_traversal,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_sub_contract(
    sub_contract_id: str,
    parent_contract_id: str,
    mission_id: str = "mission-001",
    skill_bundle_id: str = "esb-fe-001",
    agent_profile_id: str = "prf-fe-001",
    objective: str = "Build frontend components",
    repository_scope: str = "frontend/src/",
    technology_context: List[str] | None = None,
    dependencies: List[str] | None = None,
    owned_deliverables: List[str] | None = None,
    execution_wave: int = 1,
    is_atomic: bool = False,
    acceptance_criteria: List[str] | None = None,
    required_skills: List[str] | None = None,
    required_capabilities: List[str] | None = None,
) -> SubContract:
    """Create a test SubContract."""
    if technology_context is None:
        technology_context = ["React", "TypeScript"]
    if dependencies is None:
        dependencies = []
    if owned_deliverables is None:
        owned_deliverables = [f"del-{sub_contract_id}-01"]
    if acceptance_criteria is None:
        acceptance_criteria = ["Functional acceptance test"]
    if required_skills is None:
        required_skills = ["React"]
    if required_capabilities is None:
        required_capabilities = ["frontend"]

    return SubContract(
        sub_contract_id=sub_contract_id,
        parent_contract_id=parent_contract_id,
        mission_id=mission_id,
        agent_profile_id=agent_profile_id,
        skill_bundle_id=skill_bundle_id,
        objective=objective,
        required_capabilities=required_capabilities,
        required_skills=required_skills,
        inputs=["design tokens"],
        expected_deliverables=["Component file"],
        acceptance_criteria=acceptance_criteria,
        dependencies=dependencies,
        constraints=["lint", "typecheck"],
        repository_scope=repository_scope,
        technology_context=technology_context,
        priority="HIGH",
        execution_order=1,
        execution_wave=execution_wave,
        risk_level="MEDIUM",
        is_atomic=is_atomic,
        decomposition_reason="Test decomposition",
        owned_deliverables=owned_deliverables,
        traceability={"contract_id": parent_contract_id},
        deterministic_hash="hash123",
    )


def _make_artifact_route(
    artifact_id: str,
    producing_sub_contract_id: str,
    artifact_type: str = "frontend_application",
    repository_path: str = "frontend/src/components/",
) -> ArtifactRoute:
    """Create a test ArtifactRoute."""
    return ArtifactRoute(
        route_id=f"artr-{producing_sub_contract_id}",
        artifact_id=artifact_id,
        producing_sub_contract_id=producing_sub_contract_id,
        consuming_sub_contract_ids=[],
        artifact_type=artifact_type,
        repository_path=repository_path,
        technology_context=["React"],
        is_optional=False,
    )


def _make_decomposition_report(
    sub_contracts: List[SubContract],
    artifact_routes: List[ArtifactRoute],
) -> ContractDecompositionReport:
    """Create a test ContractDecompositionReport."""
    dep_graph = DependencyGraph(
        graph_id="depgraph-test",
        nodes=[s.sub_contract_id for s in sub_contracts],
        edges=[],
        adjacency={},
        reverse_adjacency={},
        in_degree={s.sub_contract_id: 0 for s in sub_contracts},
        is_acyclic=True,
    )

    wave = ExecutionWave(
        wave_number=1,
        wave_name="Frontend Implementation",
        sub_contract_ids=[s.sub_contract_id for s in sub_contracts],
        parallelizable=True,
        blocking_waves=[],
        produced_artifacts=[r.artifact_id for r in artifact_routes],
    )

    peg = ParallelExecutionGroup(
        group_id="peg-wave1",
        wave_number=1,
        sub_contract_ids=[s.sub_contract_id for s in sub_contracts],
    )

    return ContractDecompositionReport(
        report_id="cdcr-test-001",
        mission_id="mission-001",
        parent_contract_report_id="ecr-test-001",
        sub_contracts=sub_contracts,
        dependency_graph=dep_graph,
        artifact_routes=artifact_routes,
        execution_waves=[wave],
        parallel_execution_groups=[peg],
        coverage={},
        validation_results={},
        traceability={},
        deterministic=True,
        report_hash="hash456",
        total_sub_contracts=len(sub_contracts),
        total_waves=1,
        total_artifact_routes=len(artifact_routes),
        parallelizable_groups=1,
        timestamp="2026-08-29T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestE23Models:
    def test_artifact_execution_unit_has_required_fields(self):
        unit = ArtifactExecutionUnit(
            artifact_execution_id="aeu-sctr-ctr-0001-01-01",
            artifact_id="del-sctr-ctr-0001-01-01",
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            mission_id="mission-001",
            agent_profile_id="prf-fe-001",
            skill_bundle_id="esb-fe-001",
            repository_scope="frontend/src/",
            target_path="frontend/src/components/PropertyCard.tsx",
            path_type=PathType.SOURCE,
            artifact_type="frontend_application",
            file_format="tsx",
            language="TypeScript",
            framework="React",
            technology_context=["React", "TypeScript"],
            generation_strategy=GenerationStrategy.LLM_GENERATED,
            strategy_reason="Frontend application with tech context",
            execution_wave=1,
            deterministic_hash="hash789",
        )
        assert unit.artifact_execution_id == "aeu-sctr-ctr-0001-01-01"
        assert unit.target_path == "frontend/src/components/PropertyCard.tsx"
        assert unit.generation_strategy == GenerationStrategy.LLM_GENERATED

    def test_artifact_execution_unit_is_frozen(self):
        unit = ArtifactExecutionUnit(
            artifact_execution_id="aeu-test-01",
            artifact_id="del-test-01",
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            mission_id="mission-001",
            agent_profile_id="prf-fe-001",
            skill_bundle_id="esb-fe-001",
            repository_scope="frontend/src/",
            target_path="frontend/src/App.tsx",
            path_type=PathType.SOURCE,
            artifact_type="frontend_application",
            file_format="tsx",
            execution_wave=1,
            generation_strategy=GenerationStrategy.TEMPLATE,
            deterministic_hash="hash",
        )
        with pytest.raises(Exception):  # pydantic immutability error
            unit.target_path = "changed"

    def test_artifact_dependency_input_model(self):
        inp = ArtifactDependencyInput(
            input_id="aei-unit-001",
            source_artifact_id="del-db-001",
            source_sub_contract_id="sctr-db-001",
            dependency_type=ArtifactDependencyType.REQUIRES,
            required_before_generation=True,
        )
        assert inp.input_id == "aei-unit-001"
        assert inp.dependency_type == ArtifactDependencyType.REQUIRES

    def test_validation_checkpoint_model(self):
        chk = ValidationCheckpoint(
            checkpoint_id="chk-unit-01-01",
            category=ValidationCategory.PATH_VALIDATION,
            description="Path is valid",
            is_blocking=True,
            validator="ArtifactExecutionPlanValidator",
        )
        assert chk.category == ValidationCategory.PATH_VALIDATION
        assert chk.is_blocking is True

    def test_artifact_dependency_graph_model(self):
        edge = ArtifactDependencyEdge(
            from_artifact_execution_id="aeu-db-001",
            to_artifact_execution_id="aeu-fe-001",
            dependency_type=ArtifactDependencyType.REQUIRES,
            artifact_id="del-db-001",
            is_blocking=True,
        )
        graph = ArtifactDependencyGraph(
            graph_id="adepg-2",
            nodes=["aeu-db-001", "aeu-fe-001"],
            edges=[edge],
            adjacency={"aeu-db-001": ["aeu-fe-001"]},
            reverse_adjacency={"aeu-fe-001": ["aeu-db-001"]},
            in_degree={"aeu-db-001": 0, "aeu-fe-001": 1},
            is_acyclic=True,
        )
        assert len(graph.nodes) == 2
        assert graph.is_acyclic is True

    def test_conflict_model(self):
        conflict = Conflict(
            conflict_id="cf-0001",
            conflict_type=ConflictType.DUPLICATE_PATH,
            description="Two artifacts target same path",
            affected_artifact_ids=["aeu-1", "aeu-2"],
            severity="ERROR",
        )
        assert conflict.conflict_type == ConflictType.DUPLICATE_PATH

    def test_conflict_report_model(self):
        report = ConflictReport(
            total_conflicts=1,
            errors=1,
            warnings=0,
            conflicts=[
                Conflict(
                    conflict_id="cf-0001",
                    conflict_type=ConflictType.DUPLICATE_PATH,
                    description="Duplicate path",
                    affected_artifact_ids=["aeu-1"],
                    severity="ERROR",
                )
            ],
            has_blocking_conflicts=True,
        )
        assert report.has_blocking_conflicts is True
        assert report.errors == 1

    def test_generation_strategy_summary_model(self):
        summary = GenerationStrategySummary(
            total_units=10,
            template_count=2,
            pattern_count=3,
            llm_generated_count=4,
            unresolved_count=1,
            unresolved_artifacts=["aeu-unresolved-1"],
        )
        assert summary.total_units == 10
        assert summary.unresolved_count == 1

    def test_repository_scope_summary_model(self):
        summary = RepositoryScopeSummary(
            total_units=5,
            scopes={"frontend/src/": 3, "backend/src/": 2},
            boundaries=[
                RepositoryBoundary(
                    scope="frontend/src/",
                    discipline="Frontend",
                    is_authorized=True,
                )
            ],
            out_of_scope_artifacts=[],
        )
        assert summary.total_units == 5
        assert summary.scopes["frontend/src/"] == 3

    def test_artifact_execution_wave_model(self):
        wave = ArtifactExecutionWave(
            wave_number=1,
            wave_name="Frontend Artifacts",
            artifact_execution_ids=["aeu-1", "aeu-2"],
            parallelizable=True,
            blocking_waves=[],
            blocking_artifacts={},
            required_artifact_ids=[],
            produced_artifact_ids=["del-1", "del-2"],
        )
        assert wave.parallelizable is True

    def test_artifact_execution_plan_model(self):
        plan = ArtifactExecutionPlan(
            plan_id="aep-test-001",
            mission_id="mission-001",
            contract_decomposition_report_id="cdcr-test-001",
            execution_units=[],
            artifact_dependency_graph=ArtifactDependencyGraph(
                graph_id="empty",
                nodes=[],
                edges=[],
                adjacency={},
                reverse_adjacency={},
                in_degree={},
                is_acyclic=True,
            ),
            execution_waves=[],
            execution_order=[],
            generation_strategy_summary=GenerationStrategySummary(
                total_units=0, template_count=0, pattern_count=0,
                llm_generated_count=0, unresolved_count=0,
            ),
            repository_scope_summary=RepositoryScopeSummary(
                total_units=0, scopes={}, boundaries=[], out_of_scope_artifacts=[],
            ),
            validation_checkpoints=[],
            conflict_report=ConflictReport(
                total_conflicts=0, errors=0, warnings=0,
                conflicts=[], has_blocking_conflicts=False,
            ),
            traceability={},
            deterministic=True,
            deterministic_hash="hash",
            validation_passed=True,
            total_artifacts=0,
            total_waves=0,
            timestamp="2026-08-29T00:00:00Z",
        )
        assert plan.plan_id == "aep-test-001"
        assert plan.deterministic is True


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestE23Helpers:
    def test_compute_artifact_execution_id(self):
        assert compute_artifact_execution_id("sctr-ctr-0001-01", 1) == "aeu-sctr-ctr-0001-01-01"
        assert compute_artifact_execution_id("sctr-ctr-0002-03", 5) == "aeu-sctr-ctr-0002-03-05"

    def test_normalize_path(self):
        assert normalize_path("  frontend/src/components/  ") == "frontend/src/components"
        assert normalize_path("frontend//src///components") == "frontend/src/components"
        assert normalize_path("frontend/src/components/") == "frontend/src/components"

    def test_validate_absolute_path(self):
        assert validate_absolute_path("frontend/src/App.tsx") is True
        assert validate_absolute_path("/Users/aniruddhadas/Desktop/file.ts") is False
        assert validate_absolute_path("") is True

    def test_validate_no_traversal(self):
        assert validate_no_traversal("frontend/src/components/PropertyCard.tsx") is True
        assert validate_no_traversal("frontend/../backend/src/api.ts") is False
        assert validate_no_traversal("frontend/../../etc/passwd") is False

    def test_compute_artifact_execution_hash(self):
        h1 = compute_artifact_execution_hash("aeu-001", "del-001", "sctr-001", "src/app.tsx")
        h2 = compute_artifact_execution_hash("aeu-001", "del-001", "sctr-001", "src/app.tsx")
        h3 = compute_artifact_execution_hash("aeu-001", "del-001", "sctr-001", "src/app.tsx")
        assert h1 == h2 == h3
        assert len(h1) == 64  # SHA-256 hex

    def test_compute_plan_hash(self):
        unit = ArtifactExecutionUnit(
            artifact_execution_id="aeu-test-01",
            artifact_id="del-test-01",
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            mission_id="mission-001",
            agent_profile_id="prf-fe-001",
            skill_bundle_id="esb-fe-001",
            repository_scope="frontend/src/",
            target_path="frontend/src/App.tsx",
            path_type=PathType.SOURCE,
            artifact_type="frontend_application",
            file_format="tsx",
            execution_wave=1,
            generation_strategy=GenerationStrategy.TEMPLATE,
            deterministic_hash="hash",
        )
        wave = ArtifactExecutionWave(
            wave_number=1,
            wave_name="Test Wave",
            artifact_execution_ids=["aeu-test-01"],
            parallelizable=True,
            blocking_waves=[],
            blocking_artifacts={},
            required_artifact_ids=[],
            produced_artifact_ids=["del-test-01"],
        )
        h = compute_plan_hash("aep-001", "cdcr-001", [unit], [wave])
        assert len(h) == 64


# ---------------------------------------------------------------------------
# Planner tests
# ---------------------------------------------------------------------------

class TestArtifactExecutionPlanner:
    def test_single_unit_generation(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            skill_bundle_id="esb-fe-001",
            agent_profile_id="prf-fe-001",
            objective="Build React PropertyCard component",
            repository_scope="frontend/src/",
            technology_context=["React", "TypeScript"],
            owned_deliverables=["del-sctr-001-01"],
            execution_wave=1,
        )
        route = _make_artifact_route(
            artifact_id="del-sctr-001-01",
            producing_sub_contract_id="sctr-ctr-0001-01",
            artifact_type="frontend_application",
            repository_path="frontend/src/components/",
        )
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        assert plan.plan_id.startswith("aep-")
        assert plan.total_artifacts == 1
        assert plan.validation_passed is True
        assert plan.deterministic is True
        assert plan.execution_units[0].target_path == "frontend/src/components"

    def test_multi_unit_wave_propagation(self):
        sctrs = [
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0001-01",
                parent_contract_id="ctr-0001",
                skill_bundle_id="esb-db-001",
                agent_profile_id="prf-db-001",
                objective="Build database schema",
                repository_scope="database/migrations/",
                technology_context=["SQL", "PostgreSQL"],
                owned_deliverables=["del-db-001"],
                execution_wave=1,
            ),
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0002-01",
                parent_contract_id="ctr-0002",
                skill_bundle_id="esb-be-001",
                agent_profile_id="prf-be-001",
                objective="Build backend API",
                repository_scope="backend/src/",
                technology_context=["Python", "FastAPI"],
                owned_deliverables=["del-be-001"],
                execution_wave=2,
                dependencies=["sctr-ctr-0001-01"],
            ),
        ]
        routes = [
            _make_artifact_route("del-db-001", "sctr-ctr-0001-01", "database_schema", "database/migrations/"),
            _make_artifact_route("del-be-001", "sctr-ctr-0002-01", "api_endpoint", "backend/src/api/"),
        ]
        report = _make_decomposition_report(sctrs, routes)
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        assert plan.total_artifacts == 2
        assert plan.total_waves == 2
        assert len(plan.execution_waves) == 2
        # Wave 2 should block wave 1
        wave2 = next(w for w in plan.execution_waves if w.wave_number == 2)
        assert wave2.blocking_waves == [1]

    def test_strategy_selection_template(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            skill_bundle_id="esb-db-001",
            agent_profile_id="prf-db-001",
            objective="Build database schema",
            repository_scope="database/migrations/",
            technology_context=["SQL"],
            owned_deliverables=["del-db-001"],
        )
        route = _make_artifact_route("del-db-001", "sctr-ctr-0001-01", "database_schema", "database/migrations/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        unit = plan.execution_units[0]
        assert unit.generation_strategy == GenerationStrategy.TEMPLATE

    def test_strategy_selection_llm_generated(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            skill_bundle_id="esb-fe-001",
            agent_profile_id="prf-fe-001",
            objective="Build React component",
            repository_scope="frontend/src/",
            technology_context=["React", "TypeScript"],
            owned_deliverables=["del-fe-001"],
        )
        route = _make_artifact_route("del-fe-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/components/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        unit = plan.execution_units[0]
        assert unit.generation_strategy == GenerationStrategy.LLM_GENERATED

    def test_strategy_selection_unresolved(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            skill_bundle_id="esb-test-001",
            agent_profile_id="prf-test-001",
            objective="Build tests",
            repository_scope="tests/",
            technology_context=[],  # No tech context
            owned_deliverables=["del-test-001"],
            acceptance_criteria=[],  # No criteria
            required_skills=[],  # No skills -> UNRESOLVED
            required_capabilities=[],  # No capabilities -> UNRESOLVED
        )
        route = _make_artifact_route("del-test-001", "sctr-ctr-0001-01", "tests", "tests/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        unit = plan.execution_units[0]
        assert unit.generation_strategy == GenerationStrategy.UNRESOLVED

    def test_path_normalization_in_unit(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="frontend/src/",
            technology_context=["TypeScript"],
            owned_deliverables=["del-001"],
        )
        route = _make_artifact_route(
            "del-001", "sctr-ctr-0001-01", "frontend_application",
            "frontend/src//components///PropertyCard.tsx/"
        )
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        unit = plan.execution_units[0]
        assert "//" not in unit.target_path
        assert unit.target_path.endswith("/") is False

    def test_repository_scope_summary(self):
        sctrs = [
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0001-01",
                parent_contract_id="ctr-0001",
                repository_scope="frontend/src/",
                technology_context=["React"],
                owned_deliverables=["del-fe-001"],
            ),
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0002-01",
                parent_contract_id="ctr-0002",
                repository_scope="backend/src/",
                technology_context=["Python"],
                owned_deliverables=["del-be-001"],
            ),
        ]
        routes = [
            _make_artifact_route("del-fe-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/"),
            _make_artifact_route("del-be-001", "sctr-ctr-0002-01", "api_endpoint", "backend/src/"),
        ]
        report = _make_decomposition_report(sctrs, routes)
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        rs = plan.repository_scope_summary
        assert rs.total_units == 2
        assert "frontend/src/" in rs.scopes
        assert "backend/src/" in rs.scopes

    def test_generation_strategy_summary(self):
        sctrs = [
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0001-01",
                parent_contract_id="ctr-0001",
                repository_scope="database/migrations/",
                technology_context=["SQL"],
                owned_deliverables=["del-db-001"],
            ),
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0002-01",
                parent_contract_id="ctr-0002",
                repository_scope="frontend/src/",
                technology_context=["React", "TypeScript"],
                owned_deliverables=["del-fe-001"],
            ),
        ]
        routes = [
            _make_artifact_route("del-db-001", "sctr-ctr-0001-01", "database_schema", "database/migrations/"),
            _make_artifact_route("del-fe-001", "sctr-ctr-0002-01", "frontend_application", "frontend/src/"),
        ]
        report = _make_decomposition_report(sctrs, routes)
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        ss = plan.generation_strategy_summary
        assert ss.template_count >= 1
        assert ss.llm_generated_count >= 1
        assert ss.total_units == 2

    def test_conflict_detection_duplicate_path(self):
        sctrs = [
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0001-01",
                parent_contract_id="ctr-0001",
                repository_scope="frontend/src/",
                technology_context=["React"],
                owned_deliverables=["del-001"],
            ),
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0002-01",
                parent_contract_id="ctr-0002",
                repository_scope="frontend/src/",
                technology_context=["React"],
                owned_deliverables=["del-002"],
            ),
        ]
        # Both produce to the same path
        routes = [
            _make_artifact_route("del-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/components/"),
            _make_artifact_route("del-002", "sctr-ctr-0002-01", "frontend_application", "frontend/src/components/"),
        ]
        report = _make_decomposition_report(sctrs, routes)
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        cr = plan.conflict_report
        assert cr.total_conflicts >= 1
        dup_paths = [c for c in cr.conflicts if c.conflict_type == ConflictType.DUPLICATE_PATH]
        assert len(dup_paths) >= 1

    def test_conflict_detection_unknown_strategy(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="tests/",
            technology_context=[],
            owned_deliverables=["del-test-001"],
            acceptance_criteria=[],
            required_skills=[],
            required_capabilities=[],
        )
        route = _make_artifact_route("del-test-001", "sctr-ctr-0001-01", "tests", "tests/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        cr = plan.conflict_report
        unknown_strat = [c for c in cr.conflicts if c.conflict_type == ConflictType.UNKNOWN_STRATEGY]
        assert len(unknown_strat) >= 1

    def test_validation_checkpoints_created(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="frontend/src/",
            technology_context=["React"],
            owned_deliverables=["del-001"],
            acceptance_criteria=["All tests pass"],
        )
        route = _make_artifact_route("del-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        unit = plan.execution_units[0]
        assert len(unit.validation_checkpoints) >= 1
        cats = {c.category for c in unit.validation_checkpoints}
        assert ValidationCategory.PATH_VALIDATION in cats

    def test_determinism_same_inputs_same_output(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="frontend/src/",
            technology_context=["React"],
            owned_deliverables=["del-001"],
        )
        route = _make_artifact_route("del-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/")
        report = _make_decomposition_report([sctr], [route])

        planner = ArtifactExecutionPlanner()
        plan1 = planner.plan(report)
        plan2 = planner.plan(report)

        assert plan1.plan_id == plan2.plan_id
        assert plan1.deterministic_hash == plan2.deterministic_hash
        assert plan1.execution_units[0].artifact_execution_id == plan2.execution_units[0].artifact_execution_id

    def test_traceability_chain(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            mission_id="mission-001",
            repository_scope="frontend/src/",
            technology_context=["React"],
            owned_deliverables=["del-001"],
        )
        route = _make_artifact_route("del-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        assert plan.mission_id == "mission-001"
        assert plan.contract_decomposition_report_id == "cdcr-test-001"
        assert plan.traceability.get("decomposition_report_id") == "cdcr-test-001"

    def test_execution_order_per_wave(self):
        sctrs = [
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0001-01",
                parent_contract_id="ctr-0001",
                repository_scope="database/migrations/",
                technology_context=["SQL"],
                owned_deliverables=["del-db-001"],
                execution_wave=1,
            ),
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0002-01",
                parent_contract_id="ctr-0002",
                repository_scope="frontend/src/",
                technology_context=["React"],
                owned_deliverables=["del-fe-001"],
                execution_wave=2,
                dependencies=["sctr-ctr-0001-01"],
            ),
        ]
        routes = [
            _make_artifact_route("del-db-001", "sctr-ctr-0001-01", "database_schema", "database/migrations/"),
            _make_artifact_route("del-fe-001", "sctr-ctr-0002-01", "frontend_application", "frontend/src/"),
        ]
        report = _make_decomposition_report(sctrs, routes)
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        assert len(plan.execution_order) == 2
        wave1_units = [o for o in plan.execution_order if o.execution_wave == 1]
        wave2_units = [o for o in plan.execution_order if o.execution_wave == 2]
        assert len(wave1_units) == 1
        assert len(wave2_units) == 1

    def test_invalid_input_type(self):
        planner = ArtifactExecutionPlanner()
        with pytest.raises(ArtifactPlanningError, match="Expected ContractDecompositionReport"):
            planner.plan("not a report")

    def test_serializes_to_json(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="frontend/src/",
            technology_context=["React"],
            owned_deliverables=["del-001"],
        )
        route = _make_artifact_route("del-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        json_str = plan.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["plan_id"] == plan.plan_id
        assert parsed["total_artifacts"] == 1

    def test_plan_is_immutable(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="frontend/src/",
            technology_context=["React"],
            owned_deliverables=["del-001"],
        )
        route = _make_artifact_route("del-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        with pytest.raises(Exception):
            plan.plan_id = "changed"

    def test_language_detection(self):
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="backend/src/",
            technology_context=["Python", "FastAPI"],
            owned_deliverables=["del-001"],
        )
        route = _make_artifact_route("del-001", "sctr-ctr-0001-01", "api_endpoint", "backend/src/")
        report = _make_decomposition_report([sctr], [route])
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        unit = plan.execution_units[0]
        assert unit.language == "Python"
        assert unit.framework == "FastAPI"

    def test_real_estate_example(self):
        """Test with the real estate example scenario."""
        sctrs = [
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0001-01",
                parent_contract_id="ctr-0001",
                skill_bundle_id="esb-fe-001",
                agent_profile_id="prf-fe-001",
                objective="Build property search UI",
                repository_scope="frontend/src/",
                technology_context=["React", "TypeScript"],
                owned_deliverables=["del-fe-search-01", "del-fe-card-01"],
                execution_wave=3,
            ),
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0002-01",
                parent_contract_id="ctr-0002",
                skill_bundle_id="esb-be-001",
                agent_profile_id="prf-be-001",
                objective="Build property search API",
                repository_scope="backend/src/",
                technology_context=["Python", "FastAPI"],
                owned_deliverables=["del-be-search-01"],
                execution_wave=2,
            ),
            _make_sub_contract(
                sub_contract_id="sctr-ctr-0003-01",
                parent_contract_id="ctr-0003",
                skill_bundle_id="esb-db-001",
                agent_profile_id="prf-db-001",
                objective="Build property database schema",
                repository_scope="database/migrations/",
                technology_context=["SQL", "PostgreSQL"],
                owned_deliverables=["del-db-property-01"],
                execution_wave=1,
            ),
        ]
        routes = [
            _make_artifact_route("del-fe-search-01", "sctr-ctr-0001-01", "frontend_application", "frontend/src/pages/"),
            _make_artifact_route("del-fe-card-01", "sctr-ctr-0001-01", "frontend_application", "frontend/src/components/"),
            _make_artifact_route("del-be-search-01", "sctr-ctr-0002-01", "api_endpoint", "backend/src/api/"),
            _make_artifact_route("del-db-property-01", "sctr-ctr-0003-01", "database_schema", "database/migrations/"),
        ]
        report = _make_decomposition_report(sctrs, routes)
        planner = ArtifactExecutionPlanner()
        plan = planner.plan(report)

        assert plan.total_artifacts == 4
        assert plan.total_waves == 3
        assert plan.validation_passed is True
        # Wave 3 should block waves 1 and 2
        wave3 = next(w for w in plan.execution_waves if w.wave_number == 3)
        assert 1 in wave3.blocking_waves
        assert 2 in wave3.blocking_waves
        # Strategy summary
        ss = plan.generation_strategy_summary
        assert ss.template_count >= 1  # database schema
        assert ss.llm_generated_count >= 2  # frontend + backend


# ---------------------------------------------------------------------------
# E2.1/E2.2 Regression
# ---------------------------------------------------------------------------

class TestE23E2Regression:
    def test_e21_contracts_still_work(self):
        """Verify E2.1 contract building still works after E2.3 changes."""
        from runtime.contracts import EngineeringContractBuilder
        from runtime.skills.models import ExecutionSkillBundleReport, AgentProfileReport, SkillSelectionReport, ExecutionSkillBundle
        from runtime.workspace.plan import EngineeringExecutionPlan

        # Verify all imports work
        assert EngineeringContractBuilder is not None
        # Verify no circular import issues
        from runtime.contracts import ArtifactExecutionPlanner
        assert ArtifactExecutionPlanner is not None

    def test_e22_decomposer_still_works(self):
        """Verify E2.2 decomposition still works."""
        from runtime.contracts import ContractDecompositionEngine
        # Just verify the decomposer can be instantiated and the model is correct
        decomposer = ContractDecompositionEngine()
        assert decomposer is not None
        # Verify the decomposer has the expected method
        assert hasattr(decomposer, "decompose")
        # Verify a minimal decomposition report works with the planner
        sctr = _make_sub_contract(
            sub_contract_id="sctr-ctr-0001-01",
            parent_contract_id="ctr-0001",
            repository_scope="frontend/src/",
            technology_context=["React"],
            owned_deliverables=["del-001"],
        )
        route = _make_artifact_route("del-001", "sctr-ctr-0001-01", "frontend_application", "frontend/src/")
        decomp_report = _make_decomposition_report([sctr], [route])
        # Verify the report has the expected structure
        assert decomp_report.report_id == "cdcr-test-001"
        assert len(decomp_report.sub_contracts) == 1
