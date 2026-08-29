"""E3.1 Real Code Generation Engine Models.

Phase E3.1 — Real Code Generation Engine.

Provides immutable models for consuming ArtifactExecutionPlan and
producing real source files via template resolution, pattern application,
or LLM generation through the existing InvocationEngine.

Self-contained: depends only on Python stdlib + pydantic + runtime.contracts.e23_models.

Architecture:
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionUnit
        ↓
    GenerationContext
        ↓
    TemplateResolver | PatternResolver | LLM Generation
        ↓
    Generated Content
        ↓
    ContentValidation
        ↓
    RepositoryWriter
        ↓
    REAL FILES
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from runtime.contracts.e23_models import (
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactExecutionWave,
    GenerationStrategy,
    OverwritePolicy,
    PathType,
    ValidationCheckpoint,
    ValidationCategory,
)


# ---------------------------------------------------------------------------
# E3.1 - Exception classes
# ---------------------------------------------------------------------------

class CodeGenerationError(Exception):
    """Base exception for E3.1 generation failures."""
    pass


class TemplateResolutionError(CodeGenerationError):
    """Raised when a template cannot be resolved."""
    pass


class PatternResolutionError(CodeGenerationError):
    """Raised when a pattern cannot be resolved."""
    pass


class ContentValidationError(CodeGenerationError):
    """Raised when generated content fails validation."""
    pass


class RepositoryWriteError(CodeGenerationError):
    """Raised when a file cannot be written to the repository."""
    pass


class GenerationContextError(CodeGenerationError):
    """Raised when generation context cannot be built."""
    pass


class BlockingConflictError(CodeGenerationError):
    """Raised when blocking conflicts prevent execution."""
    pass


# ---------------------------------------------------------------------------
# E3.1.1 - Generation Context
# ---------------------------------------------------------------------------

class GenerationContext(BaseModel):
    """Immutable context for generating a single artifact.

    Built from ArtifactExecutionUnit with full upstream traceability.
    Provides everything needed to generate the actual artifact content.
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )

    # Project context
    project_objective: str = Field(
        description="Original project/mission objective"
    )

    # Artifact context
    artifact_objective: str = Field(
        description="Objective of this specific artifact"
    )
    artifact_type: str = Field(
        description="Type: schema, api, component, config, test, doc"
    )
    parent_contract_objective: str = Field(
        description="Parent contract's objective"
    )
    sub_contract_objective: str = Field(
        description="Sub-contract's objective"
    )

    # Target
    repository_scope: str = Field(
        description="Authorized repository scope"
    )
    target_path: str = Field(
        description="Repository-relative target path"
    )
    path_type: PathType = Field(
        description="Type of file at target path"
    )
    overwrite_policy: OverwritePolicy = Field(
        description="Policy for handling existing files"
    )

    # Technology
    language: str = Field(
        description="Programming language"
    )
    framework: str = Field(
        description="Framework (e.g., React, FastAPI)"
    )
    file_format: str = Field(
        description="File format/extension"
    )
    technology_context: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Technology stack context"
    )

    # Generation
    generation_strategy: GenerationStrategy = Field(
        description="Deterministic generation strategy"
    )
    generation_priority: str = Field(
        description="Priority level: HIGH, MEDIUM, LOW"
    )

    # Dependencies
    dependencies: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="SubContract IDs this depends on"
    )
    required_inputs: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Artifact inputs required before generation"
    )

    # Ownership
    agent_profile_id: str = Field(
        description="Agent profile for execution"
    )
    skill_bundle_id: str = Field(
        description="Skill bundle for generation"
    )

    # Validation
    validation_checkpoints: Tuple[ValidationCheckpoint, ...] = Field(
        default_factory=tuple,
        description="Validation checkpoints"
    )
    acceptance_criteria_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Acceptance criteria IDs"
    )

    # Traceability
    traceability: Dict[str, str] = Field(
        default_factory=dict,
        description="Upstream traceability map"
    )

    # Determinism
    deterministic_hash: str = Field(
        description="SHA-256 hash for context integrity"
    )


# ---------------------------------------------------------------------------
# E3.1.2 - Generation Request (for LLM generation)
# ---------------------------------------------------------------------------

