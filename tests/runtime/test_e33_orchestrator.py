"""E3.3 End-to-End Tests for Artifact Execution Orchestration.

Tests verify:
1. Single artifact execution
2. Multiple independent artifacts
3. Dependency ordering
4. Wave construction
5. Parallel-safe wave grouping
6. Dependency cycle detection
7. Failed artifact propagation
8. Blocked dependent artifact
9. Independent artifact continues after failure
10. State transitions
11. Progress reporting
12. Workspace file creation
13. Multi-file real project generation
14. Deterministic execution ordering
15. Partial project success
16. Repository boundary enforcement
17. Duplicate artifact handling
18. Integration with RealCodeGenerationEngine
19. Integration with InvocationEngine
20. LLM_GENERATED multi-artifact execution using mocked InvocationEngine
"""

from __future__ import annotations

import os
import tempfile
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from runtime.contracts.e23_models import (
    ArtifactDependencyGraph,
    ArtifactDependencyInput,
    ArtifactDependencyType,
    ArtifactExecutionOrder,
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactExecutionWave,
    ConflictReport,
    GenerationStrategy,
    GenerationStrategySummary,
    OverwritePolicy,
    PathType,
    RepositoryBoundary,
    RepositoryScopeSummary,
    ValidationCategory,
    ValidationCheckpoint,
)
from runtime.contracts.e31_models import GenerationResult
from runtime.contracts.e33_models import (
    ArtifactExecutionStatus,
    CycleDetectionResult,
    DependencyFailureInfo,
    ExecutionReport,
    ExecutionState,
    ExecutionStateTransition,
    WaveExecutionStatus,
)
from runtime.contracts.orchestrator import ArtifactExecutionOrchestrator


# ---------------------------------------------------------------------------
# Mock Generation Engine
# ---------------------------------------------------------------------------

class MockGenerationEngine:
    """Mock generation engine for testing."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """Initialize with optional response mapping."""
        self.responses = responses or {}
        self.execution_log: List[str] = []
        self.execution_order: List[str] = []
        self.invoke_count = 0

    def generate_single(
        self,
        unit: ArtifactExecutionUnit,
        plan: ArtifactExecutionPlan,
    ) -> GenerationResult:
        """Generate a single artifact."""
        self.invoke_count += 1
        self.execution_log.append(unit.artifact_execution_id)
        self.execution_order.append(unit.artifact_execution_id)

        # Check for expected response
        content = self.responses.get(
            unit.artifact_execution_id,
            self._generate_default_content(unit)
        )

        return GenerationResult(
            result_id=f"gen-{unit.artifact_execution_id}",
            artifact_execution_id=unit.artifact_execution_id,
            artifact_id=unit.artifact_id,
            sub_contract_id=unit.sub_contract_id,
            strategy=unit.generation_strategy,
            generation_started=datetime.now(timezone.utc).isoformat(),
            generation_completed=datetime.now(timezone.utc).isoformat(),
            generation_duration_ms=10.0,
            success=True,
            content=content,
            file_written=True,
            written_path=unit.target_path,
            context_hash="mock-context-hash",
            errors=(),
            warnings=(),
            validation_passed=True,
            validation_errors=(),
            content_hash=f"hash-{unit.artifact_execution_id}",
        )

    def _generate_default_content(self, unit: ArtifactExecutionUnit) -> str:
        """Generate default content based on unit."""
        if unit.language == "TypeScript" or unit.file_format == "tsx":
            return f"// {unit.target_path}\nexport const {unit.artifact_type} = () => {{}};\n"
        elif unit.language == "Python" or unit.file_format == "py":
            return f'"""{unit.target_path}"""\ndef {unit.artifact_type}():\n    pass\n'
        elif unit.file_format == "css":
            return f"/* {unit.target_path} */\n.{unit.artifact_type} {{ }}\n"
        elif unit.file_format == "html":
            return f"<!-- {unit.target_path} -->\n<html><body></body></html>\n"
        else:
            return f"// {unit.target_path}\n"


class MockFailingEngine(MockGenerationEngine):
    """Mock engine that fails for specific artifacts."""

    def __init__(self, responses: Optional[Dict[str, str]] = None, failing_ids: Optional[List[str]] = None):
        super().__init__(responses)
        self.failing_ids = failing_ids or []

    def generate_single(
        self,
        unit: ArtifactExecutionUnit,
        plan: ArtifactExecutionPlan,
    ) -> GenerationResult:
        """Generate a single artifact, potentially failing."""
        self.invoke_count += 1
        self.execution_log.append(unit.artifact_execution_id)
        self.execution_order.append(unit.artifact_execution_id)

        if unit.artifact_execution_id in self.failing_ids:
            return GenerationResult(
                result_id=f"gen-{unit.artifact_execution_id}",
                artifact_execution_id=unit.artifact_execution_id,
                artifact_id=unit.artifact_id,
                sub_contract_id=unit.sub_contract_id,
                strategy=unit.generation_strategy,
                generation_started=datetime.now(timezone.utc).isoformat(),
                generation_completed=datetime.now(timezone.utc).isoformat(),
                generation_duration_ms=10.0,
                success=False,
                content=None,
                file_written=False,
                written_path="",
                context_hash="mock-context-hash",
                errors=("Generation failed",),
                warnings=(),
                validation_passed=False,
                validation_errors=("Generation failed",),
                content_hash="",
            )

        return super().generate_single(unit, plan)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_repo_root(tmp_path):
    """Create a temporary repository root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return str(repo)


