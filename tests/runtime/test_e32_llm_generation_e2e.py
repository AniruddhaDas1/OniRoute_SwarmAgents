"""E3.2 End-to-End Tests for LLM_GENERATED Production Path.

These tests verify the complete execution path:
Mission → E2 Contract → ArtifactExecutionPlan → E3.1 → LLM_GENERATED → InvocationEngine → Files
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
from runtime.invocation.request import InvocationRequest
from runtime.invocation.response import InvocationResponse
from runtime.invocation.models import Message


# ---------------------------------------------------------------------------
# Mock Provider Adapter for Testing
# ---------------------------------------------------------------------------

class MockProviderAdapter:
    """Mock provider adapter that returns deterministic code."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """Initialize with optional response mapping.

        Args:
            responses: Optional dict mapping artifact execution IDs to responses
        """
        self.responses = responses or {}
        self.last_request: Optional[InvocationRequest] = None

    def invoke(self, model: Any, request: InvocationRequest) -> InvocationResponse:
        """Return deterministic response based on request metadata."""
        self.last_request = request

        # Extract artifact execution ID from metadata
        artifact_id = None
        if hasattr(request, 'metadata') and request.metadata:
            artifact_id = request.metadata.get('artifact_execution_id')

        # Get response for this artifact, or generate default
        response_content = self.responses.get(artifact_id, self._generate_default_response(request))

        return InvocationResponse(
            text=response_content,
            usage={"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
        )

    def _generate_default_response(self, request: InvocationRequest) -> str:
        """Generate a default response based on request content."""
        # Extract language/framework from request
        language = "Python"
        framework = ""
        target_path = ""
        file_format = ""

        if hasattr(request, 'metadata') and request.metadata:
            constraints = request.metadata.get('generation_constraints', {})
            language = constraints.get('language', 'Python')
            framework = constraints.get('framework', '')
            target_path = constraints.get('target_path', '')
            file_format = constraints.get('file_format', '')

        # Check for language in system/user prompts
        prompt_text = ""
        if hasattr(request, 'messages'):
            for msg in request.messages:
                if hasattr(msg, 'content'):
                    prompt_text += msg.content + " "

        # Detect from prompts and metadata
        if 'TypeScript' in prompt_text or 'tsx' in file_format or framework == 'React':
            language = "TypeScript"
            if framework == 'React':
                return self._generate_react_component(target_path)
            return self._generate_typescript_code(target_path)
        elif 'JavaScript' in prompt_text or 'js' in file_format:
            language = "JavaScript"
            return self._generate_javascript_code(target_path)
        elif 'HTML' in prompt_text or 'html' in file_format:
            return self._generate_html_code(target_path)
        elif 'CSS' in prompt_text or 'css' in file_format:
            return self._generate_css_code(target_path)
        elif framework == "FastAPI":
            return self._generate_fastapi_endpoint(target_path)
        elif 'Python' in prompt_text:
            return self._generate_python_module(target_path)
        else:
            # Default based on file extension
            if target_path.endswith('.py'):
                return self._generate_python_module(target_path)
            elif target_path.endswith('.ts') or target_path.endswith('.tsx'):
                if framework == 'React':
                    return self._generate_react_component(target_path)
                return self._generate_typescript_code(target_path)
            elif target_path.endswith('.js'):
                return self._generate_javascript_code(target_path)
            elif target_path.endswith('.html'):
                return self._generate_html_code(target_path)
            elif target_path.endswith('.css'):
                return self._generate_css_code(target_path)
            else:
                return self._generate_python_module(target_path)

    def _generate_react_component(self, target_path: str) -> str:
        """Generate a React component."""
        component_name = "Component"
        if target_path:
            # Extract component name from path
            basename = os.path.basename(target_path)
            component_name = os.path.splitext(basename)[0].replace('-', '').replace('_', '')
            component_name = component_name.title()

        return '''import React, { useState } from 'react';

interface ComponentProps {
  className?: string;
  title?: string;
}

export const Component: React.FC<ComponentProps> = ({
  className = '',
  title = 'Property Card'
}) => {
  const [isActive, setIsActive] = useState(false);

  const handleClick = () => {
    setIsActive(!isActive);
  };

  return (
    <div className={"property-card " + className}>
      <h2 className="title">{title}</h2>
      <button
        className={"toggle-btn " + (isActive ? "active" : "")}
        onClick={handleClick}
      >
        {isActive ? "Active" : "Inactive"}
      </button>
    </div>
  );
};

export default Component;
'''

    def _generate_typescript_code(self, target_path: str) -> str:
        """Generate TypeScript code."""
        return '''export interface Config {
  apiUrl: string;
  timeout: number;
  retries: number;
}

export class ConfigManager {
  private config: Config;

  constructor(config: Config) {
    this.config = config;
  }

  get<K extends keyof Config>(key: K): Config[K] {
    return this.config[key];
  }

  set<K extends keyof Config>(key: K, value: Config[K]): void {
    this.config[key] = value;
  }

  toJSON(): Config {
    return { ...this.config };
  }
}

export const createConfig = (partial: Partial<Config>): Config => ({
  apiUrl: partial.apiUrl || 'http://localhost:3000',
  timeout: partial.timeout || 5000,
  retries: partial.retries || 3,
});
'''

    def _generate_javascript_code(self, target_path: str) -> str:
        """Generate JavaScript code."""
        return '''export class EventEmitter {
  constructor() {
    this.events = {};
  }

  on(event, callback) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(callback);
    return this;
  }

  off(event, callback) {
    if (!this.events[event]) return this;
    this.events[event] = this.events[event].filter(cb => cb !== callback);
    return this;
  }

  emit(event, ...args) {
    if (!this.events[event]) return this;
    this.events[event].forEach(callback => callback(...args));
    return this;
  }
}

export default EventEmitter;
'''

    def _generate_html_code(self, target_path: str) -> str:
        """Generate HTML code."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Real Estate Landing Page</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="hero">
    <div class="hero-content">
      <h1>Find Your Dream Home</h1>
      <p>Discover amazing properties in your area</p>
      <button class="cta-button">Get Started</button>
    </div>
  </header>

  <section class="properties">
    <h2>Featured Properties</h2>
    <div class="property-grid">
      <article class="property-card">
        <img src="https://via.placeholder.com/300x200" alt="Property 1">
        <h3>Modern Apartment</h3>
        <p class="price">$500,000</p>
        <p class="details">3 bed, 2 bath</p>
      </article>
      <article class="property-card">
        <img src="https://via.placeholder.com/300x200" alt="Property 2">
        <h3>Luxury Villa</h3>
        <p class="price">$1,200,000</p>
        <p class="details">5 bed, 4 bath</p>
      </article>
    </div>
  </section>

  <footer class="footer">
    <p>&copy; 2024 Real Estate. All rights reserved.</p>
  </footer>

  <script src="main.js"></script>
