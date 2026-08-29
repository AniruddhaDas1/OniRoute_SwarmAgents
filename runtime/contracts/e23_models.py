"""E2.3 Artifact Execution Planning Models.

Phase E2.3 — Contract Execution Preparation / Artifact Planning.

Provides immutable models for converting ContractDecompositionReport
into an ArtifactExecutionPlan ready for E3.1 Real Code Generation.

Self-contained: depends only on Python stdlib + pydantic to avoid circular imports.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# E2.3 - Exception classes
# ---------------------------------------------------------------------------

class ArtifactPlanningError(Exception):
    """Base exception for artifact planning failures."""
    pass


class PathResolutionError(ArtifactPlanningError):
    """Raised when a repository path cannot be resolved."""
    pass


class StrategyUnresolvedError(ArtifactPlanningError):
    """Raised when a generation strategy cannot be determined."""
    pass


class ConflictError(ArtifactPlanningError):
    """Raised when a planning conflict is detected."""
    pass


class ValidationCheckpointError(ArtifactPlanningError):
    """Raised when validation checkpoint check fails."""
    pass


# ---------------------------------------------------------------------------
# E2.3.3 - Generation strategies
# ---------------------------------------------------------------------------

class GenerationStrategy(str, Enum):
    """Machine-readable artifact generation strategy for E3.1."""

    TEMPLATE = "TEMPLATE"          # Use an existing template
    PATTERN = "PATTERN"            # Apply a known pattern
    LLM_GENERATED = "LLM_GENERATED"  # Requires LLM generation
    UNRESOLVED = "UNRESOLVED"      # Cannot determine strategy


# ---------------------------------------------------------------------------
# E2.3.4 - Path types
# ---------------------------------------------------------------------------

class PathType(str, Enum):
    """Type of repository path for an artifact."""

    SOURCE = "SOURCE"              # Source code file
    CONFIG = "CONFIG"             # Configuration file
    TEST = "TEST"                 # Test file
    DOC = "DOC"                   # Documentation file
    SCHEMA = "SCHEMA"             # Database schema / migration
    ASSET = "ASSET"              # Static asset
    BUILD = "BUILD"              # Build artifact
    OTHER = "OTHER"               # Miscellaneous


# ---------------------------------------------------------------------------
# E2.3.6 - Artifact overwrite policies
# ---------------------------------------------------------------------------

class OverwritePolicy(str, Enum):
    """Policy for handling existing files at target path."""

    SAFE = "SAFE"                # Write only if file doesn't exist
    OVERWRITE = "OVERWRITE"       # Always overwrite
    SKIP = "SKIP"                # Never overwrite, skip if exists
    RENAME = "RENAME"            # Rename with suffix if exists


# ---------------------------------------------------------------------------
# E2.3.6 - Artifact dependency types
# ---------------------------------------------------------------------------

class ArtifactDependencyType(str, Enum):
    """Type of dependency between artifacts."""

    REQUIRES = "REQUIRES"         # Needs artifact from another unit
    PRODUCES = "PRODUCES"         # Produces artifact consumed by others
    BLOCKS = "BLOCKS"             # Blocks another artifact
    VALIDATES = "VALIDATES"        # Validates another artifact


# ---------------------------------------------------------------------------
# E2.3.6 - Artifact dependency input
# ---------------------------------------------------------------------------

class ArtifactDependencyInput(BaseModel):
    """An input artifact required before generation."""

    model_config = ConfigDict(frozen=True)

    input_id: str = Field(
        description="Unique input identifier (aei-{unit_id}-{n:03d})"
    )
    source_artifact_id: str = Field(
        description="Artifact ID that provides this input"
    )
    source_sub_contract_id: str = Field(
        description="SubContract that produces this input"
    )
    dependency_type: ArtifactDependencyType = Field(
        description="Type of dependency relationship"
    )
    required_before_generation: bool = Field(
        default=True,
        description="True if input must exist before generation",
    )


# ---------------------------------------------------------------------------
# E2.3.9 - Validation checkpoint categories
# ---------------------------------------------------------------------------

class ValidationCategory(str, Enum):
    """Category of validation checkpoint."""

    PATH_VALIDATION = "PATH_VALIDATION"
    ARTIFACT_TYPE_VALIDATION = "ARTIFACT_TYPE_VALIDATION"
    DEPENDENCY_VALIDATION = "DEPENDENCY_VALIDATION"
    REPOSITORY_BOUNDARY_VALIDATION = "REPOSITORY_BOUNDARY_VALIDATION"
    TECHNOLOGY_COMPATIBILITY = "TECHNOLOGY_COMPATIBILITY"
    ACCEPTANCE_CRITERIA_LINKAGE = "ACCEPTANCE_CRITERIA_LINKAGE"
    REQUIRED_INPUT_AVAILABILITY = "REQUIRED_INPUT_AVAILABILITY"
    OUTPUT_OWNERSHIP = "OUTPUT_OWNERSHIP"


class ValidationCheckpoint(BaseModel):
    """Immutable validation checkpoint for an artifact execution unit."""

    model_config = ConfigDict(frozen=True)

    checkpoint_id: str = Field(
        description="Unique checkpoint identifier (chk-{unit_id}-{category})"
    )
    category: ValidationCategory = Field(
        description="Validation category"
    )
    description: str = Field(
        description="Human-readable checkpoint description"
    )
    is_blocking: bool = Field(
        default=True,
        description="True if E3.1 must pass this before proceeding",
    )
    validator: str = Field(
        description="Name of the validator/rule that checks this",
    )


# ---------------------------------------------------------------------------
# E2.3.2 - Artifact Execution Unit
# ---------------------------------------------------------------------------

class ArtifactExecutionUnit(BaseModel):
    """Immutable execution unit representing one concrete artifact to generate.

    This is the granular unit that E3.1 will consume.
    Each unit represents exactly ONE file or artifact.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    artifact_execution_id: str = Field(
        description="Unique execution unit identifier (aeu-{sctr_id}-{n:02d})"
    )
    artifact_id: str = Field(
        description="Associated artifact identifier from upstream"
    )
    sub_contract_id: str = Field(
        description="Parent SubContract identifier"
    )
    parent_contract_id: str = Field(
        description="Grandparent EngineeringContract identifier"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )

    # Ownership
    agent_profile_id: str = Field(
        description="Agent profile that will execute this"
    )
    skill_bundle_id: str = Field(
        description="Skill bundle associated with this artifact"
    )

    # Repository
    repository_scope: str = Field(
        description="Authorized repository scope (from parent SubContract)"
    )
    target_path: str = Field(
        description="Repository-relative target path"
    )
    path_type: PathType = Field(
        description="Type of file at target path"
    )
    overwrite_policy: OverwritePolicy = Field(
        default=OverwritePolicy.SAFE,
        description="Policy for handling existing files",
    )

    # Artifact
    artifact_type: str = Field(
        description="Artifact type (schema, api, component, config, test, doc)"
    )
    file_format: str = Field(
        description="File format/extension (e.g., tsx, py, sql)"
    )
    language: str = Field(
        default="",
        description="Programming language (e.g., TypeScript, Python)"
    )
    framework: str = Field(
        default="",
        description="Framework (e.g., React, FastAPI)"
    )
    technology_context: List[str] = Field(
        default_factory=list,
        description="Technology stack context",
    )

    # Generation
    generation_strategy: GenerationStrategy = Field(
        description="Deterministic generation strategy for E3.1"
    )
    strategy_reason: str = Field(
        default="",
        description="Why this strategy was selected (or why UNRESOLVED)",
    )
    generation_priority: str = Field(
        default="MEDIUM",
        description="Priority level (HIGH, MEDIUM, LOW)",
    )
    execution_wave: int = Field(
        ge=1,
        description="Execution wave number (from E2.2)"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="SubContract IDs this unit depends on",
    )
    required_inputs: List[ArtifactDependencyInput] = Field(
        default_factory=list,
        description="Artifact inputs required before generation",
    )

    # Expected output
    expected_outputs: List[str] = Field(
        default_factory=list,
        description="Outputs this artifact will produce",
    )

    # Validation
    validation_checkpoints: List[ValidationCheckpoint] = Field(
        default_factory=list,
        description="Validation checkpoints for E3.1",
    )
    acceptance_criteria_ids: List[str] = Field(
        default_factory=list,
        description="AcceptanceCriteria IDs linked to this unit",
    )

    # Traceability
    artifact_route_id: str = Field(
        default="",
        description="Source ArtifactRoute ID from E2.2"
    )
    deliverable_id: str = Field(
        default="",
        description="Source DeliverableContract ID"
    )
    deterministic_hash: str = Field(
        description="SHA-256 hash for deterministic identity",
    )


