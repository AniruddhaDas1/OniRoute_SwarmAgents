"""E3.1 Real Code Generation Engine.

The main orchestrator that consumes ArtifactExecutionPlan and produces
real source files through template resolution, pattern application,
or LLM generation via the existing InvocationEngine.

Architecture:
    ArtifactExecutionPlan
        ↓
    ArtifactExecutionUnit
        ↓
    GenerationContext
        ↓
    GenerationStrategy (TEMPLATE | PATTERN | LLM_GENERATED)
        ↓
    TemplateResolver | PatternResolver | LLM Invocation
        ↓
    GeneratedContent
        ↓
    ContentValidation
        ↓
    RepositoryWriter
        ↓
    REAL FILES

IMPORTANT:
- E3.1 uses the existing InvocationEngine for LLM_GENERATED artifacts
- E3.1 does NOT call providers directly
- E3.1 does NOT bypass ArtifactExecutionPlan
- E3.1 produces REAL source files, not placeholders
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from runtime.contracts.e23_models import (
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactExecutionWave,
    GenerationStrategy,
)
from runtime.contracts.e31_models import (
    BlockingConflictReport,
    CodeGenerationError,
    GeneratedContent,
    GenerationContext,
    GenerationReport,
    GenerationResult,
    GenerationRequest,
    WaveGenerationResult,
    BlockingConflictError,
    compute_content_hash,
    compute_generation_report_hash,
    compute_generation_result_hash,
)
from runtime.contracts.generators.context import GenerationContextBuilder, GenerationRequestConstructor
from runtime.contracts.generators.output import ContentValidator, OutputNormalizer, create_generated_content
from runtime.contracts.generators.patterns import PatternResolver
from runtime.contracts.generators.resolver import TemplateResolver
from runtime.contracts.generators.writer import BlockingConflictDetector, RepositoryWriter
from runtime.models import Capability, ModelManager, SelectionRequest
from runtime.invocation import InvocationEngine


# Optional InvocationEngine import - will be set if provided
_InvocationEngine = None


class RealCodeGenerationEngine:
    """Main engine for real code generation from ArtifactExecutionPlan.

    This engine:
    1. Validates the plan and detects blocking conflicts
    2. Iterates through ArtifactExecutionUnits by wave
    3. Resolves generation strategy (TEMPLATE, PATTERN, LLM_GENERATED)
    4. Generates content via appropriate method
    5. Validates generated content
    6. Writes files to repository
    7. Returns structured generation report

    For LLM_GENERATED artifacts, this engine uses the existing InvocationEngine
    and does NOT call providers directly.
    """

    def __init__(
        self,
        repository_root: str,
        invocation_engine: Optional[InvocationEngine] = None,
        strict_validation: bool = True,
        min_lines: int = 1,
    ):
        """Initialize the generation engine.

        Args:
            repository_root: Absolute path to repository root
            invocation_engine: Existing InvocationEngine for LLM generation
            strict_validation: If True, fail on validation warnings
            min_lines: Minimum lines required for generated content
        """
        self.repository_root = os.path.abspath(repository_root)

        # Initialize components
        self.template_resolver = TemplateResolver(repository_root)
        self.pattern_resolver = PatternResolver()
        self.content_validator = ContentValidator(min_lines=min_lines, strict=strict_validation)
        self.output_normalizer = OutputNormalizer()
        self.repository_writer = RepositoryWriter(repository_root)
        self.conflict_detector = BlockingConflictDetector(repository_root)

        # Store invocation engine for LLM generation
        global _InvocationEngine
        _InvocationEngine = invocation_engine
        self._invocation_engine = invocation_engine

    def generate(self, plan: ArtifactExecutionPlan) -> GenerationReport:
        """Generate all artifacts from an ArtifactExecutionPlan.

        This is the main entry point for E3.1 generation.

        Args:
            plan: ArtifactExecutionPlan from E2.3

        Returns:
            GenerationReport with results for all artifacts

        Raises:
            BlockingConflictError: If blocking conflicts prevent execution
            CodeGenerationError: If generation fails
        """
        start_time = time.time()
        generation_started = datetime.now(timezone.utc).isoformat()

        # Step 1: Validate plan
        if not self._validate_plan(plan):
            raise CodeGenerationError("Invalid ArtifactExecutionPlan")

        # Step 2: Detect blocking conflicts
        conflict_report = self.conflict_detector.detect_conflicts(plan.execution_units)
        if not conflict_report.can_proceed:
            raise BlockingConflictError(
                f"Blocking conflicts detected: {[c.description for c in conflict_report.conflicts]}"
            )

        # Step 3: Initialize context builder
        context_builder = GenerationContextBuilder(plan)

        # Track results
        artifact_results: List[GenerationResult] = []
        wave_results: List[WaveGenerationResult] = []

        # Step 4: Execute by waves
        sorted_waves = sorted(plan.execution_waves, key=lambda w: w.wave_number)

        for wave in sorted_waves:
            wave_start = time.time()

            # Get units in this wave
            wave_units = [
                u for u in plan.execution_units
                if u.execution_wave == wave.wave_number
            ]

            # Generate each unit
            wave_successful = 0
            wave_failed = 0
            wave_written = 0

            for unit in wave_units:
                result = self._generate_single(unit, plan, context_builder)

                if result.success:
                    wave_successful += 1
                else:
                    wave_failed += 1

                if result.file_written:
                    wave_written += 1

                artifact_results.append(result)

            wave_duration = (time.time() - wave_start) * 1000

            wave_results.append(WaveGenerationResult(
                wave_number=wave.wave_number,
                wave_name=wave.wave_name,
                total_units=len(wave_units),
                successful=wave_successful,
                failed=wave_failed,
                artifacts_written=wave_written,
                duration_ms=wave_duration,
            ))

        # Step 5: Compute summary
        total_duration = (time.time() - start_time) * 1000
        generation_completed = datetime.now(timezone.utc).isoformat()

        # Count by strategy
        template_count = sum(1 for r in artifact_results if r.strategy == GenerationStrategy.TEMPLATE)
        pattern_count = sum(1 for r in artifact_results if r.strategy == GenerationStrategy.PATTERN)
        llm_count = sum(1 for r in artifact_results if r.strategy == GenerationStrategy.LLM_GENERATED)
        unresolved_count = sum(1 for r in artifact_results if r.strategy == GenerationStrategy.UNRESOLVED)

        # Compute report hash
        report_id = f"genr-{plan.plan_id[:8]}"
        report = GenerationReport(
            report_id=report_id,
            plan_id=plan.plan_id,
            mission_id=plan.mission_id,
            generation_started=generation_started,
            generation_completed=generation_completed,
            total_duration_ms=total_duration,
            total_artifacts=len(plan.execution_units),
            successful_generations=sum(1 for r in artifact_results if r.success),
            failed_generations=sum(1 for r in artifact_results if not r.success),
            files_written=sum(1 for r in artifact_results if r.file_written),
            template_count=template_count,
            pattern_count=pattern_count,
            llm_count=llm_count,
            unresolved_count=unresolved_count,
            waves_executed=len(wave_results),
            wave_results=tuple(wave_results),
            artifact_results=tuple(artifact_results),
            errors=tuple(
                err for r in artifact_results for err in r.errors
            ),
            deterministic=True,
            deterministic_hash="",  # Will be computed
        )

        # Compute hash
        report_hash = compute_generation_report_hash(report)

        # Return with hash
        return GenerationReport(
            report_id=report.report_id,
            plan_id=report.plan_id,
            mission_id=report.mission_id,
            generation_started=report.generation_started,
            generation_completed=report.generation_completed,
            total_duration_ms=report.total_duration_ms,
            total_artifacts=report.total_artifacts,
            successful_generations=report.successful_generations,
            failed_generations=report.failed_generations,
            files_written=report.files_written,
            template_count=report.template_count,
            pattern_count=report.pattern_count,
            llm_count=report.llm_count,
            unresolved_count=report.unresolved_count,
            waves_executed=report.waves_executed,
            wave_results=report.wave_results,
            artifact_results=report.artifact_results,
            errors=report.errors,
            deterministic=report.deterministic,
            deterministic_hash=report_hash,
        )

    def generate_single(
        self,
        unit: ArtifactExecutionUnit,
        plan: ArtifactExecutionPlan,
    ) -> GenerationResult:
        """Generate a single artifact.

        Args:
            unit: Artifact execution unit to generate
            plan: Full artifact execution plan

        Returns:
            GenerationResult for this artifact
        """
        context_builder = GenerationContextBuilder(plan)
        return self._generate_single(unit, plan, context_builder)

    def _generate_single(
        self,
        unit: ArtifactExecutionUnit,
        plan: ArtifactExecutionPlan,
        context_builder: GenerationContextBuilder,
    ) -> GenerationResult:
        """Internal method to generate a single artifact."""
        start_time = time.time()
        generation_started = datetime.now(timezone.utc).isoformat()

        errors: List[str] = []
        warnings: List[str] = []
        content: Optional[str] = None
        validation_passed = False
        file_written = False
        written_path = ""

        # Build generation context
        try:
            context = context_builder.build_context(unit)
        except Exception as e:
            errors.append(f"Context building failed: {e}")
            return self._create_error_result(
                unit, start_time, generation_started, errors, warnings,
                validation_passed, file_written, written_path
            )

        # Generate based on strategy
        try:
            if unit.generation_strategy == GenerationStrategy.TEMPLATE:
                content, _ = self.template_resolver.resolve_and_apply(context, unit)
            elif unit.generation_strategy == GenerationStrategy.PATTERN:
                content, _ = self.pattern_resolver.resolve_and_apply(context, unit)
            elif unit.generation_strategy == GenerationStrategy.LLM_GENERATED:
                content = self._generate_via_llm(context, unit)
            else:  # UNRESOLVED
                errors.append(
                    f"Cannot generate with UNRESOLVED strategy: {unit.strategy_reason}"
                )
        except Exception as e:
            errors.append(f"Generation failed: {e}")

        # Validate content
        if content:
            validation_result = self.content_validator.validate(content, unit)
            validation_passed = validation_result.passed
            if not validation_passed:
                errors.extend(validation_result.errors)
            warnings.extend(validation_result.warnings)

        # Write to repository
        if content and validation_passed:
            try:
                write_result = self.repository_writer.write(content, unit)
                if write_result.success:
                    file_written = True
                    written_path = write_result.target_path
                else:
                    errors.append(f"Write failed: {write_result.error}")
            except Exception as e:
                errors.append(f"Repository write failed: {e}")

        # Compute result
        generation_completed = datetime.now(timezone.utc).isoformat()
        duration_ms = (time.time() - start_time) * 1000

        # Compute hashes
        content_hash = compute_content_hash(content) if content else ""
        context_hash = context.deterministic_hash

        result = GenerationResult(
            result_id=f"gen-{unit.artifact_execution_id}",
            artifact_execution_id=unit.artifact_execution_id,
            artifact_id=unit.artifact_id,
            sub_contract_id=unit.sub_contract_id,
            strategy=unit.generation_strategy,
            generation_started=generation_started,
            generation_completed=generation_completed,
            generation_duration_ms=duration_ms,
            success=len(errors) == 0 and content is not None,
            content=content,
            file_written=file_written,
            written_path=written_path,
            context_hash=context_hash,
            errors=tuple(errors),
            warnings=tuple(warnings),
            validation_passed=validation_passed,
            validation_errors=tuple(errors),
            content_hash=content_hash,
        )

        return result

    def _generate_via_llm(
        self,
        context: GenerationContext,
        unit: ArtifactExecutionUnit,
    ) -> str:
        """Generate content via LLM using existing InvocationEngine.

        Args:
            context: Generation context
            unit: Source artifact execution unit

        Returns:
            Generated content string

        Raises:
            CodeGenerationError: If LLM generation fails
        """
        if self._invocation_engine is None:
            raise CodeGenerationError(
                "InvocationEngine not provided - cannot perform LLM generation"
            )

        # Build generation request
        request_constructor = GenerationRequestConstructor()
        generation_request = request_constructor.construct(context)

        # Convert to InvocationRequest
        invocation_request = request_constructor.to_invocation_request(generation_request)

        # Select model with CODING capability
        selection = SelectionRequest(
            capabilities=frozenset([Capability.CODING]),
            local_preference=False,
        )

        # Invoke
        response = self._invocation_engine.invoke(
            request=invocation_request,
            selection=selection,
        )

        # Extract content from response
        if hasattr(response, 'content') and response.content:
            raw_content = response.content
        elif hasattr(response, 'text') and response.text:
            raw_content = response.text
        elif hasattr(response, 'message') and response.message:
            raw_content = response.message.content if hasattr(response.message, 'content') else str(response.message)
        else:
            raw_content = str(response)

        # Normalize output
        normalized_content = self.output_normalizer.normalize(
            raw_content,
            expected_language=context.language,
        )

        if not normalized_content:
            raise CodeGenerationError("LLM returned empty content")

        return normalized_content

    def _validate_plan(self, plan: ArtifactExecutionPlan) -> bool:
        """Validate the artifact execution plan."""
        if not plan.execution_units:
            return False

        if not plan.mission_id:
            return False

        return True

    def _create_error_result(
        self,
        unit: ArtifactExecutionUnit,
        start_time: float,
        generation_started: str,
        errors: List[str],
        warnings: List[str],
        validation_passed: bool,
        file_written: bool,
        written_path: str,
    ) -> GenerationResult:
        """Create a GenerationResult for a failed generation."""
        generation_completed = datetime.now(timezone.utc).isoformat()
        duration_ms = (time.time() - start_time) * 1000

        return GenerationResult(
            result_id=f"gen-{unit.artifact_execution_id}",
            artifact_execution_id=unit.artifact_execution_id,
            artifact_id=unit.artifact_id,
            sub_contract_id=unit.sub_contract_id,
            strategy=unit.generation_strategy,
            generation_started=generation_started,
            generation_completed=generation_completed,
            generation_duration_ms=duration_ms,
            success=False,
            content=None,
            file_written=file_written,
            written_path=written_path,
            context_hash="",
            errors=tuple(errors),
            warnings=tuple(warnings),
            validation_passed=validation_passed,
            validation_errors=tuple(errors),
            content_hash="",
        )


def get_invocation_engine() -> Optional[InvocationEngine]:
    """Get the stored invocation engine instance."""
    global _InvocationEngine
    return _InvocationEngine


def set_invocation_engine(engine: InvocationEngine) -> None:
    """Set the invocation engine instance for LLM generation."""
    global _InvocationEngine
    _InvocationEngine = engine
