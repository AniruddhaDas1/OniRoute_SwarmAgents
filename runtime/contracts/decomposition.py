"""E2.2 Contract Decomposition Models.

Provides SubContract, DependencyGraph, ArtifactRoute, ExecutionWave,
and ContractDecompositionReport for Phase E2.2.

These models are self-contained and depend only on runtime.contracts.e21_models
(and indirectly on runtime.contracts.models) to avoid circular imports.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Set
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# E2.2 - Exception classes
# ---------------------------------------------------------------------------

class ContractDecompositionError(Exception):
    """Base exception for contract decomposition failures."""
    pass


class ValidationError(ContractDecompositionError):
    """Raised when decomposition validation checks fail."""
    pass


class DeterminismError(ContractDecompositionError):
    """Raised when decomposition is non-deterministic."""
    pass


class DuplicateIDError(ValidationError):
    """Raised when duplicate sub-contract or deliverable IDs are detected."""
    pass


class TechnologyMismatchError(ValidationError):
    """Raised when technology context doesn't match parent contract."""
    pass


class TraceabilityError(ValidationError):
    """Raised when traceability chain is incomplete."""
    pass


class WaveOrderingError(ValidationError):
    """Raised when execution wave ordering is invalid."""
    pass


# ---------------------------------------------------------------------------
# E2.2.1 - Audit result: pre-defined error messages
# ---------------------------------------------------------------------------

NO_ORPHAN_ERROR = "NO_ORPHAN_ERROR"
NO_CYCLE_ERROR = "NO_CYCLE_ERROR"
UNIQUE_DELIVERABLE_ERROR = "UNIQUE_DELIVERABLE_ERROR"
MISSING_OWNERSHIP_ERROR = "MISSING_OWNERSHIP_ERROR"
INVALID_DEPENDENCY_ERROR = "INVALID_DEPENDENCY_ERROR"
NO_CYCLIC_DEPENDENCY_ERROR = "NO_CYCLIC_DEPENDENCY_ERROR"


# ---------------------------------------------------------------------------
# E2.2.3 - Decomposition rules
# ---------------------------------------------------------------------------

CONTRACT_DECOMPOSITION_RULES: Dict[str, str] = {
    "rule_1": "Every parent contract must remain traceable",
    "rule_2": "Every sub-contract belongs to exactly one parent",
    "rule_3": "Every deliverable belongs to exactly one sub-contract",
    "rule_4": "Atomic contracts may remain as single sub-contract",
    "rule_5": "Large contracts may produce multiple sub-contracts",
    "rule_6": "Decomposition must be deterministic",
    "rule_7": "No orphan deliverables",
    "rule_8": "No duplicate deliverable ownership",
    "rule_9": "No orphan sub-contracts",
    "rule_10": "No duplicate sub-contract IDs",
}


# ---------------------------------------------------------------------------
# E2.2.8 - Repository scope per discipline
# ---------------------------------------------------------------------------

CONTRACT_REPOSITORY_SCOPE: Dict[str, str] = {
    "Frontend": "frontend/src/",
    "Backend": "backend/src/",
    "Database": "database/migrations/",
    "Infrastructure": "infrastructure/",
    "Security": "security/",
    "AI": "ai/",
    "Automation": "automation/",
    "Testing": "tests/",
    "Documentation": "docs/",
    "Analytics": "analytics/",
    "DevOps": "devops/",
    "Mobile": "mobile/",
    "Software Engineering": "src/",
    "QA": "tests/",
    "Shared": "shared/",
}


# ---------------------------------------------------------------------------
# E2.2.5 - Deliverable type per discipline
# ---------------------------------------------------------------------------

CONTRACT_DELIVERABLE_TYPE: Dict[str, str] = {
    "Frontend": "frontend_application",
    "Backend": "api_endpoint",
    "Database": "database_schema",
    "Infrastructure": "config",
    "Security": "auth_flow",
    "AI": "component",
    "Automation": "component",
    "Testing": "tests",
    "Documentation": "documentation",
    "Analytics": "component",
    "DevOps": "config",
    "Mobile": "frontend_application",
    "Software Engineering": "component",
    "QA": "tests",
    "Shared": "shared",
}