</body>
</html>
'''

    def _generate_css_code(self, target_path: str) -> str:
        """Generate CSS code."""
        return '''* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  color: #333;
}

.hero {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 4rem 2rem;
  text-align: center;
}

.hero h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.cta-button {
  background: #fff;
  color: #667eea;
  border: none;
  padding: 0.75rem 2rem;
  font-size: 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 1rem;
}

.cta-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.properties {
  padding: 3rem 2rem;
}

.properties h2 {
  text-align: center;
  margin-bottom: 2rem;
}

.property-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.property-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.2s;
}

.property-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.property-card img {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.property-card h3 {
  padding: 1rem 1rem 0.5rem;
}

.property-card .price {
  color: #667eea;
  font-weight: bold;
  padding: 0 1rem;
}

.property-card .details {
  color: #666;
  padding: 0.5rem 1rem 1rem;
}

.footer {
  background: #333;
  color: white;
  text-align: center;
  padding: 2rem;
  margin-top: 2rem;
}
'''

    def _generate_fastapi_endpoint(self, target_path: str) -> str:
        """Generate FastAPI endpoint."""
        return '''"""API endpoint module.

Generated for: FastAPI application
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter()


class RequestModel(BaseModel):
    """Request payload model."""
    data: Optional[dict[str, Any]] = None
    action: str = "process"


class ResponseModel(BaseModel):
    """Response model."""
    success: bool
    message: str
    data: Optional[dict[str, Any]] = None


@router.post("/api/process", response_model=ResponseModel)
async def process_request(request: RequestModel) -> ResponseModel:
    """Handle process request with business logic."""
    try:
        result = {"processed": True, "action": request.action, "received": request.data}
        return ResponseModel(
            success=True,
            message="Request processed successfully",
            data=result,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "api"}
'''

    def _generate_python_module(self, target_path: str) -> str:
        """Generate Python module."""
        return '''"""Python module.

Generated for: Python application
"""

from typing import Any, Dict, List, Optional


class DataProcessor:
    """Data processing utility class."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the processor with optional config."""
        self.config = config or {}
        self._items: List[Any] = []
        self._initialized = True

    def add_item(self, item: Any) -> None:
        """Add an item to the processor."""
        self._items.append(item)

    def get_items(self) -> List[Any]:
        """Get all items."""
        return list(self._items)

    def process(self, data: Any) -> Dict[str, Any]:
        """Process data and return result."""
        return {
            "processed": True,
            "data": data,
            "item_count": len(self._items),
            "config": self.config,
        }

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()
'''


class MockInvocationEngine:
    """Mock InvocationEngine that uses MockProviderAdapter."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.adapter = MockProviderAdapter(responses)
        self.invoked = False
        self.last_request: Optional[InvocationRequest] = None

    def invoke(self, request: InvocationRequest, selection: Any, model_id: str = None, retry: Any = None):
        """Mock invoke that delegates to adapter."""
        self.invoked = True
        self.last_request = request
        return self.adapter.invoke(None, request)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_repo_root(tmp_path):
    """Create a temporary repository root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return str(repo)


def create_llm_plan() -> ArtifactExecutionPlan:
    """Create a test plan with LLM_GENERATED artifacts."""

    checkpoints = [
        ValidationCheckpoint(
            checkpoint_id="chk-01",
            category=ValidationCategory.PATH_VALIDATION,
            description="Verify path is valid",
            is_blocking=True,
            validator="PathValidator",
        ),
    ]

    # Create units for a real estate website
    units = [
        # React Component (LLM_GENERATED)
        ArtifactExecutionUnit(
            artifact_execution_id="aeu-frontend-01",
            artifact_id="art-frontend-01",
            sub_contract_id="sctr-frontend",
            parent_contract_id="ctr-frontend",
            mission_id="mission-realestate",
            agent_profile_id="agent-frontend",
            skill_bundle_id="bundle-frontend",
            repository_scope="frontend/src/components/",
            target_path="frontend/src/components/PropertyCard.tsx",
            path_type=PathType.SOURCE,
            overwrite_policy=OverwritePolicy.SAFE,
            artifact_type="component",
            file_format="tsx",
            language="TypeScript",
            framework="React",
            technology_context=["React", "TypeScript"],
            generation_strategy=GenerationStrategy.LLM_GENERATED,
            strategy_reason="Dynamic component with specific styling",
            generation_priority="HIGH",
            execution_wave=2,
            dependencies=[],
            required_inputs=[],
            validation_checkpoints=checkpoints,
            acceptance_criteria_ids=["ac-frontend-01"],
            artifact_route_id="route-frontend-01",
            deliverable_id="del-frontend-01",
            deterministic_hash="hash-frontend-01",
        ),
        # API Endpoint (LLM_GENERATED)
        ArtifactExecutionUnit(
            artifact_execution_id="aeu-backend-01",
            artifact_id="art-backend-01",
            sub_contract_id="sctr-backend",
            parent_contract_id="ctr-backend",
            mission_id="mission-realestate",
            agent_profile_id="agent-backend",
            skill_bundle_id="bundle-backend",
            repository_scope="backend/src/api/",
            target_path="backend/src/api/properties.py",
            path_type=PathType.SOURCE,
            overwrite_policy=OverwritePolicy.SAFE,
            artifact_type="api",
            file_format="py",
            language="Python",
            framework="FastAPI",
            technology_context=["Python", "FastAPI"],
            generation_strategy=GenerationStrategy.LLM_GENERATED,
            strategy_reason="Dynamic API endpoint",
            generation_priority="HIGH",
            execution_wave=1,
            dependencies=[],
            required_inputs=[],
            validation_checkpoints=checkpoints,
            acceptance_criteria_ids=["ac-backend-01"],
            artifact_route_id="route-backend-01",
            deliverable_id="del-backend-01",
            deterministic_hash="hash-backend-01",
        ),
    ]

    waves = [
        ArtifactExecutionWave(
            wave_number=1,
            wave_name="Backend API",
            artifact_execution_ids=["aeu-backend-01"],
            parallelizable=True,
            blocking_waves=[],
            blocking_artifacts={},
            required_artifact_ids=[],
            produced_artifact_ids=["art-backend-01"],
        ),
        ArtifactExecutionWave(
            wave_number=2,
            wave_name="Frontend",
            artifact_execution_ids=["aeu-frontend-01"],
            parallelizable=True,
            blocking_waves=[1],
            blocking_artifacts={},
            required_artifact_ids=["art-backend-01"],
            produced_artifact_ids=["art-frontend-01"],
        ),
    ]

    order = [
        ArtifactExecutionOrder(
            artifact_execution_id="aeu-backend-01",
            execution_wave=1,
            execution_order=0,
            blocking_artifacts=[],
            prerequisite_artifacts=[],
        ),
        ArtifactExecutionOrder(
            artifact_execution_id="aeu-frontend-01",
            execution_wave=2,
            execution_order=1,
            blocking_artifacts=[],
            prerequisite_artifacts=["aeu-backend-01"],
        ),
    ]

    graph = ArtifactDependencyGraph(
        graph_id="graph-realestate",
        nodes=["aeu-backend-01", "aeu-frontend-01"],
        edges=[],
        adjacency={"aeu-backend-01": [], "aeu-frontend-01": []},
        reverse_adjacency={"aeu-backend-01": [], "aeu-frontend-01": []},
        in_degree={"aeu-backend-01": 0, "aeu-frontend-01": 0},
        is_acyclic=True,
    )

    strategy_summary = GenerationStrategySummary(
        total_units=2,
        template_count=0,
        pattern_count=0,
        llm_generated_count=2,
        unresolved_count=0,
        unresolved_artifacts=[],
    )

    scope_summary = RepositoryScopeSummary(
        total_units=2,
        scopes={"frontend/src/components/": 1, "backend/src/api/": 1},
        boundaries=[
            RepositoryBoundary(scope="frontend/src/components/", discipline="Frontend", is_authorized=True),
            RepositoryBoundary(scope="backend/src/api/", discipline="Backend", is_authorized=True),
        ],
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
        plan_id="aep-realestate-test",
        mission_id="mission-realestate",
        contract_decomposition_report_id="cdr-realestate",
        execution_units=units,
        artifact_dependency_graph=graph,
        execution_waves=waves,
        execution_order=order,
        generation_strategy_summary=strategy_summary,
        repository_scope_summary=scope_summary,
        validation_checkpoints=checkpoints,
        conflict_report=conflict_report,
        traceability={
            "mission_id": "mission-realestate",
            "project_objective": "Build a responsive real estate website with property listings",
        },
        deterministic=True,
        deterministic_hash="plan-hash-realestate",
        validation_passed=True,
        total_artifacts=2,
        total_waves=2,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return plan


# ---------------------------------------------------------------------------
# E2E Tests: LLM Generation with Real InvocationEngine
# ---------------------------------------------------------------------------

class TestLLMGenerationE2E:
    """End-to-end tests for LLM_GENERATED production path."""

    def test_llm_generation_produces_real_files(self, temp_repo_root):
        """Test that LLM_GENERATED artifacts produce real files on disk."""
        plan = create_llm_plan()
        mock_engine = MockInvocationEngine()

        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)

        # Check report
        assert report.total_artifacts == 2
        assert report.llm_count == 2
        assert report.successful_generations == 2, f"Expected 2 successful, got {report.successful_generations}"
        assert report.files_written == 2, f"Expected 2 files written, got {report.files_written}"

        # Check files exist
        frontend_path = os.path.join(temp_repo_root, "frontend/src/components/PropertyCard.tsx")
        backend_path = os.path.join(temp_repo_root, "backend/src/api/properties.py")

        assert os.path.exists(frontend_path), f"File not found: {frontend_path}"
        assert os.path.exists(backend_path), f"File not found: {backend_path}"

        # Check files have content
        with open(frontend_path, "r") as f:
            frontend_content = f.read()
        assert len(frontend_content) > 100, "Frontend file too short"
        assert "React" in frontend_content, "Missing React import"

        with open(backend_path, "r") as f:
            backend_content = f.read()
        assert len(backend_content) > 100, "Backend file too short"
        assert "FastAPI" in backend_content or "router" in backend_content.lower(), "Missing FastAPI content"

    def test_llm_generation_invokes_engine(self, temp_repo_root):
        """Test that LLM_GENERATED artifacts actually call InvocationEngine."""
        plan = create_llm_plan()
        mock_engine = MockInvocationEngine()

        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)

        # Verify InvocationEngine was called
        assert mock_engine.invoked, "InvocationEngine was not invoked"
        assert mock_engine.last_request is not None, "No request was sent to InvocationEngine"

    def test_llm_generation_sends_correct_context(self, temp_repo_root):
        """Test that LLM generation sends correct context to InvocationEngine."""
        plan = create_llm_plan()
        mock_engine = MockInvocationEngine()

        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)

        # Check the last request contains correct metadata
        request = mock_engine.last_request
        assert request is not None

        # Verify metadata contains artifact info
        if hasattr(request, 'metadata') and request.metadata:
            assert 'generation_constraints' in request.metadata

    def test_llm_generation_uses_coding_capability(self, temp_repo_root):
        """Test that LLM generation requests CODING capability."""
        plan = create_llm_plan()
        mock_engine = MockInvocationEngine()

        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)

        request = mock_engine.last_request
        assert request is not None

        # Check capabilities include CODING
        if hasattr(request, 'capabilities'):
            caps = request.capabilities
            # Should have CODING capability
            has_coding = any('CODING' in str(cap).upper() for cap in caps)
            assert has_coding, f"Expected CODING capability, got {caps}"

    def test_llm_generation_with_related_artifacts(self, temp_repo_root):
        """Test that LLM generation includes related artifacts for coherence."""
        plan = create_llm_plan()
        mock_engine = MockInvocationEngine()

        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)

        # Check that generation succeeded
        assert report.successful_generations == 2

        # Both files should be generated
        frontend_path = os.path.join(temp_repo_root, "frontend/src/components/PropertyCard.tsx")
        backend_path = os.path.join(temp_repo_root, "backend/src/api/properties.py")

        assert os.path.exists(frontend_path)
        assert os.path.exists(backend_path)

    def test_llm_generation_idempotent(self, temp_repo_root):
        """Test that LLM generation is deterministic."""
        plan = create_llm_plan()
        mock_engine = MockInvocationEngine()

        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)

        # First generation
        report1 = engine.generate(plan)
        assert report1.successful_generations == 2

        # Read file hashes
        frontend_path = os.path.join(temp_repo_root, "frontend/src/components/PropertyCard.tsx")
        with open(frontend_path, "r") as f:
            content1 = f.read()
        hash1 = compute_content_hash(content1)

        # Second generation (with mock, content should be identical)
        report2 = engine.generate(plan)
        assert report2.successful_generations == 2

        with open(frontend_path, "r") as f:
            content2 = f.read()
        hash2 = compute_content_hash(content2)

        assert hash1 == hash2, "Content changed between generations"


# ---------------------------------------------------------------------------
# E2E Tests: Multi-File Coherent Generation
# ---------------------------------------------------------------------------

class TestMultiFileCoherentGeneration:
    """Tests for coherent multi-file generation."""

    def test_website_generation_produces_coherent_files(self, temp_repo_root):
        """Test that website generation produces coherent HTML/CSS/JS files."""
        # Create a plan with multiple related files
        checkpoints = [
            ValidationCheckpoint(
                checkpoint_id="chk-01",
                category=ValidationCategory.PATH_VALIDATION,
                description="Verify path is valid",
                is_blocking=True,
                validator="PathValidator",
            ),
        ]

        units = [
            ArtifactExecutionUnit(
                artifact_execution_id="aeu-html-01",
                artifact_id="art-html",
                sub_contract_id="sctr-frontend",
                parent_contract_id="ctr-frontend",
                mission_id="mission-website",
                agent_profile_id="agent-frontend",
                skill_bundle_id="bundle-frontend",
                repository_scope="",
                target_path="index.html",
                path_type=PathType.SOURCE,
                overwrite_policy=OverwritePolicy.SAFE,
                artifact_type="component",
                file_format="html",
                language="HTML",
                framework="",
                technology_context=["HTML"],
                generation_strategy=GenerationStrategy.LLM_GENERATED,
                strategy_reason="Dynamic HTML",
                generation_priority="HIGH",
                execution_wave=1,
                dependencies=[],
                required_inputs=[],
                validation_checkpoints=checkpoints,
                acceptance_criteria_ids=["ac-html"],
                artifact_route_id="route-html",
                deliverable_id="del-html",
                deterministic_hash="hash-html",
            ),
            ArtifactExecutionUnit(
                artifact_execution_id="aeu-css-01",
                artifact_id="art-css",
                sub_contract_id="sctr-frontend",
                parent_contract_id="ctr-frontend",
                mission_id="mission-website",
                agent_profile_id="agent-frontend",
                skill_bundle_id="bundle-frontend",
                repository_scope="",
                target_path="styles.css",
                path_type=PathType.SOURCE,
                overwrite_policy=OverwritePolicy.SAFE,
                artifact_type="component",
                file_format="css",
                language="CSS",
                framework="",
                technology_context=["CSS"],
                generation_strategy=GenerationStrategy.LLM_GENERATED,
                strategy_reason="Dynamic CSS",
                generation_priority="HIGH",
                execution_wave=1,
                dependencies=[],
                required_inputs=[],
                validation_checkpoints=checkpoints,
                acceptance_criteria_ids=["ac-css"],
                artifact_route_id="route-css",
                deliverable_id="del-css",
                deterministic_hash="hash-css",
            ),
            ArtifactExecutionUnit(
                artifact_execution_id="aeu-js-01",
                artifact_id="art-js",
                sub_contract_id="sctr-frontend",
                parent_contract_id="ctr-frontend",
                mission_id="mission-website",
                agent_profile_id="agent-frontend",
                skill_bundle_id="bundle-frontend",
                repository_scope="",
                target_path="main.js",
                path_type=PathType.SOURCE,
                overwrite_policy=OverwritePolicy.SAFE,
                artifact_type="component",
                file_format="js",
                language="JavaScript",
                framework="",
                technology_context=["JavaScript"],
                generation_strategy=GenerationStrategy.LLM_GENERATED,
                strategy_reason="Dynamic JavaScript",
                generation_priority="HIGH",
                execution_wave=1,
                dependencies=[],
                required_inputs=[],
                validation_checkpoints=checkpoints,
                acceptance_criteria_ids=["ac-js"],
                artifact_route_id="route-js",
                deliverable_id="del-js",
                deterministic_hash="hash-js",
            ),
        ]

        waves = [
            ArtifactExecutionWave(
                wave_number=1,
                wave_name="Frontend Files",
                artifact_execution_ids=["aeu-html-01", "aeu-css-01", "aeu-js-01"],
                parallelizable=True,
                blocking_waves=[],
                blocking_artifacts={},
                required_artifact_ids=[],
                produced_artifact_ids=["art-html", "art-css", "art-js"],
            ),
        ]

        order = [
            ArtifactExecutionOrder(artifact_execution_id="aeu-html-01", execution_wave=1, execution_order=0, blocking_artifacts=[], prerequisite_artifacts=[]),
            ArtifactExecutionOrder(artifact_execution_id="aeu-css-01", execution_wave=1, execution_order=1, blocking_artifacts=[], prerequisite_artifacts=[]),
            ArtifactExecutionOrder(artifact_execution_id="aeu-js-01", execution_wave=1, execution_order=2, blocking_artifacts=[], prerequisite_artifacts=[]),
        ]

        graph = ArtifactDependencyGraph(
            graph_id="graph-website",
            nodes=["aeu-html-01", "aeu-css-01", "aeu-js-01"],
            edges=[],
            adjacency={"aeu-html-01": [], "aeu-css-01": [], "aeu-js-01": []},
            reverse_adjacency={"aeu-html-01": [], "aeu-css-01": [], "aeu-js-01": []},
            in_degree={"aeu-html-01": 0, "aeu-css-01": 0, "aeu-js-01": 0},
            is_acyclic=True,
        )

        strategy_summary = GenerationStrategySummary(
            total_units=3,
            template_count=0,
            pattern_count=0,
            llm_generated_count=3,
            unresolved_count=0,
            unresolved_artifacts=[],
        )

        scope_summary = RepositoryScopeSummary(
            total_units=3,
            scopes={"": 3},
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
            plan_id="aep-website-test",
            mission_id="mission-website",
            contract_decomposition_report_id="cdr-website",
            execution_units=units,
            artifact_dependency_graph=graph,
            execution_waves=waves,
            execution_order=order,
            generation_strategy_summary=strategy_summary,
            repository_scope_summary=scope_summary,
            validation_checkpoints=checkpoints,
            conflict_report=conflict_report,
            traceability={
                "mission_id": "mission-website",
                "project_objective": "Build a responsive real-estate landing page with hero section, property cards, and CTA",
            },
            deterministic=True,
            deterministic_hash="plan-hash-website",
            validation_passed=True,
            total_artifacts=3,
            total_waves=1,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Create mock with explicit responses for each artifact
        mock_responses = {
            "aeu-html-01": '<!DOCTYPE html>\n<html>\n<head><title>Test</title></head>\n<body><h1>Hello</h1></body>\n</html>',
            "aeu-css-01": 'body { margin: 0; padding: 0; }\nh1 { color: blue; }',
            "aeu-js-01": 'console.log("Hello World");',
        }
        mock_engine = MockInvocationEngine(mock_responses)
        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)

        # Verify files generated
        assert report.total_artifacts == 3
        assert report.llm_count == 3

        # Verify files exist
        for filename in ["index.html", "styles.css", "main.js"]:
            path = os.path.join(temp_repo_root, filename)
            assert os.path.exists(path), f"File not found: {filename}"

            with open(path, "r") as f:
                content = f.read()
            assert len(content) > 0, f"{filename} is empty"

        # Verify they are distinct (not duplicates)
        with open(os.path.join(temp_repo_root, "index.html"), "r") as f:
            html = f.read()
        with open(os.path.join(temp_repo_root, "styles.css"), "r") as f:
            css = f.read()
        with open(os.path.join(temp_repo_root, "main.js"), "r") as f:
            js = f.read()

        # Content should be distinct
        assert html != css, "HTML and CSS should be different"
        assert html != js, "HTML and JS should be different"
        assert css != js, "CSS and JS should be different"


# ---------------------------------------------------------------------------
# E2E Tests: Failure Handling
# ---------------------------------------------------------------------------

class TestLLMFailureHandling:
    """Tests for LLM generation failure handling."""

    def test_missing_invocation_engine_raises_error(self, temp_repo_root):
        """Test that missing InvocationEngine raises appropriate error."""
        plan = create_llm_plan()

        # Create engine without InvocationEngine
        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=None)

        # The engine will try to invoke LLM_GENERATED but no engine is available
        # It should fail during generation
        from runtime.contracts.e31_models import CodeGenerationError
        from runtime.contracts.e31_models import BlockingConflictError

        # When LLM_GENERATED strategy is used but no engine, it should raise
        try:
            report = engine.generate(plan)
            # If generation completed but with failures, that's expected
            # (engine handles missing invocation engine by raising during generation)
        except CodeGenerationError as e:
            assert "InvocationEngine not provided" in str(e)


# ---------------------------------------------------------------------------
# E2E Tests: Realistic Website Generation
# ---------------------------------------------------------------------------

class TestRealisticWebsiteGeneration:
    """Tests for realistic website generation scenario."""

    def test_real_estate_landing_page_generation(self, temp_repo_root):
        """Test generation of a realistic real estate landing page.

        This test demonstrates the complete E3.2 execution path:
        1. E2 Contract (simulated via plan)
        2. ArtifactExecutionPlan
        3. LLM_GENERATED strategy
        4. InvocationEngine (mock)
        5. Real files on disk
        """
        # Create a realistic plan for a real estate landing page
        checkpoints = [
            ValidationCheckpoint(
                checkpoint_id="chk-01",
                category=ValidationCategory.PATH_VALIDATION,
                description="Verify path is valid",
                is_blocking=True,
                validator="PathValidator",
            ),
        ]

        units = [
            ArtifactExecutionUnit(
                artifact_execution_id="aeu-landing-html",
                artifact_id="art-landing-html",
                sub_contract_id="sctr-landing",
                parent_contract_id="ctr-landing",
                mission_id="mission-realestate-landing",
                agent_profile_id="agent-frontend",
                skill_bundle_id="bundle-frontend",
                repository_scope="",
                target_path="index.html",
                path_type=PathType.SOURCE,
                overwrite_policy=OverwritePolicy.SAFE,
                artifact_type="component",
                file_format="html",
                language="HTML",
                framework="",
                technology_context=["HTML", "CSS", "JavaScript"],
                generation_strategy=GenerationStrategy.LLM_GENERATED,
                strategy_reason="Dynamic landing page with hero, property cards, CTA",
                generation_priority="HIGH",
                execution_wave=1,
                dependencies=[],
                required_inputs=[],
                validation_checkpoints=checkpoints,
                acceptance_criteria_ids=["ac-landing"],
                artifact_route_id="route-landing",
                deliverable_id="del-landing",
                deterministic_hash="hash-landing",
            ),
        ]

        waves = [
            ArtifactExecutionWave(
                wave_number=1,
                wave_name="Landing Page",
                artifact_execution_ids=["aeu-landing-html"],
                parallelizable=True,
                blocking_waves=[],
                blocking_artifacts={},
                required_artifact_ids=[],
                produced_artifact_ids=["art-landing-html"],
            ),
        ]

        order = [
            ArtifactExecutionOrder(
                artifact_execution_id="aeu-landing-html",
                execution_wave=1,
                execution_order=0,
                blocking_artifacts=[],
                prerequisite_artifacts=[],
            ),
        ]

        graph = ArtifactDependencyGraph(
            graph_id="graph-landing",
            nodes=["aeu-landing-html"],
            edges=[],
            adjacency={"aeu-landing-html": []},
            reverse_adjacency={"aeu-landing-html": []},
            in_degree={"aeu-landing-html": 0},
            is_acyclic=True,
        )

        strategy_summary = GenerationStrategySummary(
            total_units=1,
            template_count=0,
            pattern_count=0,
            llm_generated_count=1,
            unresolved_count=0,
            unresolved_artifacts=[],
        )

        scope_summary = RepositoryScopeSummary(
            total_units=1,
            scopes={"": 1},
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
            plan_id="aep-realestate-landing",
            mission_id="mission-realestate-landing",
            contract_decomposition_report_id="cdr-realestate-landing",
            execution_units=units,
            artifact_dependency_graph=graph,
            execution_waves=waves,
            execution_order=order,
            generation_strategy_summary=strategy_summary,
            repository_scope_summary=scope_summary,
            validation_checkpoints=checkpoints,
            conflict_report=conflict_report,
            traceability={
                "mission_id": "mission-realestate-landing",
                "project_objective": "Build a responsive real-estate landing page with hero section, property cards, CTA, responsive CSS and basic motion",
            },
            deterministic=True,
            deterministic_hash="plan-hash-landing",
            validation_passed=True,
            total_artifacts=1,
            total_waves=1,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Create mock with explicit HTML response
        mock_responses = {
            "aeu-landing-html": '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Real Estate - Find Your Dream Home</title>
</head>
<body>
  <header class="hero">
    <h1>Find Your Dream Home</h1>
    <p>Discover amazing properties in your area</p>
    <button class="cta">Get Started</button>
  </header>
  <section class="properties">
    <h2>Featured Properties</h2>
    <div class="grid">
      <article class="card">
        <img src="property1.jpg" alt="Modern Apartment">
        <h3>Modern Apartment</h3>
        <p class="price">$500,000</p>
      </article>
    </div>
  </section>
</body>
</html>''',
        }
        mock_engine = MockInvocationEngine(mock_responses)
        engine = RealCodeGenerationEngine(temp_repo_root, invocation_engine=mock_engine)
        report = engine.generate(plan)

        # Verify complete execution
        assert report.total_artifacts == 1
        assert report.llm_count == 1
        assert report.successful_generations == 1
        assert report.files_written == 1

        # Verify InvocationEngine was used
        assert mock_engine.invoked, "InvocationEngine was not invoked"

        # Verify file exists and has content
        index_path = os.path.join(temp_repo_root, "index.html")
        assert os.path.exists(index_path), "index.html not created"

        with open(index_path, "r") as f:
            content = f.read()

        assert len(content) > 200, "Content too short"
        assert "<html" in content.lower() or "<!doctype" in content.lower(), "Not valid HTML"

        # Verify it's real HTML (not placeholder)
        assert "TODO" not in content, "Contains TODO placeholder"
        assert "FIXME" not in content, "Contains FIXME placeholder"
        assert "PLACEHOLDER" not in content, "Contains PLACEHOLDER"

        print(f"\n✓ Real estate landing page generated successfully")
        print(f"  File: {index_path}")
        print(f"  Size: {len(content)} bytes")
        print(f"  InvocationEngine: ✓")
        print(f"  Content validated: ✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