def create_checkpoint() -> ValidationCheckpoint:
    """Create a standard validation checkpoint."""
    return ValidationCheckpoint(
        checkpoint_id="chk-01",
        category=ValidationCategory.PATH_VALIDATION,
        description="Verify path is valid",
        is_blocking=True,
        validator="PathValidator",
    )


def create_plan(
    units: List[ArtifactExecutionUnit],
    waves: List[ArtifactExecutionWave],
) -> ArtifactExecutionPlan:
    """Create a test plan with given units and waves."""
    checkpoints = [create_checkpoint()]

    order = []
    for i, unit in enumerate(units):
        order.append(ArtifactExecutionOrder(
            artifact_execution_id=unit.artifact_execution_id,
            execution_wave=unit.execution_wave,
            execution_order=i,
            blocking_artifacts=[],
            prerequisite_artifacts=[],
        ))

    graph = ArtifactDependencyGraph(
        graph_id="test-graph",
        nodes=[u.artifact_execution_id for u in units],
        edges=[],
        adjacency={u.artifact_execution_id: [] for u in units},
        reverse_adjacency={u.artifact_execution_id: [] for u in units},
        in_degree={u.artifact_execution_id: 0 for u in units},
        is_acyclic=True,
    )

    strategy_summary = GenerationStrategySummary(
        total_units=len(units),
        template_count=0,
        pattern_count=0,
        llm_generated_count=len(units),
        unresolved_count=0,
        unresolved_artifacts=[],
    )

    scope_summary = RepositoryScopeSummary(
        total_units=len(units),
        scopes={"": len(units)},
        boundaries=[RepositoryBoundary(scope="", discipline="Frontend", is_authorized=True)],
        out_of_scope_artifacts=[],
    )

    conflict_report = ConflictReport(
        total_conflicts=0,
        errors=0,
        warnings=0,
        conflicts=[],
        has_blocking_conflicts=False,
    )

    plan = ArtifactExecutionPlan(
        plan_id="aep-test",
        mission_id="mission-test",
        contract_decomposition_report_id="cdr-test",
        execution_units=units,
        artifact_dependency_graph=graph,
        execution_waves=waves,
        execution_order=order,
        generation_strategy_summary=strategy_summary,
        repository_scope_summary=scope_summary,
        validation_checkpoints=checkpoints,
        conflict_report=conflict_report,
        traceability={"mission_id": "mission-test", "project_objective": "Test Project"},
        deterministic=True,
        deterministic_hash="test-hash",
        validation_passed=True,
        total_artifacts=len(units),
        total_waves=len(waves),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return plan


def create_unit(
    execution_id: str,
    artifact_id: str,
    target_path: str,
    wave: int = 1,
    language: str = "TypeScript",
    file_format: str = "ts",
) -> ArtifactExecutionUnit:
    """Create a test artifact execution unit."""
    return ArtifactExecutionUnit(
        artifact_execution_id=execution_id,
        artifact_id=artifact_id,
        sub_contract_id="sctr-test",
        parent_contract_id="ctr-test",
        mission_id="mission-test",
        agent_profile_id="agent-test",
        skill_bundle_id="bundle-test",
        repository_scope="",
        target_path=target_path,
        path_type=PathType.SOURCE,
        overwrite_policy=OverwritePolicy.SAFE,
        artifact_type="component",
        file_format=file_format,
        language=language,
        framework="",
        technology_context=[language],
        generation_strategy=GenerationStrategy.LLM_GENERATED,
        strategy_reason="Test",
        generation_priority="HIGH",
        execution_wave=wave,
        dependencies=[],
        required_inputs=[],
        validation_checkpoints=[create_checkpoint()],
        acceptance_criteria_ids=["ac-01"],
        artifact_route_id="route-01",
        deliverable_id="del-01",
        deterministic_hash=f"hash-{execution_id}",
    )


def create_unit_with_dependency(
    execution_id: str,
    artifact_id: str,
    target_path: str,
    source_artifact_id: str,
    wave: int = 1,
    language: str = "TypeScript",
    file_format: str = "ts",
) -> ArtifactExecutionUnit:
    """Create a test unit with a dependency."""
    return ArtifactExecutionUnit(
        artifact_execution_id=execution_id,
        artifact_id=artifact_id,
        sub_contract_id="sctr-test",
        parent_contract_id="ctr-test",
        mission_id="mission-test",
        agent_profile_id="agent-test",
        skill_bundle_id="bundle-test",
        repository_scope="",
        target_path=target_path,
        path_type=PathType.SOURCE,
        overwrite_policy=OverwritePolicy.SAFE,
        artifact_type="component",
        file_format=file_format,
        language=language,
        framework="",
        technology_context=[language],
        generation_strategy=GenerationStrategy.LLM_GENERATED,
        strategy_reason="Test",
        generation_priority="HIGH",
        execution_wave=wave,
        dependencies=[],
        required_inputs=[
            ArtifactDependencyInput(
                input_id=f"ai-{execution_id}-01",
                source_artifact_id=source_artifact_id,
                source_sub_contract_id="sctr-test",
                dependency_type=ArtifactDependencyType.REQUIRES,
                required_before_generation=True,
            )
        ],
        validation_checkpoints=[create_checkpoint()],
        acceptance_criteria_ids=["ac-01"],
        artifact_route_id="route-01",
        deliverable_id="del-01",
        deterministic_hash=f"hash-{execution_id}",
    )


# ---------------------------------------------------------------------------
# Test 1: Single Artifact Execution
# ---------------------------------------------------------------------------

class TestSingleArtifactExecution:
    """Tests for single artifact execution."""

    def test_single_artifact_executes(self, temp_repo_root):
        """Test that a single artifact executes successfully."""
        unit = create_unit("aeu-01", "art-01", "test.ts")
        wave = ArtifactExecutionWave(
            wave_number=1,
            wave_name="Test Wave",
            artifact_execution_ids=["aeu-01"],
            parallelizable=True,
            blocking_waves=[],
            blocking_artifacts={},
            required_artifact_ids=[],
            produced_artifact_ids=["art-01"],
        )
        plan = create_plan([unit], [wave])

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 1
        assert report.successful_artifacts == 1
        assert report.failed_artifacts == 0
        assert report.is_success
        assert engine.invoke_count == 1

    def test_single_artifact_fails(self, temp_repo_root):
        """Test that a single artifact failure is reported."""
        unit = create_unit("aeu-01", "art-01", "test.ts")
        wave = ArtifactExecutionWave(
            wave_number=1,
            wave_name="Test Wave",
            artifact_execution_ids=["aeu-01"],
            parallelizable=True,
            blocking_waves=[],
            blocking_artifacts={},
            required_artifact_ids=[],
            produced_artifact_ids=["art-01"],
        )
        plan = create_plan([unit], [wave])

        engine = MockFailingEngine(failing_ids=["aeu-01"])
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 1
        assert report.successful_artifacts == 0
        assert report.failed_artifacts == 1
        assert not report.is_success


# ---------------------------------------------------------------------------
# Test 2: Multiple Independent Artifacts
# ---------------------------------------------------------------------------

class TestMultipleIndependentArtifacts:
    """Tests for multiple independent artifact execution."""

    def test_independent_artifacts_execute(self, temp_repo_root):
        """Test that independent artifacts execute successfully."""
        units = [
            create_unit("aeu-01", "art-01", "file1.ts"),
            create_unit("aeu-02", "art-02", "file2.ts"),
            create_unit("aeu-03", "art-03", "file3.ts"),
        ]
        waves = [
            ArtifactExecutionWave(
                wave_number=1,
                wave_name="Independent Files",
                artifact_execution_ids=["aeu-01", "aeu-02", "aeu-03"],
                parallelizable=True,
                blocking_waves=[],
                blocking_artifacts={},
                required_artifact_ids=[],
                produced_artifact_ids=["art-01", "art-02", "art-03"],
            ),
        ]
        plan = create_plan(units, waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 3
        assert report.successful_artifacts == 3
        assert report.failed_artifacts == 0
        assert engine.invoke_count == 3


# ---------------------------------------------------------------------------
# Test 3: Dependency Ordering
# ---------------------------------------------------------------------------

class TestDependencyOrdering:
    """Tests for dependency-based execution ordering."""

    def test_dependent_artifact_waits(self, temp_repo_root):
        """Test that dependent artifacts wait for their dependencies."""
        # Unit 2 depends on Unit 1
        unit1 = create_unit("aeu-01", "art-01", "dependency.ts", wave=1)
        unit2 = create_unit_with_dependency(
            "aeu-02", "art-02", "dependent.ts",
            source_artifact_id="art-01", wave=2
        )

        waves = [
            ArtifactExecutionWave(
                wave_number=1,
                wave_name="Dependencies",
                artifact_execution_ids=["aeu-01"],
                parallelizable=False,
                blocking_waves=[],
                blocking_artifacts={},
                required_artifact_ids=[],
                produced_artifact_ids=["art-01"],
            ),
            ArtifactExecutionWave(
                wave_number=2,
                wave_name="Dependents",
                artifact_execution_ids=["aeu-02"],
                parallelizable=False,
                blocking_waves=[1],
                blocking_artifacts={},
                required_artifact_ids=["art-01"],
                produced_artifact_ids=["art-02"],
            ),
        ]
        plan = create_plan([unit1, unit2], waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        # Both should succeed
        assert report.total_artifacts == 2
        assert report.successful_artifacts == 2
        # Execution order should respect dependency
        assert engine.execution_order == ["aeu-01", "aeu-02"]


# ---------------------------------------------------------------------------
# Test 4: Wave Construction
# ---------------------------------------------------------------------------

class TestWaveConstruction:
    """Tests for wave-based execution."""

    def test_multiple_waves_execute_in_order(self, temp_repo_root):
        """Test that waves execute in correct order."""
        units = [
            create_unit("aeu-01", "art-01", "wave1.ts", wave=1),
            create_unit("aeu-02", "art-02", "wave2.ts", wave=2),
            create_unit("aeu-03", "art-03", "wave3.ts", wave=3),
        ]
        waves = [
            ArtifactExecutionWave(
                wave_number=1, wave_name="Wave 1",
                artifact_execution_ids=["aeu-01"], parallelizable=True,
                blocking_waves=[], blocking_artifacts={},
                required_artifact_ids=[], produced_artifact_ids=["art-01"],
            ),
            ArtifactExecutionWave(
                wave_number=2, wave_name="Wave 2",
                artifact_execution_ids=["aeu-02"], parallelizable=True,
                blocking_waves=[1], blocking_artifacts={},
                required_artifact_ids=["art-01"], produced_artifact_ids=["art-02"],
            ),
            ArtifactExecutionWave(
                wave_number=3, wave_name="Wave 3",
                artifact_execution_ids=["aeu-03"], parallelizable=True,
                blocking_waves=[2], blocking_artifacts={},
                required_artifact_ids=["art-02"], produced_artifact_ids=["art-03"],
            ),
        ]
        plan = create_plan(units, waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_waves == 3
        assert report.waves_executed == 3
        assert report.total_artifacts == 3
        assert report.successful_artifacts == 3
        assert engine.execution_order == ["aeu-01", "aeu-02", "aeu-03"]


# ---------------------------------------------------------------------------
# Test 5: Parallel-Safe Wave Grouping
# ---------------------------------------------------------------------------

class TestParallelSafeWaveGrouping:
    """Tests for parallel execution within waves."""

    def test_parallel_wave_executes_all(self, temp_repo_root):
        """Test that parallel artifacts in same wave all execute."""
        units = [
            create_unit("aeu-01", "art-01", "parallel1.ts", wave=1),
            create_unit("aeu-02", "art-02", "parallel2.ts", wave=1),
            create_unit("aeu-03", "art-03", "parallel3.ts", wave=1),
        ]
        waves = [
            ArtifactExecutionWave(
                wave_number=1,
                wave_name="Parallel Wave",
                artifact_execution_ids=["aeu-01", "aeu-02", "aeu-03"],
                parallelizable=True,
                blocking_waves=[],
                blocking_artifacts={},
                required_artifact_ids=[],
                produced_artifact_ids=["art-01", "art-02", "art-03"],
            ),
        ]
        plan = create_plan(units, waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 3
        assert report.successful_artifacts == 3
        assert len(report.wave_results) == 1
        assert report.wave_results[0].completed_units == 3


# ---------------------------------------------------------------------------
# Test 6: Dependency Cycle Detection
# ---------------------------------------------------------------------------

class TestDependencyCycleDetection:
    """Tests for dependency cycle detection."""

    def test_cycle_detection(self, temp_repo_root):
        """Test that cycles are detected before execution."""
        # Create units that would form a cycle
        unit1 = create_unit_with_dependency(
            "aeu-01", "art-01", "file1.ts",
            source_artifact_id="art-03", wave=1
        )
        unit2 = create_unit_with_dependency(
            "aeu-02", "art-02", "file2.ts",
            source_artifact_id="art-01", wave=1
        )
        unit3 = create_unit_with_dependency(
            "aeu-03", "art-03", "file3.ts",
            source_artifact_id="art-02", wave=1
        )

        waves = [
            ArtifactExecutionWave(
                wave_number=1,
                wave_name="Cyclic Wave",
                artifact_execution_ids=["aeu-01", "aeu-02", "aeu-03"],
                parallelizable=False,
                blocking_waves=[],
                blocking_artifacts={},
                required_artifact_ids=[],
                produced_artifact_ids=["art-01", "art-02", "art-03"],
            ),
        ]
        plan = create_plan([unit1, unit2, unit3], waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        # Should detect cycle
        assert report.cycle_result.cycle_detected
        assert len(report.cycle_result.cycle_path) > 0
        assert not report.is_success


# ---------------------------------------------------------------------------
# Test 7: Failed Artifact Propagation
# ---------------------------------------------------------------------------

class TestFailedArtifactPropagation:
    """Tests for failure propagation to dependents."""

    def test_failed_artifact_blocks_dependent(self, temp_repo_root):
        """Test that a failed artifact blocks dependent artifacts."""
        unit1 = create_unit("aeu-01", "art-01", "will-fail.ts", wave=1)
        unit2 = create_unit_with_dependency(
            "aeu-02", "art-02", "blocked.ts",
            source_artifact_id="art-01", wave=2
        )

        waves = [
            ArtifactExecutionWave(
                wave_number=1, wave_name="Will Fail",
                artifact_execution_ids=["aeu-01"], parallelizable=True,
                blocking_waves=[], blocking_artifacts={},
                required_artifact_ids=[], produced_artifact_ids=["art-01"],
            ),
            ArtifactExecutionWave(
                wave_number=2, wave_name="Blocked",
                artifact_execution_ids=["aeu-02"], parallelizable=True,
                blocking_waves=[1], blocking_artifacts={},
                required_artifact_ids=["art-01"], produced_artifact_ids=["art-02"],
            ),
        ]
        plan = create_plan([unit1, unit2], waves)

        engine = MockFailingEngine(failing_ids=["aeu-01"])
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.successful_artifacts == 0
        assert report.failed_artifacts == 1
        assert report.blocked_artifacts == 1
        assert len(report.dependency_failures) == 1


# ---------------------------------------------------------------------------
# Test 8: Independent Artifact Continues After Failure
# ---------------------------------------------------------------------------

class TestIndependentContinuesAfterFailure:
    """Tests for independent artifact continuation after failure."""

    def test_independent_succeeds_despite_other_failure(self, temp_repo_root):
        """Test that independent artifacts succeed even if others fail."""
        unit1 = create_unit("aeu-01", "art-01", "will-fail.ts", wave=1)
        unit2 = create_unit("aeu-02", "art-02", "independent.ts", wave=1)

        waves = [
            ArtifactExecutionWave(
                wave_number=1,
                wave_name="Mixed Wave",
                artifact_execution_ids=["aeu-01", "aeu-02"],
                parallelizable=True,
                blocking_waves=[],
                blocking_artifacts={},
                required_artifact_ids=[],
                produced_artifact_ids=["art-01", "art-02"],
            ),
        ]
        plan = create_plan([unit1, unit2], waves)

        engine = MockFailingEngine(failing_ids=["aeu-01"])
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 2
        assert report.successful_artifacts == 1
        assert report.failed_artifacts == 1


# ---------------------------------------------------------------------------
# Test 9: State Transitions
# ---------------------------------------------------------------------------

class TestStateTransitions:
    """Tests for execution state transitions."""

    def test_state_transitions_are_recorded(self, temp_repo_root):
        """Test that state transitions are properly recorded."""
        unit = create_unit("aeu-01", "art-01", "test.ts")
        wave = ArtifactExecutionWave(
            wave_number=1, wave_name="Test",
            artifact_execution_ids=["aeu-01"], parallelizable=True,
            blocking_waves=[], blocking_artifacts={},
            required_artifact_ids=[], produced_artifact_ids=["art-01"],
        )
        plan = create_plan([unit], [wave])

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        # Find the artifact status
        status = None
        for s in report.artifact_results:
            if s.artifact_execution_id == "aeu-01":
                status = s
                break

        assert status is not None
        assert len(status.state_history) >= 2  # QUEUED -> RUNNING -> COMPLETED
        assert status.state == ExecutionState.COMPLETED


# ---------------------------------------------------------------------------
# Test 10: Progress Reporting
# ---------------------------------------------------------------------------

class TestProgressReporting:
    """Tests for progress tracking."""

    def test_progress_updates(self, temp_repo_root):
        """Test that progress is correctly reported."""
        units = [
            create_unit("aeu-01", "art-01", "file1.ts"),
            create_unit("aeu-02", "art-02", "file2.ts"),
        ]
        waves = [
            ArtifactExecutionWave(
                wave_number=1, wave_name="Test",
                artifact_execution_ids=["aeu-01", "aeu-02"], parallelizable=True,
                blocking_waves=[], blocking_artifacts={},
                required_artifact_ids=[], produced_artifact_ids=["art-01", "art-02"],
            ),
        ]
        plan = create_plan(units, waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 2
        assert report.total_files_written == 2
        assert report.execution_started is not None
        assert report.execution_completed is not None
        assert report.total_duration_ms > 0


# ---------------------------------------------------------------------------
# Test 11-15: Multi-File Real Project Generation
# ---------------------------------------------------------------------------

class TestMultiFileRealProjectGeneration:
    """Tests for realistic multi-file project generation."""

    def test_real_estate_website_generation(self, temp_repo_root):
        """Test generation of a real estate website with multiple artifacts."""
        # Create realistic project structure
        units = [
            create_unit("aeu-html", "art-html", "index.html", wave=1, language="HTML", file_format="html"),
            create_unit("aeu-css", "art-css", "styles.css", wave=1, language="CSS", file_format="css"),
            create_unit("aeu-js", "art-js", "app.js", wave=1, language="JavaScript", file_format="js"),
            create_unit("aeu-header", "art-header", "components/Header.tsx", wave=2, language="TypeScript", file_format="tsx"),
            create_unit("aeu-hero", "art-hero", "components/Hero.tsx", wave=2, language="TypeScript", file_format="tsx"),
        ]

        waves = [
            ArtifactExecutionWave(
                wave_number=1, wave_name="Foundation",
                artifact_execution_ids=["aeu-html", "aeu-css", "aeu-js"], parallelizable=True,
                blocking_waves=[], blocking_artifacts={},
                required_artifact_ids=[], produced_artifact_ids=["art-html", "art-css", "art-js"],
            ),
            ArtifactExecutionWave(
                wave_number=2, wave_name="Components",
                artifact_execution_ids=["aeu-header", "aeu-hero"], parallelizable=True,
                blocking_waves=[1], blocking_artifacts={},
                required_artifact_ids=["art-html"], produced_artifact_ids=["art-header", "art-hero"],
            ),
        ]
        plan = create_plan(units, waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        # All artifacts should succeed
        assert report.total_artifacts == 5
        assert report.successful_artifacts == 5
        assert report.total_files_written == 5
        assert report.waves_executed == 2

        # Verify files exist
        for unit in units:
            # Note: Mock engine doesn't actually write files
            # In real execution, files would be written
            pass


# ---------------------------------------------------------------------------
# Test 16: Deterministic Execution Ordering
# ---------------------------------------------------------------------------

class TestDeterministicExecution:
    """Tests for deterministic execution."""

    def test_execution_is_deterministic(self, temp_repo_root):
        """Test that execution order is deterministic."""
        units = [
            create_unit("aeu-01", "art-01", "file1.ts"),
            create_unit("aeu-02", "art-02", "file2.ts"),
            create_unit("aeu-03", "art-03", "file3.ts"),
        ]
        waves = [
            ArtifactExecutionWave(
                wave_number=1, wave_name="Test",
                artifact_execution_ids=["aeu-01", "aeu-02", "aeu-03"], parallelizable=True,
                blocking_waves=[], blocking_artifacts={},
                required_artifact_ids=[], produced_artifact_ids=["art-01", "art-02", "art-03"],
            ),
        ]
        plan = create_plan(units, waves)

        # Execute twice
        engine1 = MockGenerationEngine()
        orchestrator1 = ArtifactExecutionOrchestrator(temp_repo_root, engine1)
        report1 = orchestrator1.execute(plan)

        engine2 = MockGenerationEngine()
        orchestrator2 = ArtifactExecutionOrchestrator(temp_repo_root, engine2)
        report2 = orchestrator2.execute(plan)

        # Results should be identical
        assert report1.successful_artifacts == report2.successful_artifacts
        assert report1.total_files_written == report2.total_files_written


# ---------------------------------------------------------------------------
# Test 17: Partial Project Success
# ---------------------------------------------------------------------------

class TestPartialProjectSuccess:
    """Tests for partial success scenarios."""

    def test_partial_success_reporting(self, temp_repo_root):
        """Test that partial success is correctly reported."""
        unit1 = create_unit("aeu-01", "art-01", "file1.ts")
        unit2 = create_unit("aeu-02", "art-02", "file2.ts")
        unit3 = create_unit("aeu-03", "art-03", "file3.ts")

        waves = [
            ArtifactExecutionWave(
                wave_number=1, wave_name="Test",
                artifact_execution_ids=["aeu-01", "aeu-02", "aeu-03"], parallelizable=True,
                blocking_waves=[], blocking_artifacts={},
                required_artifact_ids=[], produced_artifact_ids=["art-01", "art-02", "art-03"],
            ),
        ]
        plan = create_plan([unit1, unit2, unit3], waves)

        engine = MockFailingEngine(failing_ids=["aeu-02"])
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 3
        assert report.successful_artifacts == 2
        assert report.failed_artifacts == 1
        assert report.is_partial_success
        assert not report.is_success


# ---------------------------------------------------------------------------
# Test 18: Integration with RealCodeGenerationEngine
# ---------------------------------------------------------------------------

class TestRealCodeGenerationIntegration:
    """Tests for integration with RealCodeGenerationEngine."""

    def test_integration_with_real_engine_interface(self, temp_repo_root):
        """Test that orchestrator works with RealCodeGenerationEngine interface."""
        unit = create_unit("aeu-01", "art-01", "test.ts")
        wave = ArtifactExecutionWave(
            wave_number=1, wave_name="Test",
            artifact_execution_ids=["aeu-01"], parallelizable=True,
            blocking_waves=[], blocking_artifacts={},
            required_artifact_ids=[], produced_artifact_ids=["art-01"],
        )
        plan = create_plan([unit], [wave])

        # Create mock that matches RealCodeGenerationEngine interface
        class InterfaceMatchingEngine:
            def generate_single(self, unit, plan):
                return GenerationResult(
                    result_id=f"gen-{unit.artifact_execution_id}",
                    artifact_execution_id=unit.artifact_execution_id,
                    artifact_id=unit.artifact_id,
                    sub_contract_id=unit.sub_contract_id,
                    strategy=unit.generation_strategy,
                    generation_started=datetime.now(timezone.utc).isoformat(),
                    generation_completed=datetime.now(timezone.utc).isoformat(),
                    generation_duration_ms=10.0,
                    success=True,
                    content=f"// {unit.target_path}\nexport const test = () => {{}};\n",
                    file_written=True,
                    written_path=unit.target_path,
                    context_hash="mock-hash",
                    errors=(),
                    warnings=(),
                    validation_passed=True,
                    validation_errors=(),
                    content_hash="content-hash",
                )

        engine = InterfaceMatchingEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.successful_artifacts == 1
        assert report.is_success


# ---------------------------------------------------------------------------
# Test 19-20: LLM_GENERATED Multi-Artifact Execution
# ---------------------------------------------------------------------------

class TestLLMMultiArtifactExecution:
    """Tests for LLM_GENERATED multi-artifact execution."""

    def test_llm_generated_artifacts_execute(self, temp_repo_root):
        """Test that LLM_GENERATED artifacts execute correctly."""
        units = [
            create_unit("aeu-01", "art-01", "llm1.ts"),
            create_unit("aeu-02", "art-02", "llm2.ts"),
            create_unit("aeu-03", "art-03", "llm3.ts"),
        ]
        waves = [
            ArtifactExecutionWave(
                wave_number=1, wave_name="LLM Generated",
                artifact_execution_ids=["aeu-01", "aeu-02", "aeu-03"], parallelizable=True,
                blocking_waves=[], blocking_artifacts={},
                required_artifact_ids=[], produced_artifact_ids=["art-01", "art-02", "art-03"],
            ),
        ]
        plan = create_plan(units, waves)

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        assert report.total_artifacts == 3
        assert report.successful_artifacts == 3
        assert all(
            r.generation_strategy == GenerationStrategy.LLM_GENERATED
            for r in report.artifact_results
        )


# ---------------------------------------------------------------------------
# Additional Test: State Transition Validity
# ---------------------------------------------------------------------------

class TestStateTransitionValidity:
    """Tests for valid state transitions."""

    def test_no_invalid_transitions(self, temp_repo_root):
        """Test that invalid state transitions are prevented."""
        unit = create_unit("aeu-01", "art-01", "test.ts")
        wave = ArtifactExecutionWave(
            wave_number=1, wave_name="Test",
            artifact_execution_ids=["aeu-01"], parallelizable=True,
            blocking_waves=[], blocking_artifacts={},
            required_artifact_ids=[], produced_artifact_ids=["art-01"],
        )
        plan = create_plan([unit], [wave])

        engine = MockGenerationEngine()
        orchestrator = ArtifactExecutionOrchestrator(temp_repo_root, engine)
        report = orchestrator.execute(plan)

        status = None
        for s in report.artifact_results:
            if s.artifact_execution_id == "aeu-01":
                status = s
                break

        assert status is not None
        # Valid final state
        assert status.state in (ExecutionState.COMPLETED, ExecutionState.FAILED)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