class GenerationRequest(BaseModel):
    """Immutable request for LLM-based artifact generation.

    Constructed from GenerationContext for InvocationEngine.invoke().
    """

    model_config = ConfigDict(frozen=True)

    # Identity
    request_id: str = Field(
        description="Unique generation request identifier"
    )
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )

    # System prompt - instructs the model
    system_prompt: str = Field(
        description="System prompt for generation"
    )

    # User prompt - specific generation instructions
    user_prompt: str = Field(
        description="User prompt with artifact specifics"
    )

    # Generation parameters
    language: str = Field(
        description="Target programming language"
    )
    framework: str = Field(
        default="",
        description="Target framework"
    )
    file_format: str = Field(
        description="Target file format"
    )

    # Expected output
    expected_outputs: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Expected outputs this artifact will produce"
    )

    # Constraints
    generation_constraints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional generation constraints"
    )

    # Determinism
    deterministic_hash: str = Field(
        description="SHA-256 hash for request integrity"
    )


# ---------------------------------------------------------------------------
# E3.1.3 - Template Resolution
# ---------------------------------------------------------------------------

class TemplateResolution(BaseModel):
    """Immutable result of template resolution."""

    model_config = ConfigDict(frozen=True)

    resolution_id: str = Field(
        description="Unique resolution identifier"
    )
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    template_path: str = Field(
        description="Resolved template file path"
    )
    template_type: str = Field(
        description="Template category/type"
    )
    variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Template variables extracted from context"
    )
    applied_successfully: bool = Field(
        description="True if template was applied successfully"
    )
    error: str = Field(
        default="",
        description="Error message if resolution failed"
    )


# ---------------------------------------------------------------------------
# E3.1.4 - Pattern Resolution
# ---------------------------------------------------------------------------

class PatternResolution(BaseModel):
    """Immutable result of pattern resolution and application."""

    model_config = ConfigDict(frozen=True)

    resolution_id: str = Field(
        description="Unique resolution identifier"
    )
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    pattern_id: str = Field(
        description="Resolved pattern identifier"
    )
    pattern_type: str = Field(
        description="Pattern category/type"
    )
    customization: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pattern customizations from context"
    )
    applied_successfully: bool = Field(
        description="True if pattern was applied successfully"
    )
    error: str = Field(
        default="",
        description="Error message if resolution failed"
    )


# ---------------------------------------------------------------------------
# E3.1.5 - Generated Content
# ---------------------------------------------------------------------------

class GeneratedContent(BaseModel):
    """Immutable generated artifact content."""

    model_config = ConfigDict(frozen=True)

    content_id: str = Field(
        description="Unique content identifier"
    )
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    content: str = Field(
        description="Generated artifact content"
    )
    source: str = Field(
        description="Generation source: TEMPLATE, PATTERN, LLM"
    )
    strategy: GenerationStrategy = Field(
        description="Generation strategy used"
    )

    # Content metadata
    language: str = Field(
        default="",
        description="Programming language"
    )
    file_format: str = Field(
        default="",
        description="File format"
    )
    line_count: int = Field(
        description="Number of lines in generated content"
    )

    # Validation
    validation_passed: bool = Field(
        description="True if content passed validation"
    )
    validation_errors: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Validation error messages"
    )

    # Determinism
    deterministic_hash: str = Field(
        description="SHA-256 hash of content"
    )


# ---------------------------------------------------------------------------
# E3.1.6 - Content Validation
# ---------------------------------------------------------------------------

class ContentValidationResult(BaseModel):
    """Immutable result of content validation."""

    model_config = ConfigDict(frozen=True)

    validation_id: str = Field(
        description="Unique validation identifier"
    )
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    passed: bool = Field(
        description="True if all validations passed"
    )
    checks: Tuple[ContentValidationCheck, ...] = Field(
        default_factory=tuple,
        description="Individual validation checks"
    )
    errors: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Validation error messages"
    )
    warnings: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Validation warnings"
    )


class ContentValidationCheck(BaseModel):
    """Immutable individual content validation check."""

    model_config = ConfigDict(frozen=True)

    check_id: str = Field(
        description="Unique check identifier"
    )
    check_type: str = Field(
        description="Type of validation check"
    )
    passed: bool = Field(
        description="True if check passed"
    )
    message: str = Field(
        description="Check result message"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional check details"
    )


# ---------------------------------------------------------------------------
# E3.1.7 - Repository Write
# ---------------------------------------------------------------------------