# ---------------------------------------------------------------------------
# E2.3.6 - Artifact Dependency Graph
# ---------------------------------------------------------------------------

class ArtifactDependencyEdge(BaseModel):
    """Immutable edge in the artifact dependency graph."""

    model_config = ConfigDict(frozen=True)

    from_artifact_execution_id: str = Field(
        description="Source artifact execution unit ID"
    )
    to_artifact_execution_id: str = Field(
        description="Target artifact execution unit ID (depends on source)"
    )
    dependency_type: ArtifactDependencyType = Field(
        description="Type of artifact dependency"
    )
    artifact_id: str = Field(
        default="",
        description="Artifact ID involved in this dependency",
    )
    is_blocking: bool = Field(
        default=True,
        description="True if target cannot proceed until source completes",
    )


class ArtifactDependencyGraph(BaseModel):
    """Immutable artifact-level dependency graph."""

    model_config = ConfigDict(frozen=True)

    graph_id: str = Field(
        description="Unique graph identifier"
    )
    nodes: List[str] = Field(
        default_factory=list,
        description="All artifact execution unit IDs in this graph",
    )
    edges: List[ArtifactDependencyEdge] = Field(
        default_factory=list,
        description="Directed edges between artifact execution units",
    )
    adjacency: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Adjacency list for topological ordering",
    )
    reverse_adjacency: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Reverse adjacency for dependency tracking",
    )
    in_degree: Dict[str, int] = Field(
        default_factory=dict,
        description="In-degree count per node",
    )
    is_acyclic: bool = Field(
        default=True,
        description="True if graph contains no cycles",
    )


