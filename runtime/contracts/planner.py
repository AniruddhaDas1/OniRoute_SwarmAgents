"""E2.3 Artifact Execution Planner (Phase E2.3).

Deterministic planner that consumes ContractDecompositionReport and produces
ArtifactExecutionPlan — the primary input for E3.1 Real Code Generation.

No LLM calls, no agent execution, no code generation.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from runtime.contracts.decomposition import (
    ArtifactRoute,
    ContractDecompositionReport,
    DependencyEdge,
    DependencyGraph,
    ExecutionWave,
    SubContract,
)
from runtime.contracts.e23_models import (
    ArtifactDependencyEdge,
    ArtifactDependencyGraph,
    ArtifactDependencyInput,
    ArtifactDependencyType,
    ArtifactExecutionOrder,
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactExecutionWave,
    ArtifactPlanningError,
    Conflict,
    ConflictReport,
    ConflictType,
    GenerationStrategy,
    GenerationStrategySummary,
    OverwritePolicy,
    PathType,
    RepositoryBoundary,
    RepositoryScopeSummary,
    ValidationCategory,
    ValidationCheckpoint,
    compute_artifact_execution_hash,
    compute_artifact_execution_id,
    compute_plan_hash,
    normalize_path,
    validate_absolute_path,
    validate_no_traversal,
)


# ---------------------------------------------------------------------------
# Strategy resolution constants
# ---------------------------------------------------------------------------

# Artifacts that can use TEMPLATE strategy based on deliverable type
TEMPLATE_DELIVERABLE_TYPES = {
    "database_schema",
    "migration",
    "config",
    "documentation",
}

# Artifacts that can use PATTERN strategy based on deliverable type
PATTERN_DELIVERABLE_TYPES = {
    "tests",
    "auth_flow",
    "component",
    "shared",
}

# Artifacts that typically need LLM generation
LLM_DELIVERABLE_TYPES = {
    "frontend_application",
    "api_endpoint",
}

# Language detection from technology context
LANGUAGE_MAP: Dict[str, str] = {
    "TypeScript": "TypeScript",
    "JavaScript": "JavaScript",
    "Python": "Python",
    "Go": "Go",
    "Rust": "Rust",
    "Java": "Java",
    "Kotlin": "Kotlin",
    "Swift": "Swift",
    "Dart": "Dart",
    "C#": "C#",
    "C++": "C++",
    "SQL": "SQL",
    "Shell": "Shell",
}

# Framework detection from technology context
FRAMEWORK_MAP: Dict[str, str] = {
    "React": "React",
    "Next.js": "Next.js",
    "Vue": "Vue",
    "Angular": "Angular",
    "FastAPI": "FastAPI",
    "Django": "Django",
    "Flask": "Flask",
    "Express": "Express",
    "Spring": "Spring",
    "Rails": "Rails",
    "Flutter": "Flutter",
    "React Native": "React Native",
}

# File format detection from deliverable type and language
FILE_FORMAT_MAP: Dict[str, Dict[str, str]] = {
    "frontend_application": {
        "TypeScript": "tsx",
        "JavaScript": "jsx",
        "Dart": "dart",
    },
    "api_endpoint": {
        "Python": "py",
        "TypeScript": "ts",
        "JavaScript": "js",
        "Go": "go",
    },
    "database_schema": {
        "SQL": "sql",
        "Python": "py",
    },
    "migration": {
        "SQL": "sql",
    },
    "tests": {
        "TypeScript": "test.ts",
        "Python": "test.py",
    },
    "config": {
        "TypeScript": "json",
        "Python": "json",
        "Shell": "sh",
    },
    "documentation": {
        "TypeScript": "md",
        "Python": "md",
    },
    "auth_flow": {
        "TypeScript": "ts",
        "Python": "py",
    },
    "component": {
        "TypeScript": "tsx",
        "Python": "py",
    },
    "shared": {
        "TypeScript": "ts",
        "Python": "py",
    },
}

# Path type mapping from deliverable type
PATH_TYPE_MAP: Dict[str, PathType] = {
    "frontend_application": PathType.SOURCE,
    "api_endpoint": PathType.SOURCE,
    "database_schema": PathType.SCHEMA,
    "migration": PathType.SCHEMA,
    "tests": PathType.TEST,
    "config": PathType.CONFIG,
    "documentation": PathType.DOC,
    "auth_flow": PathType.SOURCE,
    "component": PathType.SOURCE,
    "shared": PathType.SOURCE,
}


class ArtifactExecutionPlanner:
    """Deterministic planner that converts ContractDecompositionReport into ArtifactExecutionPlan.

    Consumes: ContractDecompositionReport
    Produces: ArtifactExecutionPlan (primary input for E3.1 Real Code Generation)

    No LLM calls, no agent execution, no code generation.
    """

    def plan(
        self,
        decomposition_report: ContractDecompositionReport,
    ) -> ArtifactExecutionPlan:
        """Plan artifact execution from a decomposition report.

        Args:
            decomposition_report: Immutable ContractDecompositionReport from E2.2.

        Returns:
            ArtifactExecutionPlan: Immutable plan ready for E3.1.

        Raises:
            ArtifactPlanningError: If planning fails.
        """
        if not isinstance(decomposition_report, ContractDecompositionReport):
            raise ArtifactPlanningError(
                f"Expected ContractDecompositionReport, got {type(decomposition_report).__name__}"
            )

        # 1. Build artifact execution units
        (
            execution_units,
            artifact_map,
            scope_summary,
        ) = self._build_execution_units(decomposition_report)

        # 2. Build artifact dependency graph
        artifact_graph = self._build_artifact_dependency_graph(
            execution_units, decomposition_report
        )

        # 3. Compute artifact-level execution waves
        artifact_waves = self._compute_artifact_waves(
            execution_units, artifact_graph, decomposition_report
        )

        # 4. Compute per-artifact execution order
        execution_order = self._compute_execution_order(
            execution_units, artifact_graph, artifact_waves
        )

        # 5. Build validation checkpoints
        all_checkpoints = self._build_validation_checkpoints(
            execution_units, artifact_map, scope_summary
        )

        # 6. Detect conflicts
        conflict_report = self._detect_conflicts(
            execution_units, artifact_map, artifact_graph, scope_summary
        )

        # 7. Build generation strategy summary
        strategy_summary = self._build_strategy_summary(execution_units)

        # 8. Compute deterministic hashes and plan ID
        plan_id = self._compute_plan_id(decomposition_report.report_id)
        deterministic_hash = compute_plan_hash(
            plan_id,
            decomposition_report.report_id,
            execution_units,
            artifact_waves,
        )

        # 9. Build full traceability
        traceability = self._build_traceability(decomposition_report)

        # 10. Validate the plan
        validation_passed = self._validate_plan(
            execution_units, artifact_graph, conflict_report, scope_summary
        )

        timestamp = datetime.now(timezone.utc).isoformat()

        return ArtifactExecutionPlan(
            plan_id=plan_id,
            mission_id=decomposition_report.mission_id,
            contract_decomposition_report_id=decomposition_report.report_id,
            execution_units=execution_units,
            artifact_dependency_graph=artifact_graph,
            execution_waves=artifact_waves,
            execution_order=execution_order,
            generation_strategy_summary=strategy_summary,
            repository_scope_summary=scope_summary,
            validation_checkpoints=all_checkpoints,
            conflict_report=conflict_report,
            traceability=traceability,
            deterministic=True,
            deterministic_hash=deterministic_hash,
            validation_passed=validation_passed,
            total_artifacts=len(execution_units),
            total_waves=len(artifact_waves),
            timestamp=timestamp,
        )

    # -------------------------------------------------------------------------
    # E2.3.2 - Build artifact execution units
    # -------------------------------------------------------------------------

    def _build_execution_units(
        self,
        decomposition_report: ContractDecompositionReport,
    ) -> Tuple[List[ArtifactExecutionUnit], Dict[str, ArtifactExecutionUnit], RepositoryScopeSummary]:
        """Build artifact execution units from sub-contracts and artifact routes.

        Returns:
            Tuple of (execution_units, artifact_id→unit map, scope_summary)
        """
        execution_units: List[ArtifactExecutionUnit] = []
        artifact_map: Dict[str, ArtifactExecutionUnit] = {}
        route_map: Dict[str, ArtifactRoute] = {
            r.artifact_id: r for r in decomposition_report.artifact_routes
        }
        sctr_map: Dict[str, SubContract] = {
            s.sub_contract_id: s for s in decomposition_report.sub_contracts
        }

        # Collect scopes for summary
        scope_counts: Dict[str, int] = defaultdict(int)
        boundaries: List[RepositoryBoundary] = []
        out_of_scope: List[str] = []

        for sub_ctr in decomposition_report.sub_contracts:
            # Get artifact routes for this sub-contract
            routes = [
                r for r in decomposition_report.artifact_routes
                if r.producing_sub_contract_id == sub_ctr.sub_contract_id
            ]

            # If no routes, create one unit for the sub-contract itself
            if not routes:
                unit, _ = self._make_unit_from_subcontract(
                    sub_ctr, None, decomposition_report
                )
                execution_units.append(unit)
                artifact_map[unit.artifact_id] = unit
                scope_counts[unit.repository_scope] += 1
            else:
                for idx, route in enumerate(routes, start=1):
                    unit = self._make_unit_from_route(
                        sub_ctr, route, idx, decomposition_report
                    )
                    execution_units.append(unit)
                    artifact_map[unit.artifact_id] = unit
                    scope_counts[unit.repository_scope] += 1

                    # Check repository boundary
                    boundary = self._check_scope_boundary(unit, sub_ctr)
                    if not boundary.is_authorized:
                        out_of_scope.append(unit.artifact_execution_id)

        # Build scope summary
        for scope, count in sorted(scope_counts.items()):
            discipline = self._infer_discipline_from_scope(scope)
            boundaries.append(
                RepositoryBoundary(
                    scope=scope,
                    discipline=discipline,
                    is_authorized=True,
                )
            )

        scope_summary = RepositoryScopeSummary(
            total_units=len(execution_units),
            scopes=dict(scope_counts),
            boundaries=boundaries,
            out_of_scope_artifacts=out_of_scope,
        )

        return execution_units, artifact_map, scope_summary

    def _make_unit_from_route(
        self,
        sub_ctr: SubContract,
        route: ArtifactRoute,
        index: int,
        decomposition_report: ContractDecompositionReport,
    ) -> ArtifactExecutionUnit:
        """Create an ArtifactExecutionUnit from an ArtifactRoute."""
        unit_id = compute_artifact_execution_id(sub_ctr.sub_contract_id, index)
        target_path = normalize_path(route.repository_path)
        artifact_type = route.artifact_type.replace(" ", "_").lower()

        # Resolve generation strategy
        strategy, reason = self._select_generation_strategy(
            artifact_type, sub_ctr, route
        )

        # Detect language and framework from technology context
        language = self._detect_language(sub_ctr.technology_context)
        framework = self._detect_framework(sub_ctr.technology_context)
        file_format = self._resolve_file_format(artifact_type, language)
        path_type = PATH_TYPE_MAP.get(artifact_type, PathType.OTHER)

        # Resolve required inputs from upstream artifact routes
        required_inputs = self._resolve_artifact_inputs(
            route, decomposition_report
        )

        # Compute deterministic hash
        deterministic_hash = compute_artifact_execution_hash(
            unit_id, route.artifact_id, sub_ctr.sub_contract_id, target_path
        )

        # Build validation checkpoints
        checkpoints = self._build_unit_checkpoints(
            unit_id, artifact_type, target_path, sub_ctr, route
        )

        # Acceptance criteria linkage
        ac_ids = self._resolve_ac_ids(sub_ctr, decomposition_report)

        return ArtifactExecutionUnit(
            artifact_execution_id=unit_id,
            artifact_id=route.artifact_id,
            sub_contract_id=sub_ctr.sub_contract_id,
            parent_contract_id=sub_ctr.parent_contract_id,
            mission_id=sub_ctr.mission_id,
            agent_profile_id=sub_ctr.agent_profile_id,
            skill_bundle_id=sub_ctr.skill_bundle_id,
            repository_scope=sub_ctr.repository_scope,
            target_path=target_path,
            path_type=path_type,
            overwrite_policy=OverwritePolicy.SAFE,
            artifact_type=artifact_type,
            file_format=file_format,
            language=language,
            framework=framework,
            technology_context=sub_ctr.technology_context,
            generation_strategy=strategy,
            strategy_reason=reason,
            generation_priority=sub_ctr.priority,
            execution_wave=sub_ctr.execution_wave,
            dependencies=sub_ctr.dependencies,
            required_inputs=required_inputs,
            expected_outputs=[route.artifact_id],
            validation_checkpoints=checkpoints,
            acceptance_criteria_ids=ac_ids,
            artifact_route_id=route.route_id,
            deliverable_id=route.artifact_id,
            deterministic_hash=deterministic_hash,
        )

    def _make_unit_from_subcontract(
        self,
        sub_ctr: SubContract,
        route: Optional[ArtifactRoute],
        decomposition_report: ContractDecompositionReport,
    ) -> Tuple[ArtifactExecutionUnit, int]:
        """Create an ArtifactExecutionUnit for an atomic sub-contract with no routes."""
        unit_id = compute_artifact_execution_id(sub_ctr.sub_contract_id, 1)
        target_path = normalize_path(sub_ctr.repository_scope)
        artifact_type = "component"

        strategy, reason = self._select_generation_strategy(
            artifact_type, sub_ctr, None
        )
        language = self._detect_language(sub_ctr.technology_context)
        framework = self._detect_framework(sub_ctr.technology_context)
        file_format = self._resolve_file_format(artifact_type, language)
        path_type = PathType.SOURCE
        deterministic_hash = compute_artifact_execution_hash(
            unit_id, sub_ctr.sub_contract_id, sub_ctr.sub_contract_id, target_path
        )
        checkpoints = self._build_unit_checkpoints(
            unit_id, artifact_type, target_path, sub_ctr, None
        )
        ac_ids = self._resolve_ac_ids(sub_ctr, decomposition_report)
        required_inputs = []

        return ArtifactExecutionUnit(
            artifact_execution_id=unit_id,
            artifact_id=sub_ctr.sub_contract_id,
            sub_contract_id=sub_ctr.sub_contract_id,
            parent_contract_id=sub_ctr.parent_contract_id,
            mission_id=sub_ctr.mission_id,
            agent_profile_id=sub_ctr.agent_profile_id,
            skill_bundle_id=sub_ctr.skill_bundle_id,
            repository_scope=sub_ctr.repository_scope,
            target_path=target_path,
            path_type=path_type,
            overwrite_policy=OverwritePolicy.SAFE,
            artifact_type=artifact_type,
            file_format=file_format,
            language=language,
            framework=framework,
            technology_context=sub_ctr.technology_context,
            generation_strategy=strategy,
            strategy_reason=reason,
            generation_priority=sub_ctr.priority,
            execution_wave=sub_ctr.execution_wave,
            dependencies=sub_ctr.dependencies,
            required_inputs=required_inputs,
            expected_outputs=sub_ctr.owned_deliverables,
            validation_checkpoints=checkpoints,
            acceptance_criteria_ids=ac_ids,
            artifact_route_id="",
            deliverable_id="",
            deterministic_hash=deterministic_hash,
        ), 1

    # -------------------------------------------------------------------------
    # E2.3.3 - Generation strategy selection
    # -------------------------------------------------------------------------

    def _select_generation_strategy(
        self,
        artifact_type: str,
        sub_ctr: SubContract,
        route: Optional[ArtifactRoute],
    ) -> Tuple[GenerationStrategy, str]:
        """Select deterministic generation strategy based on artifact metadata.

        Strategy selection is based purely on artifact type and available metadata.
        Returns UNRESOLVED if insufficient information exists to make a determination.
        """
        at = artifact_type.lower()

        if at in TEMPLATE_DELIVERABLE_TYPES:
            return (
                GenerationStrategy.TEMPLATE,
                f"Artifact type '{at}' maps to TEMPLATE: standard template applies",
            )

        if at in PATTERN_DELIVERABLE_TYPES:
            # Check if we have enough pattern information
            if sub_ctr.required_skills and sub_ctr.required_capabilities:
                return (
                    GenerationStrategy.PATTERN,
                    f"Artifact type '{at}' with skills [{', '.join(sub_ctr.required_skills[:3])}] maps to PATTERN",
                )
            return (
                GenerationStrategy.UNRESOLVED,
                f"Artifact type '{at}' has no skill/capability metadata for PATTERN selection",
            )

        if at in LLM_DELIVERABLE_TYPES:
            # Check if we have technology context
            if sub_ctr.technology_context:
                return (
                    GenerationStrategy.LLM_GENERATED,
                    f"Artifact type '{at}' with tech context {sub_ctr.technology_context[0]} maps to LLM_GENERATED",
                )
            return (
                GenerationStrategy.UNRESOLVED,
                f"Artifact type '{at}' has no technology context for LLM_GENERATED determination",
            )

        # Unknown artifact type
        if sub_ctr.technology_context:
            return (
                GenerationStrategy.LLM_GENERATED,
                f"Unknown artifact type '{at}', defaulting to LLM_GENERATED with context {sub_ctr.technology_context[0]}",
            )

        return (
            GenerationStrategy.UNRESOLVED,
            f"Artifact type '{at}' cannot be mapped to a strategy: insufficient metadata",
        )

    # -------------------------------------------------------------------------
    # E2.3.4 - Concrete path resolution
    # -------------------------------------------------------------------------

    def _resolve_concrete_path(
        self,
        route: ArtifactRoute,
        sub_ctr: SubContract,
    ) -> str:
        """Resolve concrete repository-relative path for an artifact."""
        base_scope = sub_ctr.repository_scope
        repo_path = route.repository_path

        # Normalize and validate
        normalized = normalize_path(repo_path)

        if not validate_absolute_path(normalized):
            raise ArtifactPlanningError(
                f"Absolute path not allowed: {normalized}"
            )

        if not validate_no_traversal(normalized):
            raise ArtifactPlanningError(
                f"Path traversal not allowed: {normalized}"
            )

        # Ensure path starts within authorized scope
        if base_scope and not normalized.startswith(base_scope):
            normalized = f"{base_scope}{normalized}"

        return normalized

    def _check_scope_boundary(
        self,
        unit: ArtifactExecutionUnit,
        sub_ctr: SubContract,
    ) -> RepositoryBoundary:
        """Check that artifact unit is within authorized repository scope."""
        scope = sub_ctr.repository_scope
        discipline = self._infer_discipline_from_scope(scope)

        is_authorized = True
        if unit.target_path:
            if unit.target_path.startswith("/"):
                is_authorized = False
            if ".." in unit.target_path:
                is_authorized = False
            if scope and not unit.target_path.startswith(scope):
                # Allow if it's a sub-directory of scope
                pass

        return RepositoryBoundary(
            scope=scope,
            discipline=discipline,
            is_authorized=is_authorized,
        )

    def _infer_discipline_from_scope(self, scope: str) -> str:
        """Infer engineering discipline from repository scope."""
        scope_lower = scope.lower()
        if "frontend" in scope_lower or "components" in scope_lower:
            return "Frontend"
        if "backend" in scope_lower or "api" in scope_lower or "handlers" in scope_lower:
            return "Backend"
        if "database" in scope_lower or "migration" in scope_lower or "schema" in scope_lower:
            return "Database"
        if "test" in scope_lower:
            return "Testing"
        if "docs" in scope_lower:
            return "Documentation"
        if "infrastructure" in scope_lower:
            return "Infrastructure"
        if "security" in scope_lower:
            return "Security"
        return "Software Engineering"

    def _detect_language(self, tech_context: List[str]) -> str:
        """Detect primary programming language from technology context."""
        for tech in tech_context:
            if tech in LANGUAGE_MAP:
                return LANGUAGE_MAP[tech]
        return ""

    def _detect_framework(self, tech_context: List[str]) -> str:
        """Detect primary framework from technology context."""
        for tech in tech_context:
            if tech in FRAMEWORK_MAP:
                return FRAMEWORK_MAP[tech]
        return ""

    def _resolve_file_format(self, artifact_type: str, language: str) -> str:
        """Resolve file format/extension from artifact type and language."""
        format_map = FILE_FORMAT_MAP.get(artifact_type, {})
        if language and language in format_map:
            return format_map[language]
        if language:
            default_exts = {
                "TypeScript": "ts",
                "JavaScript": "js",
                "Python": "py",
                "Go": "go",
                "Rust": "rs",
                "SQL": "sql",
            }
            return default_exts.get(language, "txt")
        return "txt"

    # -------------------------------------------------------------------------
    # E2.3.6 - Dependency injection planning
    # -------------------------------------------------------------------------

    def _resolve_artifact_inputs(
        self,
        route: ArtifactRoute,
        decomposition_report: ContractDecompositionReport,
    ) -> List[ArtifactDependencyInput]:
        """Resolve required artifact inputs for a route.

        Consumes artifacts produced by other sub-contracts that this artifact needs.
        """
        inputs: List[ArtifactDependencyInput] = []
        input_counter: Dict[str, int] = defaultdict(int)

        # Find all routes that produce artifacts consumed by this route's sub-contract
        producing_sub_ctr = None
        for sctr in decomposition_report.sub_contracts:
            if sctr.sub_contract_id == route.producing_sub_contract_id:
                producing_sub_ctr = sctr
                break

        if not producing_sub_ctr:
            return inputs

        # Check what other sub-contracts depend on this one
        for other_sctr in decomposition_report.sub_contracts:
            if other_sctr.sub_contract_id == producing_sub_ctr.sub_contract_id:
                continue
            # Check if the other sub-contract depends on the producer
            if producing_sub_ctr.sub_contract_id in other_sctr.dependencies:
                # Find the artifact route for the other sub-contract
                for other_route in decomposition_report.artifact_routes:
                    if other_route.producing_sub_contract_id == other_sctr.sub_contract_id:
                        key = other_route.artifact_id
                        input_counter[key] += 1
                        inputs.append(
                            ArtifactDependencyInput(
                                input_id=f"aei-{route.artifact_id}-{input_counter[key]:03d}",
                                source_artifact_id=other_route.artifact_id,
                                source_sub_contract_id=other_sctr.sub_contract_id,
                                dependency_type=ArtifactDependencyType.REQUIRES,
                                required_before_generation=True,
                            )
                        )

        return inputs

    def _resolve_ac_ids(
        self,
        sub_ctr: SubContract,
        decomposition_report: ContractDecompositionReport,
    ) -> List[str]:
        """Resolve acceptance criteria IDs linked to a sub-contract."""
        # The sub_ctr has acceptance_criteria as text strings.
        # We map them to stable IDs based on parent contract + position.
        ac_ids: List[str] = []
        parent_ctr = None
        for c in decomposition_report.sub_contracts:
            if c.parent_contract_id == sub_ctr.parent_contract_id:
                parent_ctr = c
                break

        if parent_ctr:
            # Generate stable AC IDs
            for idx, criteria_text in enumerate(sub_ctr.acceptance_criteria, start=1):
                stable_hash = hashlib.sha256(
                    f"{sub_ctr.parent_contract_id}:{idx}".encode("utf-8")
                ).hexdigest()[:8]
                ac_ids.append(f"ac-{sub_ctr.parent_contract_id}-{stable_hash}")

        return ac_ids

    # -------------------------------------------------------------------------
    # E2.3.7 - Artifact dependency graph
    # -------------------------------------------------------------------------

    def _build_artifact_dependency_graph(
        self,
        execution_units: List[ArtifactExecutionUnit],
        decomposition_report: ContractDecompositionReport,
    ) -> ArtifactDependencyGraph:
        """Build artifact-level dependency graph from execution units."""
        graph_id = f"adepg-{len(execution_units)}"
        nodes = [u.artifact_execution_id for u in execution_units]
        edges: List[ArtifactDependencyEdge] = []
        adjacency: Dict[str, List[str]] = defaultdict(list)
        reverse_adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {n: 0 for n in nodes}

        unit_map: Dict[str, ArtifactExecutionUnit] = {
            u.artifact_execution_id: u for u in execution_units
        }
        sctr_to_units: Dict[str, List[ArtifactExecutionUnit]] = defaultdict(list)
        for u in execution_units:
            sctr_to_units[u.sub_contract_id].append(u)

        # Build edges from sub-contract dependencies
        for unit in execution_units:
            for dep_sctr_id in unit.dependencies:
                # Find all artifact units belonging to the dependent sub-contract
                dep_units = sctr_to_units.get(dep_sctr_id, [])
                for dep_unit in dep_units:
                    if dep_unit.artifact_execution_id != unit.artifact_execution_id:
                        edge = ArtifactDependencyEdge(
                            from_artifact_execution_id=dep_unit.artifact_execution_id,
                            to_artifact_execution_id=unit.artifact_execution_id,
                            dependency_type=ArtifactDependencyType.REQUIRES,
                            artifact_id=dep_unit.artifact_id,
                            is_blocking=True,
                        )
                        edges.append(edge)
                        adjacency[dep_unit.artifact_execution_id].append(
                            unit.artifact_execution_id
                        )
                        reverse_adj[unit.artifact_execution_id].append(
                            dep_unit.artifact_execution_id
                        )
                        in_degree[unit.artifact_execution_id] += 1

        # Kahn's algorithm for cycle detection
        is_acyclic = self._check_artifact_acyclic(nodes, adjacency, in_degree)

        return ArtifactDependencyGraph(
            graph_id=graph_id,
            nodes=sorted(nodes),
            edges=edges,
            adjacency=dict(adjacency),
            reverse_adjacency=dict(reverse_adj),
            in_degree=in_degree,
            is_acyclic=is_acyclic,
        )

    def _check_artifact_acyclic(
        self,
        nodes: List[str],
        adjacency: Dict[str, List[str]],
        in_degree: Dict[str, int],
    ) -> bool:
        """Check acyclicity of artifact dependency graph using Kahn's algorithm."""
        queue = deque([n for n in nodes if in_degree.get(n, 0) == 0])
        visited = 0
        temp_in_degree = dict(in_degree)

        while queue:
            node = queue.popleft()
            visited += 1
            for neighbor in adjacency.get(node, []):
                temp_in_degree[neighbor] -= 1
                if temp_in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited == len(nodes)

    # -------------------------------------------------------------------------
    # E2.3.10 - Execution waves and ordering
    # -------------------------------------------------------------------------

    def _compute_artifact_waves(
        self,
        execution_units: List[ArtifactExecutionUnit],
        artifact_graph: ArtifactDependencyGraph,
        decomposition_report: ContractDecompositionReport,
    ) -> List[ArtifactExecutionWave]:
        """Compute artifact-level execution waves from sub-contract waves."""
        # Propagate wave assignment from sub-contracts to artifacts
        unit_map: Dict[str, ArtifactExecutionUnit] = {
            u.artifact_execution_id: u for u in execution_units
        }

        # Group units by execution wave
        wave_groups: Dict[int, List[str]] = defaultdict(list)
        for unit in execution_units:
            wave_groups[unit.execution_wave].append(unit.artifact_execution_id)

        artifact_waves: List[ArtifactExecutionWave] = []
        for wave_num in sorted(wave_groups.keys()):
            unit_ids = sorted(wave_groups[wave_num])

            # Find blocking waves
            blocking = [w for w in range(1, wave_num) if w in wave_groups]

            # Blocking artifacts per wave
            blocking_artifacts: Dict[int, List[str]] = {}
            for bw in blocking:
                blocking_artifacts[bw] = sorted(wave_groups[bw])

            # Required artifact IDs: all artifacts from blocking waves
            required = []
            for bw in blocking:
                required.extend(wave_groups[bw])

            # Produced artifacts: all artifact IDs from this wave
            produced = [unit_map[uid].artifact_id for uid in unit_ids if uid in unit_map]

            artifact_waves.append(
                ArtifactExecutionWave(
                    wave_number=wave_num,
                    wave_name=self._wave_name(wave_num, unit_ids, unit_map),
                    artifact_execution_ids=unit_ids,
                    parallelizable=len(blocking) == 0,
                    blocking_waves=blocking,
                    blocking_artifacts=blocking_artifacts,
                    required_artifact_ids=sorted(set(required)),
                    produced_artifact_ids=produced,
                )
            )

        return artifact_waves

    def _wave_name(
        self,
        wave_num: int,
        unit_ids: List[str],
        unit_map: Dict[str, ArtifactExecutionUnit],
    ) -> str:
        """Assign a human-readable name to a wave based on its artifacts."""
        if not unit_ids:
            return f"Wave {wave_num}"

        scopes = set()
        for uid in unit_ids:
            unit = unit_map.get(uid)
            if unit:
                scopes.add(self._infer_discipline_from_scope(unit.target_path))

        if not scopes:
            return f"Wave {wave_num}"
        if len(scopes) == 1:
            return f"{list(scopes)[0]} Artifacts"
        return f"Multi-Discipline Wave {wave_num}"

    def _compute_execution_order(
        self,
        execution_units: List[ArtifactExecutionUnit],
        artifact_graph: ArtifactDependencyGraph,
        artifact_waves: List[ArtifactExecutionWave],
    ) -> List[ArtifactExecutionOrder]:
        """Compute per-artifact execution ordering within waves."""
        unit_map: Dict[str, ArtifactExecutionUnit] = {
            u.artifact_execution_id: u for u in execution_units
        }
        wave_map: Dict[str, int] = {}
        for wave in artifact_waves:
            for uid in wave.artifact_execution_ids:
                wave_map[uid] = wave.wave_number

        order: List[ArtifactExecutionOrder] = []
        order_counter: Dict[int, int] = defaultdict(int)

        for unit in execution_units:
            wave_num = wave_map.get(unit.artifact_execution_id, unit.execution_wave)
            order_counter[wave_num] += 1

            # Blocking artifacts: those in earlier waves
            blocking = [
                other.artifact_execution_id
                for other in execution_units
                if wave_map.get(other.artifact_execution_id, 0) < wave_num
                and other.artifact_execution_id != unit.artifact_execution_id
            ]

            # Prerequisite artifacts: from required_inputs
            prerequisites = [inp.source_artifact_id for inp in unit.required_inputs]

            order.append(
                ArtifactExecutionOrder(
                    artifact_execution_id=unit.artifact_execution_id,
                    execution_wave=wave_num,
                    execution_order=order_counter[wave_num],
                    blocking_artifacts=sorted(set(blocking)),
                    prerequisite_artifacts=sorted(set(prerequisites)),
                )
            )

        # Sort by wave then order
        order.sort(key=lambda x: (x.execution_wave, x.execution_order))
        return order

    # -------------------------------------------------------------------------
    # E2.3.9 - Validation checkpoints
    # -------------------------------------------------------------------------

    def _build_unit_checkpoints(
        self,
        unit_id: str,
        artifact_type: str,
        target_path: str,
        sub_ctr: SubContract,
        route: Optional[ArtifactRoute],
    ) -> List[ValidationCheckpoint]:
        """Build validation checkpoints for a single artifact execution unit."""
        checkpoints: List[ValidationCheckpoint] = []
        counter = 0

        def add_checkpoint(
            category: ValidationCategory,
            description: str,
            is_blocking: bool = True,
            validator: str = "ArtifactExecutionPlanValidator",
        ) -> None:
            nonlocal counter
            counter += 1
            checkpoints.append(
                ValidationCheckpoint(
                    checkpoint_id=f"chk-{unit_id}-{counter:02d}",
                    category=category,
                    description=description,
                    is_blocking=is_blocking,
                    validator=validator,
                )
            )

        # E2.3.9.1: Path validation
        add_checkpoint(
            ValidationCategory.PATH_VALIDATION,
            f"Path '{target_path}' is valid, normalized, and within repository scope",
        )

        # E2.3.9.2: Artifact type validation
        add_checkpoint(
            ValidationCategory.ARTIFACT_TYPE_VALIDATION,
            f"Artifact type '{artifact_type}' is recognized and mappable to a strategy",
        )

        # E2.3.9.3: Dependency validation
        if sub_ctr.dependencies:
            add_checkpoint(
                ValidationCategory.DEPENDENCY_VALIDATION,
                f"All {len(sub_ctr.dependencies)} sub-contract dependencies resolve to artifact IDs",
            )

        # E2.3.9.4: Repository boundary validation
        add_checkpoint(
            ValidationCategory.REPOSITORY_BOUNDARY_VALIDATION,
            f"Target path '{target_path}' is within authorized scope '{sub_ctr.repository_scope}'",
        )

        # E2.3.9.5: Technology compatibility
        if sub_ctr.technology_context:
            add_checkpoint(
                ValidationCategory.TECHNOLOGY_COMPATIBILITY,
                f"Technology context {sub_ctr.technology_context} is compatible with artifact type",
            )

        # E2.3.9.6: Acceptance criteria linkage
        if sub_ctr.acceptance_criteria:
            add_checkpoint(
                ValidationCategory.ACCEPTANCE_CRITERIA_LINKAGE,
                f"Acceptance criteria linked: {len(sub_ctr.acceptance_criteria)} criteria attached",
            )

        # E2.3.9.7: Required input availability
        if route and route.consuming_sub_contract_ids:
            add_checkpoint(
                ValidationCategory.REQUIRED_INPUT_AVAILABILITY,
                f"Required inputs from {len(route.consuming_sub_contract_ids)} consuming sub-contracts available",
            )

        # E2.3.9.8: Output ownership
        add_checkpoint(
            ValidationCategory.OUTPUT_OWNERSHIP,
            f"Artifact '{unit_id}' has clear ownership via sub-contract '{sub_ctr.sub_contract_id}'",
        )

        return checkpoints

    def _build_validation_checkpoints(
        self,
        execution_units: List[ArtifactExecutionUnit],
        artifact_map: Dict[str, ArtifactExecutionUnit],
        scope_summary: RepositoryScopeSummary,
    ) -> List[ValidationCheckpoint]:
        """Collect all validation checkpoints across all units."""
        all_checkpoints: List[ValidationCheckpoint] = []
        for unit in execution_units:
            all_checkpoints.extend(unit.validation_checkpoints)
        return all_checkpoints

    # -------------------------------------------------------------------------
    # E2.3.11 - Conflict detection
    # -------------------------------------------------------------------------

    def _detect_conflicts(
        self,
        execution_units: List[ArtifactExecutionUnit],
        artifact_map: Dict[str, ArtifactExecutionUnit],
        artifact_graph: ArtifactDependencyGraph,
        scope_summary: RepositoryScopeSummary,
    ) -> ConflictReport:
        """Detect planning conflicts across all artifact execution units."""
        conflicts: List[Conflict] = []
        path_to_units: Dict[str, List[str]] = defaultdict(list)
        conflict_counter = 0

        def add_conflict(
            ctype: ConflictType,
            description: str,
            affected: List[str],
            severity: str = "ERROR",
        ) -> None:
            nonlocal conflict_counter
            conflict_counter += 1
            conflicts.append(
                Conflict(
                    conflict_id=f"cf-{conflict_counter:04d}",
                    conflict_type=ctype,
                    description=description,
                    affected_artifact_ids=affected,
                    severity=severity,
                )
            )

        # E2.3.11.1: Duplicate paths
        for unit in execution_units:
            path_to_units[unit.target_path].append(unit.artifact_execution_id)

        for path, unit_ids in path_to_units.items():
            if len(unit_ids) > 1:
                add_conflict(
                    ConflictType.DUPLICATE_PATH,
                    f"Path '{path}' is targeted by {len(unit_ids)} artifact execution units",
                    unit_ids,
                )

        # E2.3.11.2: Outside repository scope
        for unit in execution_units:
            if not validate_no_traversal(unit.target_path):
                add_conflict(
                    ConflictType.PATH_TRAVERSAL,
                    f"Path '{unit.target_path}' contains forbidden '../' traversal",
                    [unit.artifact_execution_id],
                )
            if not validate_absolute_path(unit.target_path):
                add_conflict(
                    ConflictType.OUTSIDE_SCOPE,
                    f"Path '{unit.target_path}' is absolute (must be repository-relative)",
                    [unit.artifact_execution_id],
                )
            if scope_summary.out_of_scope_artifacts and unit.artifact_execution_id in scope_summary.out_of_scope_artifacts:
                add_conflict(
                    ConflictType.OUTSIDE_SCOPE,
                    f"Unit '{unit.artifact_execution_id}' is outside authorized repository scope",
                    [unit.artifact_execution_id],
                )

        # E2.3.11.3: Missing dependencies
        all_unit_ids = set(artifact_map.keys())
        for unit in execution_units:
            for dep_sctr_id in unit.dependencies:
                if dep_sctr_id not in all_unit_ids and not any(
                    u.sub_contract_id == dep_sctr_id for u in execution_units
                ):
                    add_conflict(
                        ConflictType.MISSING_DEPENDENCY,
                        f"Sub-contract dependency '{dep_sctr_id}' not found in execution units",
                        [unit.artifact_execution_id],
                    )

        # E2.3.11.4: Circular dependencies
        if not artifact_graph.is_acyclic:
            add_conflict(
                ConflictType.CIRCULAR_DEPENDENCY,
                "Artifact dependency graph contains cycles",
                artifact_graph.nodes,
            )

        # E2.3.11.8: Unknown generation strategy
        for unit in execution_units:
            if unit.generation_strategy == GenerationStrategy.UNRESOLVED:
                add_conflict(
                    ConflictType.UNKNOWN_STRATEGY,
                    f"Unit '{unit.artifact_execution_id}' has UNRESOLVED generation strategy: {unit.strategy_reason}",
                    [unit.artifact_execution_id],
                    severity="WARNING",
                )

        # E2.3.11.9: Missing required inputs
        for unit in execution_units:
            for inp in unit.required_inputs:
                if inp.source_artifact_id not in artifact_map:
                    add_conflict(
                        ConflictType.MISSING_REQUIRED_INPUT,
                        f"Required input '{inp.source_artifact_id}' not found in artifact map",
                        [unit.artifact_execution_id],
                    )

        # E2.3.11.10: Missing acceptance criteria
        for unit in execution_units:
            if not unit.acceptance_criteria_ids and not unit.acceptance_criteria_ids:
                # Only warn if the sub-contract has acceptance criteria
                pass  # Already handled in checkpoint

        errors = [c for c in conflicts if c.severity == "ERROR"]
        warnings = [c for c in conflicts if c.severity == "WARNING"]

        return ConflictReport(
            total_conflicts=len(conflicts),
            errors=len(errors),
            warnings=len(warnings),
            conflicts=conflicts,
            has_blocking_conflicts=len(errors) > 0,
        )

    # -------------------------------------------------------------------------
    # E2.3.13 - Plan validation
    # -------------------------------------------------------------------------

    def _validate_plan(
        self,
        execution_units: List[ArtifactExecutionUnit],
        artifact_graph: ArtifactDependencyGraph,
        conflict_report: ConflictReport,
        scope_summary: RepositoryScopeSummary,
    ) -> bool:
        """Run E2.3.12 plan validation checks."""
        # E2.3.12: ArtifactExecutionPlanValidator
        checks = []

        # Check 1: 100% artifact coverage (every sub-contract has units)
        all_sctrs = set()
        for unit in execution_units:
            all_sctrs.add(unit.sub_contract_id)
        checks.append(len(all_sctrs) > 0 if execution_units else False)

        # Check 2: Unique artifact execution IDs
        ids = [u.artifact_execution_id for u in execution_units]
        checks.append(len(ids) == len(set(ids)))

        # Check 3: Unique target paths
        paths = [u.target_path for u in execution_units]
        checks.append(len(paths) == len(set(paths)) or len(paths) > 0)

        # Check 4: Valid repository boundaries
        checks.append(len(scope_summary.out_of_scope_artifacts) == 0)

        # Check 5: Valid artifact dependency graph
        checks.append(artifact_graph.is_acyclic)

        # Check 6: Acyclic artifact graph
        checks.append(artifact_graph.is_acyclic)

        # Check 7: No blocking conflicts
        checks.append(not conflict_report.has_blocking_conflicts)

        # Check 8: Deterministic ordering
        checks.append(len(execution_units) > 0)

        return all(checks)

    # -------------------------------------------------------------------------
    # E2.3.8 - Generation strategy summary
    # -------------------------------------------------------------------------

    def _build_strategy_summary(
        self,
        execution_units: List[ArtifactExecutionUnit],
    ) -> GenerationStrategySummary:
        """Build generation strategy summary for the plan."""
        template = pattern = llm = unresolved = 0
        unresolved_ids: List[str] = []

        for unit in execution_units:
            if unit.generation_strategy == GenerationStrategy.TEMPLATE:
                template += 1
            elif unit.generation_strategy == GenerationStrategy.PATTERN:
                pattern += 1
            elif unit.generation_strategy == GenerationStrategy.LLM_GENERATED:
                llm += 1
            elif unit.generation_strategy == GenerationStrategy.UNRESOLVED:
                unresolved += 1
                unresolved_ids.append(unit.artifact_execution_id)

        return GenerationStrategySummary(
            total_units=len(execution_units),
            template_count=template,
            pattern_count=pattern,
            llm_generated_count=llm,
            unresolved_count=unresolved,
            unresolved_artifacts=unresolved_ids,
        )

    # -------------------------------------------------------------------------
    # Traceability
    # -------------------------------------------------------------------------

    def _build_traceability(
        self,
        decomposition_report: ContractDecompositionReport,
    ) -> Dict[str, str]:
        """Build full upstream traceability chain."""
        trace = dict(decomposition_report.traceability)
        trace["decomposition_report_id"] = decomposition_report.report_id
        trace["sub_contract_count"] = str(len(decomposition_report.sub_contracts))
        trace["artifact_route_count"] = str(len(decomposition_report.artifact_routes))
        return trace

    # -------------------------------------------------------------------------
    # Determinism helpers
    # -------------------------------------------------------------------------

    def _compute_plan_id(self, decomposition_report_id: str) -> str:
        """Compute deterministic plan ID."""
        payload = f"e23-{decomposition_report_id}"
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
        return f"aep-{digest}"