class RepositoryWriteResult(BaseModel):
    """Immutable result of writing content to repository."""

    model_config = ConfigDict(frozen=True)

    write_id: str = Field(
        description="Unique write identifier"
    )
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    target_path: str = Field(
        description="Repository-relative target path"
    )
    absolute_path: str = Field(
        description="Absolute filesystem path"
    )
    success: bool = Field(
        description="True if write succeeded"
    )
    action: str = Field(
        description="Action taken: CREATED, OVERWRITTEN, SKIPPED, RENAMED"
    )
    bytes_written: int = Field(
        description="Number of bytes written"
    )
    error: str = Field(
        default="",
        description="Error message if write failed"
    )


# ---------------------------------------------------------------------------
# E3.1.8 - Generation Result (per artifact)
# ---------------------------------------------------------------------------

class GenerationResult(BaseModel):
    """Immutable result of generating a single artifact."""

    model_config = ConfigDict(frozen=True)

    result_id: str = Field(
        description="Unique result identifier"
    )
    artifact_execution_id: str = Field(
        description="Source ArtifactExecutionUnit ID"
    )
    artifact_id: str = Field(
        description="Artifact identifier"
    )
    sub_contract_id: str = Field(
        description="Parent SubContract ID"
    )

    # Strategy used
    strategy: GenerationStrategy = Field(
        description="Generation strategy that was used"
    )

    # Execution
    generation_started: str = Field(
        description="ISO-8601 UTC timestamp when generation started"
    )
    generation_completed: str = Field(
        description="ISO-8601 UTC timestamp when generation completed"
    )
    generation_duration_ms: float = Field(
        description="Generation duration in milliseconds"
    )

    # Result
    success: bool = Field(
        description="True if generation succeeded"
    )
    content: Optional[str] = Field(
        default=None,
        description="Generated content (None if failed)"
    )
    file_written: bool = Field(
        description="True if file was written to repository"
    )
    written_path: str = Field(
        default="",
        description="Repository path where file was written"
    )

    # Context info
    context_hash: str = Field(
        description="GenerationContext hash"
    )

    # Errors
    errors: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Error messages"
    )
    warnings: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Warning messages"
    )

    # Validation
    validation_passed: bool = Field(
        description="True if content passed validation"
    )
    validation_errors: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Validation errors"
    )

    # Determinism
    content_hash: str = Field(
        description="SHA-256 hash of generated content"
    )


# ---------------------------------------------------------------------------
# E3.1.9 - Generation Report (for entire plan)
# ---------------------------------------------------------------------------

class GenerationReport(BaseModel):
    """Immutable report for entire artifact execution plan generation."""

    model_config = ConfigDict(frozen=True)

    # Identity
    report_id: str = Field(
        description="Unique report identifier"
    )
    plan_id: str = Field(
        description="Source ArtifactExecutionPlan ID"
    )
    mission_id: str = Field(
        description="Mission identifier"
    )

    # Timing
    generation_started: str = Field(
        description="ISO-8601 UTC timestamp when generation started"
    )
    generation_completed: str = Field(
        description="ISO-8601 UTC timestamp when generation completed"
    )
    total_duration_ms: float = Field(
        description="Total generation duration in milliseconds"
    )

    # Summary
    total_artifacts: int = Field(
        description="Total artifacts to generate"
    )
    successful_generations: int = Field(
        description="Successfully generated artifacts"
    )
    failed_generations: int = Field(
        description="Failed generations"
    )
    files_written: int = Field(
        description="Files written to repository"
    )

    # Strategy breakdown
    template_count: int = Field(
        description="Artifacts generated via TEMPLATE"
    )
    pattern_count: int = Field(
        description="Artifacts generated via PATTERN"
    )
    llm_count: int = Field(
        description="Artifacts generated via LLM"
    )
    unresolved_count: int = Field(
        description="Artifacts with UNRESOLVED strategy"
    )

    # Wave execution summary
    waves_executed: int = Field(
        description="Number of waves executed"
    )
    wave_results: Tuple[WaveGenerationResult, ...] = Field(
        default_factory=tuple,
        description="Per-wave results"
    )

    # Per-artifact results
    artifact_results: Tuple[GenerationResult, ...] = Field(
        default_factory=tuple,
        description="Per-artifact generation results"
    )

    # Errors
    errors: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Top-level errors"
    )

    # Determinism
    deterministic: bool = Field(
        default=True,
        description="True if generation is deterministic"
    )
    deterministic_hash: str = Field(
        description="SHA-256 hash for report integrity"
    )