# ---------------------------------------------------------------------------
# E2.2.5 - Verification method per deliverable type
# ---------------------------------------------------------------------------

CONTRACT_VERIFICATION_METHOD: Dict[str, str] = {
    "frontend_application": "automated_test",
    "api_endpoint": "integration_test",
    "database_schema": "integration_test",
    "migration": "integration_test",
    "auth_flow": "automated_test",
    "tests": "unit_test",
    "documentation": "manual_review",
    "component": "automated_scan",
    "config": "lint_check",
    "shared": "automated_scan",
}


# ---------------------------------------------------------------------------
# E2.2.6 - Acceptance criteria templates (inherited from E2.1)
# ---------------------------------------------------------------------------

ACCEPTANCE_CRITERIA_TEMPLATES: Dict[str, Dict[str, str]] = {
    "FUNCTIONAL": {
        "given": "the {discipline} module is initialized with required inputs",
        "when": "the {objective} is executed",
        "then": "the expected deliverables are produced and pass validation",
    },
    "SECURITY": {
        "given": "all security policies and constraints are defined",
        "when": "the {discipline} implementation is reviewed",
        "then": "no security vulnerabilities or policy violations are detected",
    },
    "PERFORMANCE": {
        "given": "the performance benchmarks are established",
        "when": "the {discipline} workload is executed",
        "then": "all performance expectations are met within defined bounds",
    },
    "COMPLIANCE": {
        "given": "the coding standards and architectural rules are specified",
        "when": "the {discipline} output is audited",
        "then": "all standards and rules are satisfied",
    },
    "QUALITY": {
        "given": "the testing requirements are defined",
        "when": "the test suite is executed against the {discipline} output",
        "then": "all tests pass with 100% success rate",
    },
}


# ---------------------------------------------------------------------------
# E2.2.5 - Dependency types
# ---------------------------------------------------------------------------

class DependencyType(str, Enum):
    """Explicit dependency relationship categories."""

    REQUIRES = "REQUIRES"       # Needs artifact/output from another unit
    PRODUCES = "PRODUCES"       # Produces an artifact consumed by others
    CONSUMES = "CONSUMES"       # Directly consumes artifact from another unit
    BLOCKS = "BLOCKS"            # Prevents another unit from executing
    VALIDATES = "VALIDATES"     # Validates output of another unit


# ---------------------------------------------------------------------------
# E2.2.6 - Artifact routing
# ---------------------------------------------------------------------------

class ArtifactRoute(BaseModel):
    """Immutable artifact route defining artifact flow between sub-contracts."""

    model_config = ConfigDict(frozen=True)

    route_id: str = Field(
        description="Unique artifact route identifier (artr-{sctr_id}-{index})"
    )
    artifact_id: str = Field(
        description="Identifier of the artifact being routed"
    )
    producing_sub_contract_id: str = Field(
        description="SubContract that produces this artifact"
    )
    consuming_sub_contract_ids: List[str] = Field(
        default_factory=list,
        description="SubContracts that consume this artifact",
    )
    artifact_type: str = Field(
        description="Artifact type (schema, api, component, config, test, doc, etc.)"
    )
    repository_path: str = Field(
        description="Target repository path for this artifact"
    )
    technology_context: List[str] = Field(
        default_factory=list,
        description="Technology context relevant to this artifact",
    )
    is_optional: bool = Field(
        default=False,
        description="True if this artifact is optional (not blocking)",
    )


# ---------------------------------------------------------------------------
# E2.2.7 - Execution waves
# ---------------------------------------------------------------------------