# ---------------------------------------------------------------------------
# E2.3.7 - Artifact Execution Wave
# ---------------------------------------------------------------------------

class ArtifactExecutionWave(BaseModel):
    """Immutable artifact-level execution wave."""

    model_config = ConfigDict(frozen=True)

    wave_number: int = Field(ge=1, description="Wave number")
    wave_name: str = Field(description="Human-readable wave name")
    artifact_execution_ids: List[str] = Field(
        default_factory=list,
        description="ArtifactExecutionUnit IDs in this wave",
    )
    parallelizable: bool = Field(
        default=True,
        description="True if all units in this wave can execute in parallel",
    )
    blocking_waves: List[int] = Field(
        default_factory=list,
        description="Wave numbers that must complete first",
    )
    blocking_artifacts: Dict[int, List[str]] = Field(
        default_factory=dict,
        description="Per-blocking-wave, the artifact IDs that must complete",
    )
    required_artifact_ids: List[str] = Field(
        default_factory=list,
        description="Artifact IDs required before this wave",
    )
    produced_artifact_ids: List[str] = Field(
        default_factory=list,
        description="Artifact IDs produced by this wave",
    )


# ---------------------------------------------------------------------------
# E2.3.5 - Repository boundary
# ---------------------------------------------------------------------------

class RepositoryBoundary(BaseModel):
    """Immutable repository boundary definition."""

    model_config = ConfigDict(frozen=True)

    scope: str = Field(
        description="Repository scope prefix (e.g., 'frontend/src/')"
    )
    discipline: str = Field(
        description="Engineering discipline owning this scope"
    )
    is_authorized: bool = Field(
        default=True,
        description="True if this scope is authorized for artifact generation",
    )


# ---------------------------------------------------------------------------
# E2.3.11 - Conflict detection
# ---------------------------------------------------------------------------