class WaveGenerationResult(BaseModel):
    """Immutable result for a single execution wave."""

    model_config = ConfigDict(frozen=True)

    wave_number: int = Field(
        description="Wave number"
    )
    wave_name: str = Field(
        description="Wave name"
    )
    total_units: int = Field(
        description="Total units in wave"
    )
    successful: int = Field(
        description="Successful generations"
    )
    failed: int = Field(
        description="Failed generations"
    )
    artifacts_written: int = Field(
        description="Artifacts written to repository"
    )
    duration_ms: float = Field(
        description="Wave execution duration"
    )


# ---------------------------------------------------------------------------
# E3.1.10 - Blocking Conflict Detection
# ---------------------------------------------------------------------------

class BlockingConflict(BaseModel):
    """Immutable blocking conflict detected during generation."""

    model_config = ConfigDict(frozen=True)

    conflict_id: str = Field(
        description="Unique conflict identifier"
    )
    conflict_type: str = Field(
        description="Type of blocking conflict"
    )
    description: str = Field(
        description="Human-readable conflict description"
    )
    affected_artifact_ids: Tuple[str, ...] = Field(
        default_factory=tuple,
        description="Affected artifact execution IDs"
    )
    resolution_hint: str = Field(
        default="",
        description="Hint for resolving the conflict"
    )


class BlockingConflictReport(BaseModel):
    """Immutable report of blocking conflicts that prevent execution."""

    model_config = ConfigDict(frozen=True)

    has_blocking_conflicts: bool = Field(
        description="True if any blocking conflicts exist"
    )
    conflicts: Tuple[BlockingConflict, ...] = Field(
        default_factory=tuple,
        description="List of blocking conflicts"
    )
    can_proceed: bool = Field(
        description="True if generation can proceed"
    )


# ---------------------------------------------------------------------------
# Deterministic hash computation helpers
# ---------------------------------------------------------------------------