class ExecutionWave(BaseModel):
    """Immutable execution wave grouping parallelizable sub-contracts."""

    model_config = ConfigDict(frozen=True)

    wave_number: int = Field(ge=1, le=20, description="Wave number (1-20)")
    wave_name: str = Field(
        description="Human-readable wave name (e.g., 'Foundation', 'Backend API')"
    )
    sub_contract_ids: List[str] = Field(
        default_factory=list,
        description="SubContract IDs assigned to this wave",
    )
    parallelizable: bool = Field(
        default=True,
        description="True if all sub-contracts in this wave can execute in parallel",
    )
    blocking_waves: List[int] = Field(
        default_factory=list,
        description="Wave numbers that must complete before this wave starts",
    )
    produced_artifacts: List[str] = Field(
        default_factory=list,
        description="Artifact IDs produced by sub-contracts in this wave",
    )


class ParallelExecutionGroup(BaseModel):
    """Immutable group of sub-contracts that can safely execute in parallel."""

    model_config = ConfigDict(frozen=True)

    group_id: str = Field(description="Unique parallel group identifier")
    wave_number: int = Field(ge=1, description="Associated wave number")
    parallelizable: bool = Field(default=True, description="True if all sub-contracts in this group can execute in parallel")
    sub_contract_ids: List[str] = Field(
        default_factory=list,
        description="SubContract IDs in this parallel group",
    )
    blocking_dependencies: List[str] = Field(
        default_factory=list,
        description="SubContract IDs that block this group",
    )
    required_inputs: List[str] = Field(
        default_factory=list,
        description="Input artifact IDs required before execution",
    )
    produced_outputs: List[str] = Field(
        default_factory=list,
        description="Output artifact IDs produced by this group",
    )


# ---------------------------------------------------------------------------
# E2.2.2 - Sub-contract model
# ---------------------------------------------------------------------------