class ConflictType(str, Enum):
    """Type of planning conflict detected."""

    DUPLICATE_PATH = "DUPLICATE_PATH"
    OUTSIDE_SCOPE = "OUTSIDE_SCOPE"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    UNKNOWN_PRODUCER = "UNKNOWN_PRODUCER"
    TECH_CONTEXT_MISMATCH = "TECH_CONTEXT_MISMATCH"
    DUPLICATE_OWNERSHIP = "DUPLICATE_OWNERSHIP"
    UNKNOWN_STRATEGY = "UNKNOWN_STRATEGY"
    MISSING_REQUIRED_INPUT = "MISSING_REQUIRED_INPUT"
    MISSING_AC_CRITERIA = "MISSING_AC_CRITERIA"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"


class Conflict(BaseModel):
    """Immutable planning conflict."""

    model_config = ConfigDict(frozen=True)

    conflict_id: str = Field(description="Unique conflict identifier")
    conflict_type: ConflictType = Field(description="Type of conflict")
    description: str = Field(description="Human-readable conflict description")
    affected_artifact_ids: List[str] = Field(
        default_factory=list,
        description="Artifact IDs affected by this conflict",
    )
    severity: str = Field(
        default="ERROR",
        description="Severity: ERROR or WARNING",
    )


class ConflictReport(BaseModel):
    """Immutable conflict detection report."""

    model_config = ConfigDict(frozen=True)

    total_conflicts: int = Field(description="Total conflicts detected")
    errors: int = Field(description="Count of ERROR severity conflicts")
    warnings: int = Field(description="Count of WARNING severity conflicts")
    conflicts: List[Conflict] = Field(
        default_factory=list,
        description="Individual conflict records",
    )
    has_blocking_conflicts: bool = Field(
        description="True if any ERROR-level conflict blocks execution",
    )


# ---------------------------------------------------------------------------
# E2.3.8 - Generation strategy summary
# ---------------------------------------------------------------------------

class GenerationStrategySummary(BaseModel):
    """Immutable summary of generation strategies in the plan."""

    model_config = ConfigDict(frozen=True)

    total_units: int = Field(description="Total artifact execution units")
    template_count: int = Field(description="Units using TEMPLATE strategy")
    pattern_count: int = Field(description="Units using PATTERN strategy")
    llm_generated_count: int = Field(description="Units using LLM_GENERATED strategy")
    unresolved_count: int = Field(description="Units with UNRESOLVED strategy")
    unresolved_artifacts: List[str] = Field(
        default_factory=list,
        description="Artifact IDs with UNRESOLVED strategy",
    )


# ---------------------------------------------------------------------------
# E2.3.4 - Repository scope summary
# ---------------------------------------------------------------------------

class RepositoryScopeSummary(BaseModel):
    """Immutable summary of repository scopes in the plan."""

    model_config = ConfigDict(frozen=True)

    total_units: int = Field(description="Total artifact execution units")
    scopes: Dict[str, int] = Field(
        default_factory=dict,
        description="Scope -> unit count mapping",
    )
    boundaries: List[RepositoryBoundary] = Field(
        default_factory=list,
        description="All repository boundaries",
    )
    out_of_scope_artifacts: List[str] = Field(
        default_factory=list,
        description="Artifact IDs outside any authorized scope",
    )


# ---------------------------------------------------------------------------
# E2.3.10 - Execution ordering
# ---------------------------------------------------------------------------

class ArtifactExecutionOrder(BaseModel):
    """Immutable execution ordering for a single artifact."""

    model_config = ConfigDict(frozen=True)

    artifact_execution_id: str = Field(
        description="ArtifactExecutionUnit ID"
    )
    execution_wave: int = Field(
        ge=1,
        description="Execution wave number",
    )
    execution_order: int = Field(
        ge=0,
        description="Deterministic ordering within wave",
    )
    blocking_artifacts: List[str] = Field(
        default_factory=list,
        description="Artifact IDs that must complete first",
    )
    prerequisite_artifacts: List[str] = Field(
        default_factory=list,
        description="Artifact IDs required as inputs",
    )


# ---------------------------------------------------------------------------
# E2.3.13 - Artifact Execution Plan
# ---------------------------------------------------------------------------

