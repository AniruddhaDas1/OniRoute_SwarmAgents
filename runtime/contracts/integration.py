"""E3.4 Repository & Workspace Integration Engine.

Phase E3.4 — Repository & Workspace Integration.

Provides the integration layer that connects mission requirements to
ArtifactExecutionPlan and orchestrates end-to-end execution through
the existing E3.1/E3.3 runtime layers to produce real project files.

Architecture:
    MissionRequirements
        ↓
    MissionRequirementsAdapter (E3.4.1)
        ↓
    IntentAnalyzer → EngineeringExecutionPlan (E3.4.2)
        ↓
    WorkspaceResolver (E3.4.3)
        ↓
    ArtifactExecutionOrchestrator (from E3.3)
        ↓
    RealCodeGenerationEngine (from E3.1)
        ↓
    RepositoryWriter (from E3.1)
        ↓
    ProjectExecutionResult
        ↓
    REAL PROJECT FILES

Reuses:
- ArtifactExecutionOrchestrator (E3.3 orchestrator.py)
- RealCodeGenerationEngine (E3.1 engine.py)
- RepositoryWriter (E3.1 writer.py)
- ArtifactExecutionPlan (E2.3 e23_models.py)
- IntentAnalyzer (intent.py)
- EngineeringExecutionPlan (workspace/plan.py)

Does NOT create:
- New invocation engine
- New generation engine
- New orchestrator
- New repository writer
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from runtime.contracts.e34_models import (
    ArtifactFileResult,
    ExecutionError,
    InvalidMissionError,
    InvalidPlanError,
    ProjectExecutionResult,
    ProjectInitializer,
    ProjectType,
    WorkspaceBoundaryError,
    WorkspaceResolution,
    WorkspaceResolutionError,
    compute_execution_result_hash,
)
from runtime.contracts.e23_models import ArtifactExecutionPlan

if TYPE_CHECKING:
    from runtime.contracts.orchestrator import ArtifactExecutionOrchestrator
    from runtime.contracts.generators.engine import RealCodeGenerationEngine


# ---------------------------------------------------------------------------
# E3.4.1 - Mission Requirements Adapter
# ---------------------------------------------------------------------------

class MissionRequirementsAdapter:
    """Converts various mission inputs to MissionRequirements.

    Adapts:
    - Natural language mission strings
    - Existing mission objects from runtime.mission
    - EngineeringExecutionPlan from workspace.plan
    """

    # Known technology mappings
    TECHNOLOGY_KEYWORDS = {
        "python": ["Python"],
        "typescript": ["TypeScript", "JavaScript"],
        "javascript": ["JavaScript"],
        "react": ["React", "TypeScript"],
        "next": ["Next.js", "React", "TypeScript"],
        "vue": ["Vue", "JavaScript"],
        "fastapi": ["FastAPI", "Python"],
        "django": ["Django", "Python"],
        "flask": ["Flask", "Python"],
        "go": ["Go"],
        "rust": ["Rust"],
        "java": ["Java"],
        "kotlin": ["Kotlin"],
        "swift": ["Swift"],
        "dart": ["Dart"],
        "flutter": ["Flutter", "Dart"],
        "sql": ["SQL"],
        "postgresql": ["PostgreSQL", "SQL"],
        "mysql": ["MySQL", "SQL"],
        "mongodb": ["MongoDB"],
        "redis": ["Redis"],
        "docker": ["Docker"],
        "kubernetes": ["Kubernetes", "Docker"],
        "aws": ["AWS"],
        "gcp": ["GCP"],
        "azure": ["Azure"],
    }

    PROJECT_TYPE_KEYWORDS = {
        ProjectType.WEB_APPLICATION: ["website", "web app", "web application", "landing page", "portfolio"],
        ProjectType.API_SERVICE: ["api", "rest api", "backend", "microservice", "grpc"],
        ProjectType.FULLSTACK_APPLICATION: ["fullstack", "full stack", "crud app"],
        ProjectType.MOBILE_APPLICATION: ["mobile", "ios", "android", "app"],
        ProjectType.DESKTOP_APPLICATION: ["desktop", "electron"],
        ProjectType.LIBRARY_PACKAGE: ["library", "package", "sdk", "module"],
        ProjectType.INFRASTRUCTURE: ["infrastructure", "terraform", "ansible", "deployment"],
        ProjectType.DATA_PIPELINE: ["pipeline", "etl", "data processing"],
        ProjectType.DOCUMENTATION: ["docs", "documentation", "readme"],
    }

    FRAMEWORK_KEYWORDS = {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue",
        "angular": "Angular",
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "express": "Express",
        "spring": "Spring",
        "rails": "Rails",
        "flutter": "Flutter",
    }

    DISCIPLINE_MAPPINGS = {
        ProjectType.WEB_APPLICATION: ["Frontend", "Backend"],
        ProjectType.API_SERVICE: ["Backend"],
        ProjectType.FULLSTACK_APPLICATION: ["Frontend", "Backend", "Database"],
        ProjectType.MOBILE_APPLICATION: ["Mobile"],
        ProjectType.DESKTOP_APPLICATION: ["Desktop"],
        ProjectType.LIBRARY_PACKAGE: ["Backend"],
        ProjectType.INFRASTRUCTURE: ["Infrastructure"],
        ProjectType.DATA_PIPELINE: ["Data Engineering"],
        ProjectType.DOCUMENTATION: ["Documentation"],
    }

    def adapt_from_string(
        self,
        mission: str,
        mission_id: Optional[str] = None,
        workspace_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Adapt a natural language mission string to requirements dict.

        Args:
            mission: Natural language mission string
            mission_id: Optional mission ID
            workspace_root: Optional workspace root path

        Returns:
            Requirements dict compatible with MissionRequirements
        """
        mission_lower = mission.lower()

        # Detect project type
        project_type = ProjectType.UNKNOWN
        for ptype, keywords in self.PROJECT_TYPE_KEYWORDS.items():
            if any(kw in mission_lower for kw in keywords):
                project_type = ptype
                break

        # Detect technology stack
        tech_stack = []
        for keyword, technologies in self.TECHNOLOGY_KEYWORDS.items():
            if keyword in mission_lower:
                for tech in technologies:
                    if tech not in tech_stack:
                        tech_stack.append(tech)

        # Detect framework
        framework_hint = ""
        for keyword, framework in self.FRAMEWORK_KEYWORDS.items():
            if keyword in mission_lower:
                framework_hint = framework
                break

        # Detect language
        language_hint = ""
        if tech_stack:
            for lang in ["TypeScript", "Python", "JavaScript", "Go", "Rust", "Java", "Swift", "Dart"]:
                if lang in tech_stack:
                    language_hint = lang
                    break

        # Determine disciplines
        disciplines = self.DISCIPLINE_MAPPINGS.get(project_type, ["Software Engineering"])

        # Generate mission ID if not provided
        if not mission_id:
            mission_id = self._generate_mission_id(mission)

        # Extract key deliverables from mission
        deliverables = self._extract_deliverables(mission, project_type)

        return {
            "mission_id": mission_id,
            "primary_goal": mission.strip(),
            "project_type": project_type,
            "technology_stack": tech_stack,
            "framework_hint": framework_hint,
            "language_hint": language_hint,
            "required_deliverables": deliverables,
            "required_disciplines": disciplines,
            "constraints": [],
            "quality_requirements": ["Clean code", "Type safety", "Error handling"],
            "workspace_root": workspace_root or "",
            "workspace_id": f"ws-{mission_id[4:]}",
            "blueprint_id": "",
        }

    def _generate_mission_id(self, mission: str) -> str:
        """Generate a deterministic mission ID from mission string."""
        payload = f"msn-{mission.strip()}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"msn-{digest}"

    def _extract_deliverables(
        self, mission: str, project_type: ProjectType
    ) -> List[str]:
        """Extract required deliverables from mission and project type."""
        mission_lower = mission.lower()
        deliverables = []

        # Always add base deliverables
        deliverables.append("Project Configuration")

        if project_type in (ProjectType.WEB_APPLICATION, ProjectType.FULLSTACK_APPLICATION):
            deliverables.extend([
                "Frontend Application",
                "UI Components",
            ])
            if "api" in mission_lower or "backend" in mission_lower:
                deliverables.append("Backend API")

        if project_type == ProjectType.API_SERVICE:
            deliverables.extend([
                "API Endpoints",
                "Request Handlers",
            ])

        if project_type == ProjectType.MOBILE_APPLICATION:
            deliverables.append("Mobile App Screens")

        return deliverables


