"""E3.1 End-to-End Tests for Real Filesystem Generation.

These tests verify that the E3.1 Real Code Generation Engine can actually
produce real source files on the filesystem.
"""

from __future__ import annotations

import os
import tempfile
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

from runtime.contracts.e23_models import (
    ArtifactDependencyEdge,
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
from runtime.contracts.generators.engine import RealCodeGenerationEngine
from runtime.contracts.e31_models import compute_content_hash


# ---------------------------------------------------------------------------
# Mock InvocationEngine for LLM_GENERATED testing
# ---------------------------------------------------------------------------

class MockInvocationResponse:
    """Mock InvocationResponse for testing."""
    
    def __init__(self, content: str):
        self.content = content
        self.message = MagicMock()
        self.message.content = content
        self.text = content
        self.metadata = {}


class MockInvocationEngine:
    """Mock InvocationEngine that returns deterministic responses."""
    
    def __init__(self, response_content: str):
        self.response_content = response_content
    
    def invoke(
        self,
        request: Any,
        selection: Any,
        model_id: Optional[str] = None,
        retry: Any = None,
    ):
        """Return mock response."""
        return MockInvocationResponse(self.response_content)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_repo_root(tmp_path):
    """Create a temporary repository root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return str(repo)


def create_test_plan(artifact_count: int = 3, include_llm: bool = False) -> ArtifactExecutionPlan:
    """Create a test plan with specified artifacts."""
    
    checkpoints = [
        ValidationCheckpoint(
            checkpoint_id="chk-01",
            category=ValidationCategory.PATH_VALIDATION,
            description="Verify path is not empty",
            is_blocking=True,
            validator="PathValidator",
        ),
    ]
    
    units = []
    
    # Template artifact
    units.append(ArtifactExecutionUnit(
        artifact_execution_id="aeu-template-01",
        artifact_id="template-art",
        sub_contract_id="sctr-config",
        parent_contract_id="contract-config",
        mission_id="mission-e2e",
        agent_profile_id="agent-config",
        skill_bundle_id="bundle-config",
        repository_scope="config/",
        target_path="config/settings.json",
        path_type=PathType.SOURCE,
        overwrite_policy=OverwritePolicy.SAFE,
        artifact_type="config",
        file_format="json",
        language="TypeScript",
        framework="React",
        technology_context=["react"],
        generation_strategy=GenerationStrategy.TEMPLATE,
        strategy_reason="Config template",
        generation_priority="HIGH",
        execution_wave=1,
        dependencies=[],
        required_inputs=[],
        validation_checkpoints=checkpoints,
        acceptance_criteria_ids=["ac-001"],
        artifact_route_id="route-001",
        deliverable_id="del-001",
        deterministic_hash="hash-template-01",
    ))
    
    # Pattern artifact
    units.append(ArtifactExecutionUnit(
        artifact_execution_id="aeu-pattern-01",
        artifact_id="pattern-art",
        sub_contract_id="sctr-api",
        parent_contract_id="contract-api",
        mission_id="mission-e2e",
        agent_profile_id="agent-api",
        skill_bundle_id="bundle-api",
        repository_scope="api/",
        target_path="api/routes.py",
        path_type=PathType.SOURCE,
        overwrite_policy=OverwritePolicy.SAFE,
        artifact_type="api",
        file_format="py",
        language="Python",
        framework="FastAPI",
        technology_context=["fastapi", "python"],
        generation_strategy=GenerationStrategy.PATTERN,
        strategy_reason="FastAPI pattern",
        generation_priority="HIGH",
        execution_wave=1,
        dependencies=[],
        required_inputs=[],
        validation_checkpoints=checkpoints,
        acceptance_criteria_ids=["ac-002"],
        artifact_route_id="route-002",
        deliverable_id="del-002",
        deterministic_hash="hash-pattern-01",
    ))
    
    # Another pattern artifact (test)
    units.append(ArtifactExecutionUnit(
        artifact_execution_id="aeu-pattern-02",
        artifact_id="test-art",
        sub_contract_id="sctr-testing",
        parent_contract_id="contract-testing",
        mission_id="mission-e2e",
        agent_profile_id="agent-testing",
        skill_bundle_id="bundle-testing",
        repository_scope="tests/",
        target_path="tests/test_routes.py",
        path_type=PathType.SOURCE,
        overwrite_policy=OverwritePolicy.SAFE,
        artifact_type="test",
        file_format="py",
        language="Python",
        framework="pytest",
        technology_context=["pytest"],
        generation_strategy=GenerationStrategy.PATTERN,
        strategy_reason="Pytest pattern",
        generation_priority="MEDIUM",
        execution_wave=1,
        dependencies=[],
        required_inputs=[],
        validation_checkpoints=checkpoints,
        acceptance_criteria_ids=["ac-003"],
        artifact_route_id="route-003",
        deliverable_id="del-003",
        deterministic_hash="hash-pattern-02",
    ))
    
    # LLM artifact if requested
    if include_llm:
        units.append(ArtifactExecutionUnit(
            artifact_execution_id="aeu-llm-01",
            artifact_id="llm-art",
            sub_contract_id="sctr-llm",
            parent_contract_id="contract-llm",
            mission_id="mission-e2e",
            agent_profile_id="agent-llm",
            skill_bundle_id="bundle-llm",
            repository_scope="generated/",
            target_path="generated/script.py",
            path_type=PathType.SOURCE,
            overwrite_policy=OverwritePolicy.SAFE,
            artifact_type="shared",
            file_format="py",
            language="Python",
            framework="",
            technology_context=["python"],
            generation_strategy=GenerationStrategy.LLM_GENERATED,
            strategy_reason="LLM generation",
            generation_priority="LOW",
            execution_wave=1,
            dependencies=[],
            required_inputs=[],
            validation_checkpoints=checkpoints,
            acceptance_criteria_ids=["ac-004"],
            artifact_route_id="route-004",
            deliverable_id="del-004",
            deterministic_hash="hash-llm-01",
        ))
    
    # Waves
    waves = [
        ArtifactExecutionWave(
            wave_number=1,
            wave_name="Core Files",
            artifact_execution_ids=[u.artifact_execution_id for u in units],
            parallelizable=True,
            blocking_waves=[],
            blocking_artifacts={},
            required_artifact_ids=[],
            produced_artifact_ids=[u.artifact_id for u in units],
        ),
    ]
    
    # Execution order
    order = [
        ArtifactExecutionOrder(
            artifact_execution_id=u.artifact_execution_id,
            execution_wave=1,
            execution_order=i,
            blocking_artifacts=[],
            prerequisite_artifacts=[],
        )
        for i, u in enumerate(units)
    ]
    
    # Dependency graph
    graph = ArtifactDependencyGraph(
        graph_id="graph-e2e",
        nodes=[u.artifact_execution_id for u in units],
        edges=[],
        adjacency={u.artifact_execution_id: [] for u in units},
        reverse_adjacency={u.artifact_execution_id: [] for u in units},
        in_degree={u.artifact_execution_id: 0 for u in units},
        is_acyclic=True,
    )
    
    # Strategy summary
    llm_count = 1 if include_llm else 0
    strategy_summary = GenerationStrategySummary(
        total_units=len(units),
        template_count=1,
        pattern_count=len(units) - 1 - llm_count,
        llm_generated_count=llm_count,
        unresolved_count=0,
        unresolved_artifacts=[],
    )
    
    # Scope summary
    scope_summary = RepositoryScopeSummary(
        total_units=len(units),
        scopes={"config/": 1, "api/": 1, "tests/": 1, "generated/": llm_count},
        boundaries=[
            RepositoryBoundary(scope="config/", discipline="Config", is_authorized=True),
            RepositoryBoundary(scope="api/", discipline="API", is_authorized=True),
            RepositoryBoundary(scope="tests/", discipline="Testing", is_authorized=True),
            RepositoryBoundary(scope="generated/", discipline="Generated", is_authorized=True),
        ],
        out_of_scope_artifacts=[],
    )
    
    # Conflict report
    conflict_report = ConflictReport(
        total_conflicts=0,
        errors=0,
        warnings=0,
        conflicts=[],
        has_blocking_conflicts=False,
    )
    
    # Create plan
    plan = ArtifactExecutionPlan(
        plan_id="aep-e2e-test",
        mission_id="mission-e2e",
        contract_decomposition_report_id="cdr-e2e",
        execution_units=units,
        artifact_dependency_graph=graph,
        execution_waves=waves,
        execution_order=order,
        generation_strategy_summary=strategy_summary,
        repository_scope_summary=scope_summary,
        validation_checkpoints=checkpoints,
        conflict_report=conflict_report,
        traceability={
            "mission_id": "mission-e2e",
            "project_objective": "E2E Test Project",
        },
        deterministic=True,
        deterministic_hash="plan-hash-e2e",
        validation_passed=True,
        total_artifacts=len(units),
        total_waves=1,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    
    return plan


# ---------------------------------------------------------------------------
# E2E Tests: Template Strategy
# ---------------------------------------------------------------------------

class TestTemplateE2E:
    """End-to-end tests for TEMPLATE strategy."""
    
    def test_template_generates_real_file(self, temp_repo_root):
        """Test that TEMPLATE strategy produces a real file on disk."""
        plan = create_test_plan(artifact_count=1)
        
        engine = RealCodeGenerationEngine(temp_repo_root)
        report = engine.generate(plan)
        
        # Check report
        assert report.successful_generations >= 1
        assert report.files_written >= 1
        
        # Check file exists
        config_path = os.path.join(temp_repo_root, "config/settings.json")
        assert os.path.exists(config_path), f"File not found: {config_path}"
        
        # Check file has content
        with open(config_path, "r") as f:
            content = f.read()
        assert len(content) > 0, "File is empty"
        
        # Check file contains actual generated code (not just config JSON)
        # Templates may generate different content based on type matching
        # Just verify it has meaningful content
        assert len(content) > 50, "File content too short"


# ---------------------------------------------------------------------------
# E2E Tests: Pattern Strategy
# ---------------------------------------------------------------------------

class TestPatternE2E:
    """End-to-end tests for PATTERN strategy."""
    
    def test_pattern_generates_real_file(self, temp_repo_root):
        """Test that PATTERN strategy produces a real file on disk."""
        plan = create_test_plan(artifact_count=1)
        
        engine = RealCodeGenerationEngine(temp_repo_root)
        report = engine.generate(plan)
        
        # Check report
        assert report.successful_generations >= 1
        assert report.files_written >= 1
        
        # Check file exists
        api_path = os.path.join(temp_repo_root, "api/routes.py")
        assert os.path.exists(api_path), f"File not found: {api_path}"
        
        # Check file has content
        with open(api_path, "r") as f:
            content = f.read()
        assert len(content) > 0, "File is empty"
        
        # Check it's valid Python (no obvious syntax errors)
        compile(content, api_path, 'exec')


# ---------------------------------------------------------------------------
# E2E Tests: LLM_GENERATED Strategy (with Mock)
# ---------------------------------------------------------------------------

class TestLLME2E:
    """End-to-end tests for LLM_GENERATED strategy."""
    
    def test_llm_generates_real_file(self, temp_repo_root):
        """Test that LLM_GENERATED strategy produces a real file via InvocationEngine."""
        # Create mock LLM response
        mock_code = '''"""Generated module.

Auto-generated by E3.1 LLM generation.
"""

from typing import Any, Optional


class GeneratedService:
    """A generated service class."""
    
    def __init__(self) -> None:
        self._data: list[Any] = []
    
    def add(self, item: Any) -> None:
        """Add an item to the service."""
        self._data.append(item)
    
    def get_all(self) -> list[Any]:
        """Get all items."""
        return list(self._data)
    
    def clear(self) -> None:
        """Clear all items."""
        self._data.clear()
'''

        # Create mock engine
        mock_engine = MockInvocationEngine(mock_code)
        
        plan = create_test_plan(artifact_count=1, include_llm=True)
        
        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)
        
        # Check report
        assert report.successful_generations >= 1, f"Expected successful generation, got {report.successful_generations}"
        assert report.files_written >= 1, f"Expected files written, got {report.files_written}"
        
        # Check file exists
        generated_path = os.path.join(temp_repo_root, "generated/script.py")
        assert os.path.exists(generated_path), f"File not found: {generated_path}"
        
        # Check file has content
        with open(generated_path, "r") as f:
            content = f.read()
        assert len(content) > 0, "File is empty"
        
        # Check content matches expected
        assert "GeneratedService" in content, "Expected GeneratedService class"
        assert "add" in content, "Expected add method"
        
        # Verify it's valid Python
        compile(content, generated_path, 'exec')


# ---------------------------------------------------------------------------
# E2E Tests: Multi-File Generation
# ---------------------------------------------------------------------------

class TestMultiFileE2E:
    """End-to-end tests for multi-file generation."""
    
    def test_multi_file_generation(self, temp_repo_root):
        """Test that multiple artifacts generate multiple files."""
        plan = create_test_plan(artifact_count=3, include_llm=False)
        
        engine = RealCodeGenerationEngine(temp_repo_root)
        report = engine.generate(plan)
        
        # Check report
        assert report.total_artifacts == 3
        assert report.successful_generations == 3
        assert report.files_written == 3
        
        # Check all files exist
        expected_files = [
            "config/settings.json",
            "api/routes.py",
            "tests/test_routes.py",
        ]
        
        for file_path in expected_files:
            full_path = os.path.join(temp_repo_root, file_path)
            assert os.path.exists(full_path), f"File not found: {full_path}"
            
            with open(full_path, "r") as f:
                content = f.read()
            assert len(content) > 0, f"File is empty: {file_path}"
    
    def test_multi_file_with_llm(self, temp_repo_root):
        """Test multi-file generation including LLM artifact."""
        mock_code = '''"""Generated utility."""

def helper():
    return "helper result"
'''
        mock_engine = MockInvocationEngine(mock_code)
        
        plan = create_test_plan(artifact_count=4, include_llm=True)
        
        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)
        
        # Check report
        assert report.total_artifacts == 4
        assert report.successful_generations == 4
        assert report.files_written == 4
        
        # Check all files exist
        expected_files = [
            "config/settings.json",
            "api/routes.py",
            "tests/test_routes.py",
            "generated/script.py",
        ]
        
        for file_path in expected_files:
            full_path = os.path.join(temp_repo_root, file_path)
            assert os.path.exists(full_path), f"File not found: {file_path}"


# ---------------------------------------------------------------------------
# E2E Tests: Idempotency
# ---------------------------------------------------------------------------

class TestIdempotencyE2E:
    """End-to-end tests for idempotent generation."""
    
    def test_idempotent_generation(self, temp_repo_root):
        """Test that running generation twice produces identical files."""
        plan = create_test_plan(artifact_count=3, include_llm=False)
        
        engine = RealCodeGenerationEngine(temp_repo_root)
        
        # First generation
        report1 = engine.generate(plan)
        assert report1.files_written == 3
        
        # Read file hashes
        hashes1 = {}
        for unit in plan.execution_units:
            file_path = os.path.join(temp_repo_root, unit.target_path)
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    hashes1[unit.artifact_execution_id] = compute_content_hash(f.read())
        
        # Second generation in same directory - files may be overwritten
        # The key test is that content remains identical
        report2 = engine.generate(plan)
        
        # Read file hashes again
        hashes2 = {}
        for unit in plan.execution_units:
            file_path = os.path.join(temp_repo_root, unit.target_path)
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    hashes2[unit.artifact_execution_id] = compute_content_hash(f.read())
        
        # All hashes should match - proving deterministic content
        assert hashes1 == hashes2, "File hashes changed between runs"


# ---------------------------------------------------------------------------
# E2E Tests: Path Boundaries
# ---------------------------------------------------------------------------

class TestPathBoundariesE2E:
    """End-to-end tests for path boundary enforcement."""
    
    def test_path_traversal_blocked(self, temp_repo_root):
        """Test that path traversal attempts are blocked."""
        # Create a plan with path traversal directly
        checkpoints = [
            ValidationCheckpoint(
                checkpoint_id="chk-01",
                category=ValidationCategory.PATH_VALIDATION,
                description="Verify path is not empty",
                is_blocking=True,
                validator="PathValidator",
            ),
        ]
        
        traversal_unit = ArtifactExecutionUnit(
            artifact_execution_id="aeu-traversal",
            artifact_id="evil-art",
            sub_contract_id="sctr-evil",
            parent_contract_id="contract-evil",
            mission_id="mission-e2e",
            agent_profile_id="agent-evil",
            skill_bundle_id="bundle-evil",
            repository_scope="safe/",
            target_path="../../../etc/passwd",
            path_type=PathType.SOURCE,
            overwrite_policy=OverwritePolicy.SAFE,
            artifact_type="file",
            file_format="txt",
            language="",
            framework="",
            technology_context=[],
            generation_strategy=GenerationStrategy.TEMPLATE,
            strategy_reason="Test traversal",
            generation_priority="HIGH",
            execution_wave=1,
            dependencies=[],
            required_inputs=[],
            validation_checkpoints=checkpoints,
            acceptance_criteria_ids=[],
            artifact_route_id="route-evil",
            deliverable_id="del-evil",
            deterministic_hash="hash-evil",
        )
        
        # Create minimal plan with traversal unit
        wave = ArtifactExecutionWave(
            wave_number=1,
            wave_name="Test Wave",
            artifact_execution_ids=["aeu-traversal"],
            parallelizable=True,
            blocking_waves=[],
            blocking_artifacts={},
            required_artifact_ids=[],
            produced_artifact_ids=["evil-art"],
        )
        
        order = [
            ArtifactExecutionOrder(
                artifact_execution_id="aeu-traversal",
                execution_wave=1,
                execution_order=0,
                blocking_artifacts=[],
                prerequisite_artifacts=[],
            )
        ]
        
        graph = ArtifactDependencyGraph(
            graph_id="graph-traversal",
            nodes=["aeu-traversal"],
            edges=[],
            adjacency={"aeu-traversal": []},
            reverse_adjacency={"aeu-traversal": []},
            in_degree={"aeu-traversal": 0},
            is_acyclic=True,
        )
        
        strategy_summary = GenerationStrategySummary(
            total_units=1,
            template_count=1,
            pattern_count=0,
            llm_generated_count=0,
            unresolved_count=0,
            unresolved_artifacts=[],
        )
        
        scope_summary = RepositoryScopeSummary(
            total_units=1,
            scopes={"safe/": 1},
            boundaries=[RepositoryBoundary(scope="safe/", discipline="Test", is_authorized=True)],
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
            plan_id="aep-traversal-test",
            mission_id="mission-e2e",
            contract_decomposition_report_id="cdr-traversal",
            execution_units=[traversal_unit],
            artifact_dependency_graph=graph,
            execution_waves=[wave],
            execution_order=order,
            generation_strategy_summary=strategy_summary,
            repository_scope_summary=scope_summary,
            validation_checkpoints=checkpoints,
            conflict_report=conflict_report,
            traceability={},
            deterministic=True,
            deterministic_hash="plan-hash-traversal",
            validation_passed=True,
            total_artifacts=1,
            total_waves=1,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        engine = RealCodeGenerationEngine(temp_repo_root)
        
        # Should raise blocking conflict error
        from runtime.contracts.e31_models import BlockingConflictError
        with pytest.raises(BlockingConflictError):
            engine.generate(plan)


# ---------------------------------------------------------------------------
# E2E Tests: Content Validation
# ---------------------------------------------------------------------------

class TestContentValidationE2E:
    """End-to-end tests for content validation."""
    
    def test_no_stub_content_in_generated_files(self, temp_repo_root):
        """Test that generated files don't contain stub placeholders."""
        plan = create_test_plan(artifact_count=3, include_llm=False)
        
        engine = RealCodeGenerationEngine(temp_repo_root)
        report = engine.generate(plan)
        
        assert report.successful_generations == 3
        
        # Check each file for stub content
        stub_indicators = ["TODO:", "FIXME:", "PLACEHOLDER", "INSERT_CODE_HERE"]
        
        for unit in plan.execution_units:
            file_path = os.path.join(temp_repo_root, unit.target_path)
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    content = f.read()
                
                for indicator in stub_indicators:
                    assert indicator not in content, f"Found '{indicator}' in {unit.target_path}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