class SubContract(BaseModel):
    """Immutable sub-contract derived from an EngineeringContract.

    Represents a granular, independently executable unit of work.
    Retains complete ancestry: Mission → Plan → Bundle → Profile → Contract → SubContract.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    sub_contract_id: str = Field(
        description="Unique sub-contract identifier (sctr-{contract_id}-{n:02d})"
    )
    parent_contract_id: str = Field(
        description="Parent EngineeringContract identifier"
    )
    mission_id: str = Field(description="Associated mission identifier")

    # Ownership (must match parent)
    agent_profile_id: str = Field(
        description="Agent profile identifier (inherited from parent)"
    )
    skill_bundle_id: str = Field(
        description="Skill bundle identifier (inherited from parent)"
    )

    # Execution definition
    objective: str = Field(
        description="Specific objective this sub-contract fulfills"
    )
    required_capabilities: List[str] = Field(
        default_factory=list,
        description="Capabilities required for this sub-contract",
    )
    required_skills: List[str] = Field(
        default_factory=list,
        description="Specific skills required",
    )
    inputs: List[str] = Field(
        default_factory=list,
        description="Data and artifact inputs needed for execution",
    )
    expected_deliverables: List[str] = Field(
        default_factory=list,
        description="Expected deliverables for this sub-contract",
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="Acceptance criteria for this sub-contract",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="SubContract IDs this depends on",
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Execution constraints",
    )
    repository_scope: str = Field(
        description="Repository scope (inherited from parent)",
    )
    technology_context: List[str] = Field(
        default_factory=list,
        description="Technology context (inherited from parent)",
    )
    priority: str = Field(
        description="Priority level (inherited from parent)",
    )
    execution_order: int = Field(
        ge=0,
        description="Deterministic ordering index within parent contract",
    )
    execution_wave: int = Field(
        ge=1, le=20,
        description="Execution wave number (inherited from parent or recomputed)",
    )
    risk_level: str = Field(
        description="Risk assessment level (inherited from parent)",
    )

    # Decomposition metadata
    is_atomic: bool = Field(
        default=False,
        description="True if parent contract was atomic (no decomposition)",
    )
    decomposition_reason: str = Field(
        default="",
        description="Why this sub-contract was created",
    )
    owned_deliverables: List[str] = Field(
        default_factory=list,
        description="Deliverable IDs owned by this sub-contract",
    )

    # Traceability (full ancestry chain)
    traceability: Dict[str, str] = Field(
        default_factory=dict,
        description="Traceability mapping: intent_id, plan_id, bundle_id, "
        "profile_id, contract_id, deliverable_ids",
    )

    # Determinism
    deterministic_hash: str = Field(
        description="SHA-256 hash for deterministic identity verification",
    )


# ---------------------------------------------------------------------------
# E2.2.5 - Dependency graph
# ---------------------------------------------------------------------------

class DependencyEdge(BaseModel):
    """Immutable directed edge in the dependency graph."""

    model_config = ConfigDict(frozen=True)

    from_id: str = Field(
        description="Source sub-contract ID"
    )
    to_id: str = Field(
        description="Target sub-contract ID (depends on from_id)"
    )
    dependency_type: DependencyType = Field(
        description="Type of dependency relationship"
    )
    artifact_id: str = Field(
        default="",
        description="Artifact ID involved in this dependency (if applicable)",
    )
    is_blocking: bool = Field(
        default=True,
        description="True if this dependency blocks the target until resolved",
    )


class DependencyGraph(BaseModel):
    """Immutable dependency graph for sub-contracts."""

    model_config = ConfigDict(frozen=True)

    graph_id: str = Field(
        description="Unique dependency graph identifier"
    )
    nodes: List[str] = Field(
        default_factory=list,
        description="All sub-contract IDs in this graph",
    )
    edges: List[DependencyEdge] = Field(
        default_factory=list,
        description="Directed edges between sub-contracts",
    )
    adjacency: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Adjacency list: sub_contract_id -> [dependent_ids]",
    )
    reverse_adjacency: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Reverse adjacency: sub_contract_id -> [dependency_ids]",
    )
    in_degree: Dict[str, int] = Field(
        default_factory=dict,
        description="In-degree count per sub-contract (for topological sort)",
    )
    is_acyclic: bool = Field(
        default=True,
        description="True if graph contains no cycles",
    )


# ---------------------------------------------------------------------------
# E2.2.11 - Coverage metrics
# ---------------------------------------------------------------------------

class DecompositionCoverageMetrics(BaseModel):
    """E2.2.11 - Coverage metrics for decomposition validation."""

    model_config = ConfigDict(frozen=True)

    total_parent_contracts: int = Field(
        description="Total number of parent EngineeringContracts",
    )
    decomposed_contracts: int = Field(
        description="Contracts that produced sub-contracts",
    )
    atomic_contracts: int = Field(
        description="Contracts marked as atomic (single sub-contract)",
    )
    total_sub_contracts: int = Field(
        description="Total number of sub-contracts generated",
    )
    total_deliverables: int = Field(
        description="Total deliverables across all contracts",
    )
    covered_deliverables: int = Field(
        description="Deliverables assigned to sub-contracts",
    )
    total_acceptance_criteria: int = Field(
        description="Total acceptance criteria across all contracts",
    )
    covered_acceptance_criteria: int = Field(
        description="Criteria assigned to sub-contracts",
    )
    total_artifacts: int = Field(
        description="Total artifacts identified",
    )
    routed_artifacts: int = Field(
        description="Artifacts with routing information",
    )
    coverage_percent: float = Field(
        description="Overall decomposition coverage (0.0 to 100.0)",
    )


# ---------------------------------------------------------------------------
# E2.2.13 - Contract Decomposition Report
# ---------------------------------------------------------------------------

class ContractDecompositionReport(BaseModel):
    """Immutable contract decomposition report.

    Output of ContractDecompositionEngine.
    Consumed by E3 (Real Code Generation).
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    report_id: str = Field(
        description="Unique report identifier (cdcr-{sha256})"
    )
    mission_id: str = Field(
        description="Associated mission identifier"
    )
    parent_contract_report_id: str = Field(
        description="Source EngineeringContractReport identifier",
    )

    # Decomposition output
    sub_contracts: List[SubContract] = Field(
        default_factory=list,
        description="All generated sub-contracts",
    )
    dependency_graph: DependencyGraph = Field(
        description="Dependency graph for all sub-contracts",
    )
    artifact_routes: List[ArtifactRoute] = Field(
        default_factory=list,
        description="Artifact routing information",
    )
    execution_waves: List[ExecutionWave] = Field(
        default_factory=list,
        description="Execution waves (ordered by wave_number)",
    )
    parallel_execution_groups: List[ParallelExecutionGroup] = Field(
        default_factory=list,
        description="Groups of sub-contracts safe for parallel execution",
    )

    # Coverage and validation
    coverage: Dict[str, Any] = Field(
        default_factory=dict,
        description="Decomposition coverage metrics",
    )
    validation_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Validation check results",
    )

    # Traceability
    traceability: Dict[str, str] = Field(
        default_factory=dict,
        description="Full upstream traceability chain",
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="True if decomposition was fully deterministic",
    )
    report_hash: str = Field(
        description="SHA-256 hash of entire report for integrity",
    )

    # Metadata
    total_sub_contracts: int = Field(
        description="Count of sub-contracts",
    )
    total_waves: int = Field(
        description="Count of execution waves",
    )
    total_artifact_routes: int = Field(
        description="Count of artifact routes",
    )
    parallelizable_groups: int = Field(
        description="Count of parallel execution groups",
    )
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp of generation",
    )