# ---------------------------------------------------------------------------
# E3.4.2 - Mission to Plan Converter
# ---------------------------------------------------------------------------

class MissionToPlanConverter:
    """Converts mission requirements to ArtifactExecutionPlan.

    This is the bridge between mission intent and the E2.3 planning system.
    """

    def __init__(self, planner: Any):
        """Initialize with an ArtifactExecutionPlanner.

        Args:
            planner: ArtifactExecutionPlanner from runtime.contracts.planner
        """
        self._planner = planner

    def convert(
        self,
        requirements: Dict[str, Any],
        workspace_root: Optional[str] = None,
    ) -> ArtifactExecutionPlan:
        """Convert mission requirements to ArtifactExecutionPlan.

        This method creates a minimal ContractDecompositionReport that
        feeds into the existing ArtifactExecutionPlanner.

        The converter synthesizes:
        - SubContracts from mission requirements
        - ArtifactRoutes for each deliverable
        - Execution waves from discipline dependencies

        Args:
            requirements: Mission requirements dict
            workspace_root: Optional workspace root path

        Returns:
            ArtifactExecutionPlan ready for execution

        Raises:
            InvalidPlanError: If plan cannot be generated
        """
        try:
            # Build minimal decomposition report from requirements
            decomposition_report = self._build_decomposition_report(requirements)

            # Use existing planner
            plan = self._planner.plan(decomposition_report)

            return plan

        except Exception as e:
            raise InvalidPlanError(f"Failed to convert mission to plan: {e}")

    def _build_decomposition_report(
        self, requirements: Dict[str, Any]
    ) -> Any:
        """Build a minimal ContractDecompositionReport from requirements.

        This creates the intermediate structure needed by the planner.
        """
        from runtime.contracts.decomposition import (
            ArtifactRoute,
            ContractDecompositionReport,
            DependencyEdge,
            DependencyGraph,
            DependencyType,
            ExecutionWave,
            ParallelExecutionGroup,
            SubContract,
        )

        mission_id = requirements.get("mission_id", "msn-unknown")
        report_id = f"cdr-{mission_id[4:]}"
        tech_stack = requirements.get("technology_stack", [])
        disciplines = requirements.get("required_disciplines", ["Software Engineering"])
        deliverables = requirements.get("required_deliverables", [])
        project_type = requirements.get("project_type", ProjectType.UNKNOWN)

        # Build sub-contracts for each discipline
        sub_contracts = []
        artifact_routes = []
        sctr_counter = 0
        route_counter = 0

        for discipline in disciplines:
            sctr_counter += 1
            sctr_id = f"sctr-{sctr_counter:03d}"
            parent_ctr_id = f"ctr-{sctr_counter // 3 + 1:03d}"

            # Map discipline to scope
            scope = self._discipline_to_scope(discipline, project_type)

            # Compute deterministic hash
            hash_payload = f"{sctr_id}:{parent_ctr_id}:{mission_id}"
            deterministic_hash = hashlib.sha256(hash_payload.encode("utf-8")).hexdigest()

            # Build sub-contract
            sub_ctr = SubContract(
                sub_contract_id=sctr_id,
                parent_contract_id=parent_ctr_id,
                mission_id=mission_id,
                agent_profile_id=f"profile-{discipline.lower()}",
                skill_bundle_id=f"bundle-{discipline.lower()}",
                objective=f"{discipline} implementation",
                required_capabilities=["CODING"],
                required_skills=self._discipline_to_skills(discipline),
                inputs=[],
                expected_deliverables=self._get_discipline_deliverables(discipline, deliverables),
                acceptance_criteria=[
                    f"{discipline} implementation compiles without errors",
                    f"{discipline} code follows style guidelines",
                ],
                dependencies=[],
                constraints=[],
                repository_scope=scope,
                technology_context=tech_stack,
                priority="P1_HIGH",
                execution_order=sctr_counter,
                execution_wave=self._discipline_to_wave(discipline),
                risk_level="MEDIUM",
                is_atomic=False,
                decomposition_reason="E3.4 Mission Requirements Decomposition",
                owned_deliverables=self._get_discipline_deliverables(discipline, deliverables),
                traceability={},
                deterministic_hash=deterministic_hash,
            )
            sub_contracts.append(sub_ctr)

            # Build artifact routes for each deliverable
            discipline_deliverables = self._get_discipline_deliverables(discipline, deliverables)
            for dlv_idx, deliverable in enumerate(discipline_deliverables, start=1):
                route_counter += 1
                route_id = f"route-{route_counter:03d}"

                # Determine artifact type
                artifact_type = self._deliverable_to_artifact_type(deliverable)

                # Build route path
                route_path = f"{scope}{self._deliverable_to_filename(deliverable, tech_stack)}"

                route = ArtifactRoute(
                    route_id=route_id,
                    artifact_id=f"art-{route_counter:03d}",
                    producing_sub_contract_id=sctr_id,
                    consuming_sub_contract_ids=[],
                    artifact_type=artifact_type,
                    repository_path=route_path,
                    owned_by_discipline=discipline,
                    produced_by_skill="",
                )
                artifact_routes.append(route)

        # Build dependency graph
        edges = []
        for i, sctr in enumerate(sub_contracts):
            if i > 0:
                edges.append(DependencyEdge(
                    from_id=sub_contracts[i - 1].sub_contract_id,
                    to_id=sctr.sub_contract_id,
                    dependency_type=DependencyType.REQUIRES,
                ))

        dependency_graph = DependencyGraph(
            graph_id=f"dg-{mission_id[4:]}",
            nodes=[s.sub_contract_id for s in sub_contracts],
            edges=edges,
        )

        # Build execution waves
        waves = []
        wave_map: Dict[int, List[str]] = {}
        for sctr in sub_contracts:
            wave_num = sctr.execution_wave
            if wave_num not in wave_map:
                wave_map[wave_num] = []
            wave_map[wave_num].append(sctr.sub_contract_id)

        for wave_num, sctr_ids in sorted(wave_map.items()):
            waves.append(ExecutionWave(
                wave_number=wave_num,
                wave_name=f"Wave {wave_num}: {', '.join(wave_map[wave_num])}",
                sub_contract_ids=sctr_ids,
                parallelizable=wave_num > 1,
            ))

        # Compute report hash
        report_hash_payload = {
            "report_id": report_id,
            "mission_id": mission_id,
            "sub_contracts": [s.model_dump(mode="json") for s in sub_contracts],
            "artifact_routes": [r.model_dump(mode="json") for r in artifact_routes],
        }
        report_hash = hashlib.sha256(
            json.dumps(report_hash_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        # Build report
        return ContractDecompositionReport(
            report_id=report_id,
            mission_id=mission_id,
            parent_contract_report_id=f"ecr-{mission_id[4:]}",
            sub_contracts=sub_contracts,
            artifact_routes=artifact_routes,
            dependency_graph=dependency_graph,
            execution_waves=waves,
            parallel_execution_groups=[],
            coverage={},
            validation_results={},
            traceability={
                "mission_id": mission_id,
                "source": "E3.4_MissionToPlanConverter",
            },
            deterministic=True,
            report_hash=report_hash,
            total_sub_contracts=len(sub_contracts),
            total_waves=len(waves),
            total_artifact_routes=len(artifact_routes),
            parallelizable_groups=sum(1 for w in waves if w.parallelizable),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _discipline_to_scope(self, discipline: str, project_type: ProjectType) -> str:
        """Map discipline to repository scope."""
        scope_map = {
            "Frontend": "src/frontend/",
            "Backend": "src/backend/",
            "Database": "src/database/",
            "Mobile": "src/mobile/",
            "Desktop": "src/desktop/",
            "Infrastructure": "infra/",
            "Data Engineering": "src/data/",
            "Documentation": "docs/",
            "Testing": "tests/",
            "Security": "src/security/",
            "Software Engineering": "src/",
        }
        return scope_map.get(discipline, "src/")

    def _discipline_to_wave(self, discipline: str) -> int:
        """Map discipline to execution wave number."""
        wave_map = {
            "Database": 1,
            "Backend": 2,
            "Frontend": 3,
            "Mobile": 3,
            "Desktop": 3,
            "Infrastructure": 2,
            "Data Engineering": 2,
            "Documentation": 4,
            "Testing": 4,
            "Security": 2,
            "Software Engineering": 2,
        }
        return wave_map.get(discipline, 2)

    def _discipline_to_skills(self, discipline: str) -> List[str]:
        """Map discipline to required skills."""
        skill_map = {
            "Frontend": ["Frontend Development", "UI Implementation", "Responsive Design"],
            "Backend": ["API Development", "Server Logic", "Database Integration"],
            "Database": ["Schema Design", "Migration Writing", "Query Optimization"],
            "Mobile": ["Mobile Development", "Screen Implementation", "Platform Integration"],
            "Desktop": ["Desktop Development", "Window Management", "Native Integration"],
            "Infrastructure": ["Infrastructure as Code", "Containerization", "Deployment"],
            "Data Engineering": ["Data Pipeline", "ETL Development", "Data Processing"],
            "Documentation": ["Technical Writing", "API Documentation", "Readme Creation"],
            "Testing": ["Test Writing", "Test Coverage", "Integration Testing"],
            "Security": ["Security Analysis", "Secure Coding", "Vulnerability Assessment"],
            "Software Engineering": ["Software Development", "Code Implementation", "Module Design"],
        }
        return skill_map.get(discipline, ["Software Development"])

    def _get_discipline_deliverables(
        self, discipline: str, all_deliverables: List[str]
    ) -> List[str]:
        """Filter deliverables for a specific discipline."""
        if not all_deliverables:
            return [f"{discipline} Implementation"]

        # Map deliverables to disciplines
        discipline_keywords = {
            "Frontend": ["frontend", "ui", "component", "screen", "web"],
            "Backend": ["backend", "api", "server", "endpoint", "handler"],
            "Database": ["database", "schema", "migration", "query"],
            "Mobile": ["mobile", "app", "screen"],
            "Desktop": ["desktop", "window", "native"],
            "Infrastructure": ["infrastructure", "deployment", "docker", "config"],
            "Data Engineering": ["pipeline", "data", "etl"],
            "Documentation": ["documentation", "readme", "docs"],
            "Testing": ["test", "spec", "coverage"],
            "Security": ["security", "auth", "permission"],
        }

        keywords = discipline_keywords.get(discipline, [])
        matched = [d for d in all_deliverables if any(kw in d.lower() for kw in keywords)]

        if not matched:
            return [f"{discipline} Implementation"]

        return matched

    def _deliverable_to_artifact_type(self, deliverable: str) -> str:
        """Map deliverable description to artifact type."""
        lower = deliverable.lower()
        if "component" in lower or "ui" in lower or "screen" in lower:
            return "component"
        if "api" in lower or "endpoint" in lower or "handler" in lower:
            return "api_endpoint"
        if "schema" in lower or "migration" in lower or "database" in lower:
            return "database_schema"
        if "test" in lower or "spec" in lower:
            return "tests"
        if "config" in lower or "configuration" in lower:
            return "config"
        if "auth" in lower or "security" in lower:
            return "auth_flow"
        if "documentation" in lower or "readme" in lower:
            return "documentation"
        if "pipeline" in lower or "etl" in lower:
            return "data_pipeline"
        return "frontend_application"

    def _deliverable_to_filename(self, deliverable: str, tech_stack: List[str]) -> str:
        """Map deliverable to filename with extension."""
        lower = deliverable.lower().replace(" ", "_")

        # Determine extension from tech stack
        ext = "ts"
        if "Python" in tech_stack:
            ext = "py"
        elif "JavaScript" in tech_stack:
            ext = "js"
        elif "Go" in tech_stack:
            ext = "go"
        elif "Rust" in tech_stack:
            ext = "rs"

        # Map artifact type to filename
        if "component" in lower or "ui" in lower or "screen" in lower:
            return f"components/{lower}.{ext}x"
        if "api" in lower or "endpoint" in lower:
            return f"api/{lower}.{ext}"
        if "schema" in lower or "migration" in lower:
            return f"database/{lower}.sql"
        if "test" in lower or "spec" in lower:
            return f"tests/{lower}.test.{ext}"
        if "config" in lower or "configuration" in lower:
            return f"config/{lower}.json"
        if "documentation" in lower or "readme" in lower:
            return f"docs/{lower}.md"

        return f"{lower}.{ext}"


# ---------------------------------------------------------------------------
# E3.4.3 - Workspace Resolver
# ---------------------------------------------------------------------------

class WorkspaceResolver:
    """Resolves workspace boundaries for artifact generation.

    Enforces:
    - Path traversal prevention
    - Absolute path rejection
    - Repository scope boundaries
    """

    def __init__(self, workspace_root: str):
        """Initialize with workspace root.

        Args:
            workspace_root: Absolute path to workspace root
        """
        self._workspace_root = Path(workspace_root).resolve()

    def resolve(
        self,
        mission_id: str,
        plan: ArtifactExecutionPlan,
    ) -> WorkspaceResolution:
        """Resolve workspace boundaries for the plan.

        Args:
            mission_id: Mission identifier
            plan: ArtifactExecutionPlan

        Returns:
            WorkspaceResolution with boundary information

        Raises:
            WorkspaceBoundaryError: If paths violate boundaries
        """
        # Collect all scopes from the plan
        scopes = set()
        for unit in plan.execution_units:
            if unit.repository_scope:
                scopes.add(unit.repository_scope)

        # Validate all target paths
        for unit in plan.execution_units:
            self._validate_path(unit.target_path, unit.artifact_execution_id)

        # Extract required directories
        required_dirs = ProjectInitializer.get_required_directories(
            str(self._workspace_root), plan
        )

        return WorkspaceResolution(
            workspace_id=f"ws-{mission_id[4:]}",
            workspace_root=str(self._workspace_root),
            repository_scope=list(scopes)[0] if scopes else "src/",
            allowed_scopes=sorted(scopes) if scopes else ["src/"],
            is_boundary_enforced=True,
            required_directories=required_dirs,
            path_traversal_prevented=True,
            absolute_paths_allowed=False,
        )

    def _validate_path(self, target_path: str, artifact_id: str) -> None:
        """Validate a target path is within workspace boundaries.

        Args:
            target_path: Repository-relative target path
            artifact_id: Artifact ID for error reporting

        Raises:
            WorkspaceBoundaryError: If path violates boundaries
        """
        # Check for absolute paths
        if target_path.startswith("/"):
            raise WorkspaceBoundaryError(
                f"Artifact {artifact_id}: absolute paths not allowed: {target_path}"
            )

        # Check for path traversal
        if ".." in target_path:
            raise WorkspaceBoundaryError(
                f"Artifact {artifact_id}: path traversal not allowed: {target_path}"
            )

        # Normalize and check
        normalized = str(PurePosixPath(target_path))
        if normalized.startswith("/"):
            raise WorkspaceBoundaryError(
                f"Artifact {artifact_id}: normalized path is absolute: {normalized}"
            )


# ---------------------------------------------------------------------------
# E3.4.4 - Execution Engine
# ---------------------------------------------------------------------------

class ProjectExecutionEngine:
    """Orchestrates end-to-end project execution.

    Connects:
    - MissionRequirements
    - ArtifactExecutionPlan
    - ArtifactExecutionOrchestrator
    - RealCodeGenerationEngine
    - RepositoryWriter

    Produces:
    - ProjectExecutionResult
    - REAL PROJECT FILES
    """

    def __init__(
        self,
        workspace_root: str,
        generation_engine: "RealCodeGenerationEngine",
        orchestrator: "ArtifactExecutionOrchestrator",
    ):
        """Initialize the execution engine.

        Args:
            workspace_root: Absolute path to workspace root
            generation_engine: RealCodeGenerationEngine instance
            orchestrator: ArtifactExecutionOrchestrator instance
        """
        self._workspace_root = Path(workspace_root).resolve()
        self._generation_engine = generation_engine
        self._orchestrator = orchestrator

    def execute(self, plan: ArtifactExecutionPlan) -> ProjectExecutionResult:
        """Execute a complete project plan.

        Args:
            plan: ArtifactExecutionPlan from E2.3

        Returns:
            ProjectExecutionResult with complete execution results

        Raises:
            ExecutionError: If execution fails
        """
        start_time = time.time()
        execution_started = datetime.now(timezone.utc).isoformat()

        # Resolve workspace
        workspace_resolution = self._resolve_workspace(plan)

        # Initialize project directories
        self._initialize_directories(workspace_resolution)

        # Execute through orchestrator
        try:
            report = self._orchestrator.execute(plan)
        except Exception as e:
            execution_completed = datetime.now(timezone.utc).isoformat()
            total_duration = (time.time() - start_time) * 1000

            return ProjectExecutionResult(
                execution_id=f"exec-{plan.plan_id[:8]}",
                mission_id=plan.mission_id,
                plan_id=plan.plan_id,
                workspace_id=workspace_resolution.workspace_id,
                execution_status="FAILED",
                is_success=False,
                total_artifacts=len(plan.execution_units),
                artifacts_completed=0,
                artifacts_failed=len(plan.execution_units),
                files_written=0,
                total_waves=len(plan.execution_waves),
                waves_executed=0,
                execution_started=execution_started,
                execution_completed=execution_completed,
                total_duration_ms=total_duration,
                errors=[str(e)],
                failure_evidence=[f"Orchestrator execution failed: {e}"],
                workspace_root=str(self._workspace_root),
                repository_scope=workspace_resolution.repository_scope,
            )

        # Build result from orchestrator report
        return self._build_result(
            plan, report, execution_started, start_time, workspace_resolution
        )

    def _resolve_workspace(
        self, plan: ArtifactExecutionPlan
    ) -> WorkspaceResolution:
        """Resolve workspace for the plan."""
        resolver = WorkspaceResolver(str(self._workspace_root))
        return resolver.resolve(plan.mission_id, plan)

    def _initialize_directories(self, resolution: WorkspaceResolution) -> None:
        """Initialize required project directories."""
        for directory in resolution.required_directories:
            dir_path = self._workspace_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)

    def _build_result(
        self,
        plan: ArtifactExecutionPlan,
        report: Any,  # ExecutionReport from E3.3
        execution_started: str,
        start_time: float,
        workspace_resolution: WorkspaceResolution,
    ) -> ProjectExecutionResult:
        """Build ProjectExecutionResult from orchestrator report."""
        execution_completed = datetime.now(timezone.utc).isoformat()
        total_duration = (time.time() - start_time) * 1000

        # Extract file results from artifact statuses
        file_results = []
        files_written = 0

        for artifact_status in report.artifact_results:
            if artifact_status.file_written and artifact_status.written_path:
                files_written += 1
                file_results.append(ArtifactFileResult(
                    artifact_execution_id=artifact_status.artifact_execution_id,
                    target_path=artifact_status.target_path,
                    absolute_path=artifact_status.written_path,
                    file_written=True,
                    content_hash=artifact_status.content_hash,
                    file_size_bytes=self._get_file_size(artifact_status.written_path),
                ))

        result = ProjectExecutionResult(
            execution_id=f"exec-{plan.plan_id[:8]}",
            mission_id=plan.mission_id,
            plan_id=plan.plan_id,
            workspace_id=workspace_resolution.workspace_id,
            execution_status="SUCCESS" if report.is_success else "PARTIAL" if report.is_partial_success else "FAILED",
            is_success=report.is_success,
            is_partial_success=report.is_partial_success,
            total_artifacts=report.total_artifacts,
            artifacts_completed=report.successful_artifacts,
            artifacts_failed=report.failed_artifacts,
            artifacts_blocked=report.blocked_artifacts,
            files_written=files_written,
            file_results=file_results,
            total_waves=report.total_waves,
            waves_executed=report.waves_executed,
            execution_started=execution_started,
            execution_completed=execution_completed,
            total_duration_ms=total_duration,
            errors=list(report.errors),
            failure_evidence=[
                f"Failed: {df.failed_artifact_execution_id} - {df.reason}"
                for df in report.dependency_failures
            ],
            workspace_root=str(self._workspace_root),
            repository_scope=workspace_resolution.repository_scope,
        )

        # Compute deterministic hash
        result.deterministic_hash = compute_execution_result_hash(
            result.execution_id,
            result.mission_id,
            result.plan_id,
            result.files_written,
        )

        return result

    def _get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(path)
        except OSError:
            return 0


# ---------------------------------------------------------------------------
# E3.4.6 - Main Integration Entry Point
# ---------------------------------------------------------------------------

class ProjectGenerator:
    """Main entry point for E3.4 project generation.

    This is the public API for the complete mission → files pipeline.
    """

    def __init__(
        self,
        workspace_root: str,
        generation_engine: "RealCodeGenerationEngine",
        invocation_engine: Optional[Any] = None,
    ):
        """Initialize the project generator.

        Args:
            workspace_root: Absolute path to workspace root
            generation_engine: RealCodeGenerationEngine instance
            invocation_engine: Optional InvocationEngine for LLM generation
        """
        self._workspace_root = Path(workspace_root).resolve()
        self._generation_engine = generation_engine
        self._invocation_engine = invocation_engine

        # Lazy imports to avoid circular dependencies
        from runtime.contracts.orchestrator import ArtifactExecutionOrchestrator
        from runtime.contracts.planner import ArtifactExecutionPlanner

        self._planner = ArtifactExecutionPlanner()
        self._orchestrator = ArtifactExecutionOrchestrator(
            repository_root=str(self._workspace_root),
            generation_engine=generation_engine,
            invocation_engine=invocation_engine,
        )

        # Adapters
        self._requirements_adapter = MissionRequirementsAdapter()
        self._plan_converter = MissionToPlanConverter(self._planner)

        # Execution engine
        self._execution_engine = ProjectExecutionEngine(
            workspace_root=str(self._workspace_root),
            generation_engine=generation_engine,
            orchestrator=self._orchestrator,
        )

    def generate(
        self,
        mission: str,
        mission_id: Optional[str] = None,
        workspace_root: Optional[str] = None,
    ) -> ProjectExecutionResult:
        """Generate a complete project from a mission.

        Args:
            mission: Natural language mission string
            mission_id: Optional mission ID (generated if not provided)
            workspace_root: Optional workspace root override

        Returns:
            ProjectExecutionResult with complete execution results
        """
        # Determine workspace root
        ws_root = Path(workspace_root) if workspace_root else self._workspace_root

        # Step 1: Adapt mission to requirements
        requirements = self._requirements_adapter.adapt_from_string(
            mission=mission,
            mission_id=mission_id,
            workspace_root=str(ws_root),
        )

        # Step 2: Convert requirements to plan
        plan = self._plan_converter.convert(
            requirements=requirements,
            workspace_root=str(ws_root),
        )

        # Step 3: Execute the plan
        result = self._execution_engine.execute(plan)

        return result