def compute_generation_context_hash(context: GenerationContext) -> str:
    """Compute deterministic SHA-256 hash for GenerationContext."""
    hash_payload = {
        "artifact_execution_id": context.artifact_execution_id,
        "mission_id": context.mission_id,
        "target_path": context.target_path,
        "generation_strategy": context.generation_strategy.value,
        "artifact_type": context.artifact_type,
        "language": context.language,
        "framework": context.framework,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_generation_request_hash(request: GenerationRequest) -> str:
    """Compute deterministic SHA-256 hash for GenerationRequest."""
    hash_payload = {
        "request_id": request.request_id,
        "artifact_execution_id": request.artifact_execution_id,
        "system_prompt_length": len(request.system_prompt),
        "user_prompt_length": len(request.user_prompt),
        "language": request.language,
        "framework": request.framework,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_content_hash(content: str) -> str:
    """Compute deterministic SHA-256 hash for generated content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_generation_result_hash(result: GenerationResult) -> str:
    """Compute deterministic SHA-256 hash for GenerationResult."""
    hash_payload = {
        "result_id": result.result_id,
        "artifact_execution_id": result.artifact_execution_id,
        "strategy": result.strategy.value,
        "success": result.success,
        "content_hash": result.content_hash,
        "file_written": result.file_written,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


def compute_generation_report_hash(report: GenerationReport) -> str:
    """Compute deterministic SHA-256 hash for GenerationReport."""
    hash_payload = {
        "report_id": report.report_id,
        "plan_id": report.plan_id,
        "mission_id": report.mission_id,
        "total_artifacts": report.total_artifacts,
        "successful_generations": report.successful_generations,
        "failed_generations": report.failed_generations,
        "files_written": report.files_written,
    }
    json_bytes = json.dumps(hash_payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Path validation helpers
# ---------------------------------------------------------------------------

def validate_target_path(target_path: str, repository_root: str) -> Tuple[bool, str]:
    """Validate that target path is within repository scope.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not target_path:
        return False, "Target path cannot be empty"

    # Check for path traversal
    if ".." in target_path:
        return False, "Path traversal (..) is not allowed"

    # Check for absolute paths
    if target_path.startswith("/"):
        return False, "Absolute paths are not allowed"

    # Normalize path
    normalized = os.path.normpath(target_path)

    # Check against repository root
    full_path = os.path.join(repository_root, normalized)
    real_root = os.path.realpath(repository_root)
    real_full = os.path.realpath(full_path)

    if not real_full.startswith(real_root):
        return False, f"Path escapes repository scope: {target_path}"

    return True, ""


def normalize_target_path(target_path: str) -> str:
    """Normalize target path for consistency."""
    # Convert to POSIX-style path
    posix_path = str(PurePosixPath(target_path))

    # Remove leading/trailing slashes
    posix_path = posix_path.strip("/")

    # Remove duplicate slashes
    while "//" in posix_path:
        posix_path = posix_path.replace("//", "/")

    return posix_path


# ---------------------------------------------------------------------------
# Template variable extraction helpers
# ---------------------------------------------------------------------------

def extract_template_variables(context: GenerationContext) -> Dict[str, Any]:
    """Extract template variables from GenerationContext.

    These variables can be substituted into templates.
    """
    return {
        # Identity
        "artifact_execution_id": context.artifact_execution_id,
        "mission_id": context.mission_id,

        # Project
        "project_objective": context.project_objective,

        # Artifact
        "artifact_objective": context.artifact_objective,
        "artifact_type": context.artifact_type,
        "parent_contract_objective": context.parent_contract_objective,
        "sub_contract_objective": context.sub_contract_objective,

        # Technology
        "language": context.language,
        "framework": context.framework,
        "file_format": context.file_format,
        "technology_context": list(context.technology_context),

        # Target
        "repository_scope": context.repository_scope,
        "target_path": context.target_path,
        "target_filename": os.path.basename(context.target_path),

        # Generation
        "generation_priority": context.generation_priority,

        # Ownership
        "agent_profile_id": context.agent_profile_id,
        "skill_bundle_id": context.skill_bundle_id,
    }


def apply_template_variables(template: str, variables: Dict[str, Any]) -> str:
    """Apply variables to a template using {{variable}} syntax.

    Handles missing variables gracefully by leaving them as-is.
    """
    result = template

    for key, value in variables.items():
        # Handle string values
        str_value = str(value) if value is not None else ""
        result = result.replace(f"{{{{{key}}}}}", str_value)

        # Also handle Python-style format strings
        try:
            result = result.replace(f"{{{{{key}}}}}", str_value)
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Content validation helpers
# ---------------------------------------------------------------------------

def validate_content_not_empty(content: str, min_lines: int = 1) -> Tuple[bool, str]:
    """Validate that content is not empty."""
    lines = [line for line in content.strip().split("\n") if line.strip()]
    if len(lines) < min_lines:
        return False, f"Content has fewer than {min_lines} non-empty lines"
    return True, ""


def validate_content_no_placeholders(content: str) -> Tuple[bool, str]:
    """Validate that content does not contain placeholder markers."""
    placeholder_patterns = [
        r"\{\{.*\}\}",  # Unrendered template variables
        r"<TODO>",      # TODO comments
        r"<!-- TODO -->",  # HTML TODO comments
        r"# TODO",       # Python/Shell TODO
        r"// TODO",      # JS/TS TODO
        r"PLACEHOLDER",  # Generic placeholder
        r"INSERT_CODE_HERE",
        r"FIXME",
        r"XXX",
    ]

    for pattern in placeholder_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False, f"Content contains placeholder pattern: {pattern}"

    return True, ""


def validate_language_match(content: str, language: str) -> Tuple[bool, str]:
    """Validate that content appears to match the expected language."""
    if not language:
        return True, ""

    language_markers = {
        "python": [r"^import\s+", r"^from\s+\w+\s+import", r"^class\s+\w+", r"^def\s+\w+\("],
        "typescript": [r"^import\s+.*\s+from\s+['\"]", r"^export\s+(function|class|const|interface|type)"],
        "javascript": [r"^const\s+\w+\s*=", r"^let\s+\w+\s*=", r"^function\s+\w+\("],
        "rust": [r"^use\s+\w+::", r"^fn\s+\w+\(", r"^struct\s+\w+", r"^impl\s+\w+"],
        "go": [r"^package\s+\w+", r"^func\s+\w+\(", r"^type\s+\w+\s+struct"],
        "sql": [r"^SELECT\s+", r"^INSERT\s+", r"^UPDATE\s+", r"^CREATE\s+TABLE"],
        "yaml": [r"^\w+:\s*$", r"^\w+:\s+\S"],
        "json": [r"^\{", r"^\["],
    }

    if language.lower() not in language_markers:
        return True, ""  # Unknown language, skip validation

    markers = language_markers[language.lower()]
    has_match = any(re.search(pattern, content, re.MULTILINE | re.IGNORECASE) for pattern in markers)

    if not has_match and len(content.strip()) > 50:
        return False, f"Content does not appear to be valid {language}"

    return True, ""