# ---------------------------------------------------------------------------
# E2.2.11 - Contract Decomposition Validator
# ---------------------------------------------------------------------------

class ContractDecompositionValidator:
    """Validates ContractDecompositionReport against E2.2 acceptance criteria.

    Runs all validation checks and returns a detailed dict of per-check results.
    Raises ValidationError if any check fails.
    """

    def validate(
        self,
        contract_report: Any,
        sub_contracts: List[SubContract],
        dependency_graph: DependencyGraph,
        execution_waves: List[ExecutionWave],
    ) -> Dict[str, Any]:
        """Run all E2.2 validation checks.

        Args:
            contract_report: Source EngineeringContractReport.
            sub_contracts: Decomposed sub-contracts.
            dependency_graph: Dependency graph.
            execution_waves: Computed execution waves.

        Returns:
            Dict with per-check results. Raises ValidationError on failure.
        """
        results: Dict[str, Any] = {}

        results["E2.2.1_parent_decomposed"] = self._check_parent_decomposed(
            contract_report, sub_contracts
        )
        results["E2.2.2_single_parent"] = self._check_single_parent(sub_contracts)
        results["E2.2.3_single_deliverable_owner"] = self._check_deliverable_ownership(
            sub_contracts
        )
        results["E2.2.4_acceptance_criteria_owned"] = self._check_acceptance_criteria_ownership(
            sub_contracts, contract_report
        )
        results["E2.2.5_no_orphan_subcontracts"] = self._check_no_orphan_subcontracts(
            sub_contracts
        )
        results["E2.2.6_no_duplicate_ids"] = self._check_no_duplicate_ids(sub_contracts)
        results["E2.2.7_no_duplicate_deliverable"] = self._check_no_duplicate_deliverable(
            sub_contracts
        )
        results["E2.2.8_dependencies_resolve"] = self._check_dependencies_resolve(
            sub_contracts, dependency_graph
        )
        results["E2.2.9_graph_acyclic"] = self._check_graph_acyclic(dependency_graph)
        results["E2.2.10_waves_valid"] = self._check_waves_valid(
            sub_contracts, execution_waves
        )
        results["E2.2.11_repo_scope_preserved"] = self._check_repo_scope_preserved(
            sub_contracts, contract_report
        )
        results["E2.2.12_tech_context_preserved"] = self._check_tech_context_preserved(
            sub_contracts, contract_report
        )
        results["E2.2.13_ownership_preserved"] = self._check_ownership_preserved(
            sub_contracts, contract_report
        )
        results["E2.2.14_traceability_complete"] = self._check_traceability_complete(
            sub_contracts
        )
        results["E2.2.15_deterministic"] = self._check_deterministic(sub_contracts)
        results["E2.2.16_coverage_100"] = self._check_coverage_100(sub_contracts, contract_report)

        failed = [k for k, v in results.items() if not v.get("passed", False)]
        if failed:
            raise ValidationError(
                f"Decomposition validation failed: {len(failed)} checks failed: {failed}"
            )

        return results

    def _check_parent_decomposed(
        self, contract_report: Any, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.1: Every parent contract decomposed or atomic."""
        parent_ids = {c.contract_id for c in contract_report.contracts}
        decomposed_parents = {s.parent_contract_id for s in sub_contracts}
        missing = parent_ids - decomposed_parents
        passed = len(missing) == 0
        return {"passed": passed, "detail": f"Missing parents: {sorted(missing)}"}

    def _check_single_parent(
        self, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.2: Every sub-contract has exactly one parent."""
        all_ok = True
        for s in sub_contracts:
            if not s.parent_contract_id:
                all_ok = False
                break
        return {"passed": all_ok, "detail": "All sub-contracts have one parent"}

    def _check_deliverable_ownership(
        self, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.3: Every deliverable has exactly one owner."""
        all_deliverable_ids: Set[str] = set()
        for s in sub_contracts:
            for did in s.owned_deliverables:
                all_deliverable_ids.add(did)
        owned_once: Set[str] = set()
        for s in sub_contracts:
            for did in s.owned_deliverables:
                if did not in owned_once:
                    owned_once.add(did)
                else:
                    return {"passed": False, "detail": f"Duplicate owner for {did}"}
        return {"passed": True, "detail": "All deliverables owned once"}

    def _check_acceptance_criteria_ownership(
        self, sub_contracts: List[SubContract], contract_report: Any
    ) -> Dict[str, Any]:
        """E2.2.4: Every acceptance criterion has valid ownership."""
        for s in sub_contracts:
            if not s.acceptance_criteria and not s.parent_contract_id:
                return {"passed": False, "detail": f"Sub-contract {s.sub_contract_id} has no criteria and no parent"}
        return {"passed": True, "detail": "All criteria have valid ownership"}

    def _check_no_orphan_subcontracts(
        self, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.5: No orphan sub-contracts (all have parent)."""
        orphans = [s.sub_contract_id for s in sub_contracts if not s.parent_contract_id]
        return {"passed": len(orphans) == 0, "detail": f"Orphans: {orphans}"}

    def _check_no_duplicate_ids(
        self, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.6: No duplicate sub-contract IDs."""
        ids = [s.sub_contract_id for s in sub_contracts]
        unique = len(ids) == len(set(ids))
        return {"passed": unique, "detail": f"Unique: {len(set(ids))}/{len(ids)}"}

    def _check_no_duplicate_deliverable(
        self, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.7: No duplicate deliverable ownership."""
        owned_ids: List[str] = []
        for s in sub_contracts:
            owned_ids.extend(s.owned_deliverables)
        unique = len(owned_ids) == len(set(owned_ids))
        return {"passed": unique, "detail": f"Unique deliverables: {len(set(owned_ids))}/{len(owned_ids)}"}

    def _check_dependencies_resolve(
        self,
        sub_contracts: List[SubContract],
        dependency_graph: DependencyGraph,
    ) -> Dict[str, Any]:
        """E2.2.8: All dependency references resolve."""
        all_ids = set(dependency_graph.nodes)
        unresolved: Set[str] = set()
        for s in sub_contracts:
            for dep_id in s.dependencies:
                if dep_id not in all_ids:
                    unresolved.add(dep_id)
        return {"passed": len(unresolved) == 0, "detail": f"Unresolved: {sorted(unresolved)}"}

    def _check_graph_acyclic(
        self, dependency_graph: DependencyGraph
    ) -> Dict[str, Any]:
        """E2.2.9: Dependency graph is acyclic."""
        return {
            "passed": dependency_graph.is_acyclic,
            "detail": "No cycles" if dependency_graph.is_acyclic else "Cycle detected",
        }

    def _check_waves_valid(
        self,
        sub_contracts: List[SubContract],
        execution_waves: List[ExecutionWave],
    ) -> Dict[str, Any]:
        """E2.2.10: Execution waves are topologically valid."""
        wave_numbers = {w.wave_number for w in execution_waves}
        expected = set(range(1, len(execution_waves) + 1))
        missing = expected - wave_numbers
        all_sctrs = {s.sub_contract_id for s in sub_contracts}
        wave_sctrs: Set[str] = set()
        for w in execution_waves:
            wave_sctrs.update(w.sub_contract_ids)
        unplaced = all_sctrs - wave_sctrs
        return {
            "passed": len(missing) == 0 and len(unplaced) == 0,
            "detail": f"Missing waves: {sorted(missing)}, Unplaced: {sorted(unplaced)}",
        }

    def _check_repo_scope_preserved(
        self, sub_contracts: List[SubContract], contract_report: Any
    ) -> Dict[str, Any]:
        """E2.2.11: Repository scope preserved from parent."""
        contract_map = {c.contract_id: c for c in contract_report.contracts}
        mismatches = []
        for s in sub_contracts:
            parent = contract_map.get(s.parent_contract_id)
            if parent and s.repository_scope != parent.repository_scope:
                mismatches.append(s.sub_contract_id)
        return {"passed": len(mismatches) == 0, "detail": f"Mismatches: {mismatches}"}

    def _check_tech_context_preserved(
        self, sub_contracts: List[SubContract], contract_report: Any
    ) -> Dict[str, Any]:
        """E2.2.12: Technology context preserved from parent."""
        contract_map = {c.contract_id: c for c in contract_report.contracts}
        mismatches = []
        for s in sub_contracts:
            parent = contract_map.get(s.parent_contract_id)
            if parent and set(s.technology_context) != set(parent.technology_context):
                mismatches.append(s.sub_contract_id)
        return {"passed": len(mismatches) == 0, "detail": f"Mismatches: {mismatches}"}

    def _check_ownership_preserved(
        self, sub_contracts: List[SubContract], contract_report: Any
    ) -> Dict[str, Any]:
        """E2.2.13: Agent/profile/bundle ownership preserved."""
        contract_map = {c.contract_id: c for c in contract_report.contracts}
        mismatches = []
        for s in sub_contracts:
            parent = contract_map.get(s.parent_contract_id)
            if parent:
                if s.agent_profile_id != parent.agent_profile_id:
                    mismatches.append(f"{s.sub_contract_id}: agent_profile")
                if s.skill_bundle_id != parent.skill_bundle_id:
                    mismatches.append(f"{s.sub_contract_id}: skill_bundle")
        return {"passed": len(mismatches) == 0, "detail": f"Mismatches: {mismatches}"}

    def _check_traceability_complete(
        self, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.14: Traceability is complete for every sub-contract."""
        incomplete = [
            s.sub_contract_id
            for s in sub_contracts
            if not s.traceability or "contract_id" not in s.traceability
        ]
        return {"passed": len(incomplete) == 0, "detail": f"Incomplete: {incomplete}"}

    def _check_deterministic(
        self, sub_contracts: List[SubContract]
    ) -> Dict[str, Any]:
        """E2.2.15: Deterministic output for identical inputs."""
        ids = [s.sub_contract_id for s in sub_contracts]
        sequential = all(ids[i] < ids[i + 1] for i in range(len(ids) - 1)) if len(ids) > 1 else True
        hashes = [s.deterministic_hash for s in sub_contracts]
        hashes_unique = len(hashes) == len(set(hashes))
        return {
            "passed": sequential and hashes_unique,
            "detail": f"Sequential IDs: {sequential}, Unique hashes: {hashes_unique}",
        }

    def _check_coverage_100(
        self, sub_contracts: List[SubContract], contract_report: Any
    ) -> Dict[str, Any]:
        """E2.2.16: 100% parent contract coverage."""
        all_parent_ids = {c.contract_id for c in contract_report.contracts}
        decomposed_parents = {s.parent_contract_id for s in sub_contracts}
        missing = all_parent_ids - decomposed_parents
        return {
            "passed": len(missing) == 0,
            "detail": f"Coverage: {len(decomposed_parents)}/{len(all_parent_ids)}",
        }