class ArtifactExecutionPlan(BaseModel):
    """Immutable artifact execution plan — primary E3.1 input.

    Produced by ArtifactExecutionPlanner from ContractDecompositionReport.
    Contains everything E3.1 needs to begin real code generation.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    plan_id: str = Field(
        description="Unique plan identifier (aep-{sha256})"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )
    contract_decomposition_report_id: str = Field(
        description="Source ContractDecompositionReport identifier"
    )

    # Execution units
    execution_units: List[ArtifactExecutionUnit] = Field(
        default_factory=list,
        description="All artifact execution units",
    )

    # Artifact dependency graph
    artifact_dependency_graph: ArtifactDependencyGraph = Field(
        description="Artifact-level dependency graph",
    )

    # Execution ordering
    execution_waves: List[ArtifactExecutionWave] = Field(
        default_factory=list,
        description="Artifact-level execution waves",
    )
    execution_order: List[ArtifactExecutionOrder] = Field(
        default_factory=list,
        description="Per-artifact execution ordering",
    )

    # Summaries
    generation_strategy_summary: GenerationStrategySummary = Field(
        description="Summary of generation strategies",
    )
    repository_scope_summary: RepositoryScopeSummary = Field(
        description="Summary of repository scopes",
    )

    # Validation
    validation_checkpoints: List[ValidationCheckpoint] = Field(
        default_factory=list,
        description="All validation checkpoints across units",
    )

    # Conflict detection
    conflict_report: ConflictReport = Field(
        description="Planning conflict detection report",
    )

    # Traceability
    traceability: Dict[str, str] = Field(
        default_factory=dict,
        description="Full upstream traceability: mission_id, plan_id, bundle_id, profile_id, contract_id, decomposition_id",
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="True if plan is fully deterministic",
    )
    deterministic_hash: str = Field(
        description="SHA-256 hash for plan integrity verification",
    )

    # Validation result
    validation_passed: bool = Field(
        default=True,
        description="True if all validation checks passed",
    )

    # Metadata
    total_artifacts: int = Field(
        description="Total artifact execution units",
    )
    total_waves: int = Field(
        description="Total execution waves",
    )
    timestamp: str = Field(
        description="ISO-8601 UTC timestamp of generation",
    )


# ---------------------------------------------------------------------------
# Deterministic ID helpers
# ---------------------------------------------------------------------------

def compute_artifact_execution_id(sctr_id: str, index: int) -> str:
    """Compute deterministic artifact execution unit ID."""
    return f"aeu-{sctr_id}-{index:02d}"


def compute_artifact_execution_hash(
    artifact_execution_id: str,
    artifact_id: str,
    sub_contract_id: str,
    target_path: str,
) -> str:
    """Compute deterministic SHA-256 hash for an artifact execution unit."""
    payload = f"{artifact_execution_id}:{artifact_id}:{sub_contract_id}:{target_path}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_plan_hash(
    plan_id: str,
    decomposition_report_id: str,
    execution_units: List[ArtifactExecutionUnit],
    execution_waves: List[ArtifactExecutionWave],
) -> str:
    """Compute SHA-256 hash of the entire artifact execution plan."""
    hash_payload = {
        "plan_id": plan_id,
        "decomposition_report_id": decomposition_report_id,
        "unit_ids": sorted([u.artifact_execution_id for u in execution_units]),
        "wave_numbers": sorted([w.wave_number for w in execution_waves]),
        "unit_count": len(execution_units),
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Path normalization helpers
# ---------------------------------------------------------------------------

def normalize_path(path: str) -> str:
    """Normalize a repository-relative path."""
    # Remove leading/trailing whitespace
    path = path.strip()
    # Remove duplicate slashes
    while "//" in path:
        path = path.replace("//", "/")
    # Remove trailing slash
    path = path.rstrip("/")
    return path


def validate_no_traversal(path: str) -> bool:
    """Check that path does not escape repository scope via ../ traversal."""
    return ".." not in path


def validate_absolute_path(path: str) -> bool:
    """Check that path is not absolute."""
    return not path.startswith("/")
