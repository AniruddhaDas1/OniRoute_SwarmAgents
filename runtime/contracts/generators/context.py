"""E3.1 Generation Context Builder and Generation Request Constructor.

Provides:
1. GenerationContextBuilder: Builds GenerationContext from ArtifactExecutionUnit
2. GenerationRequestConstructor: Constructs InvocationRequest for LLM generation
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from runtime.contracts.e23_models import (
    ArtifactExecutionPlan,
    ArtifactExecutionUnit,
    ArtifactExecutionWave,
    GenerationStrategy,
    OverwritePolicy,
    PathType,
)
from runtime.contracts.e31_models import (
    GenerationContext,
    GenerationContextError,
    GenerationRequest,
    compute_generation_context_hash,
    compute_generation_request_hash,
    normalize_target_path,
)


# Default objective values for when upstream data is missing
DEFAULT_PROJECT_OBJECTIVE = "Multi-discipline software project"
DEFAULT_ARTIFACT_OBJECTIVE = "Implementation artifact"
DEFAULT_CONTRACT_OBJECTIVE = "Engineering contract"
DEFAULT_SUBCONTRACT_OBJECTIVE = "Sub-contract deliverable"


class GenerationContextBuilder:
    """Builds GenerationContext from ArtifactExecutionUnit.

    Provides deterministic context construction with full traceability
    to upstream artifacts from the mission down to individual sub-contracts.
    """

    def __init__(self, plan: ArtifactExecutionPlan):
        """Initialize the context builder.

        Args:
            plan: The artifact execution plan containing all units
        """
        self.plan = plan
        self._unit_map: Dict[str, ArtifactExecutionUnit] = {
            u.artifact_execution_id: u for u in plan.execution_units
        }
        self._wave_map: Dict[int, ArtifactExecutionWave] = {
            w.wave_number: w for w in plan.execution_waves
        }

    def build_context(
        self,
        unit: ArtifactExecutionUnit,
        project_objective: Optional[str] = None,
        parent_contract_objective: Optional[str] = None,
        sub_contract_objective: Optional[str] = None,
    ) -> GenerationContext:
        """Build GenerationContext from ArtifactExecutionUnit.

        Args:
            unit: Artifact execution unit to build context for
            project_objective: Optional project objective (from mission)
            parent_contract_objective: Optional parent contract objective
            sub_contract_objective: Optional sub-contract objective

        Returns:
            GenerationContext with all necessary information for generation

        Raises:
            GenerationContextError: If context cannot be built
        """
        # Validate unit is in plan
        if unit.artifact_execution_id not in self._unit_map:
            raise GenerationContextError(
                f"Unit {unit.artifact_execution_id} not found in plan"
            )

        # Resolve objectives from traceability if not provided
        trace = self.plan.traceability
        resolved_project_objective = project_objective or trace.get(
            "project_objective", DEFAULT_PROJECT_OBJECTIVE
        )
        resolved_parent_objective = parent_contract_objective or trace.get(
            "parent_contract_objective", DEFAULT_CONTRACT_OBJECTIVE
        )
        resolved_subcontract_objective = sub_contract_objective or trace.get(
            "sub_contract_objective", DEFAULT_SUBCONTRACT_OBJECTIVE
        )

        # Build artifact objective from unit data
        artifact_objective = self._build_artifact_objective(unit)

        # Normalize target path
        normalized_path = normalize_target_path(unit.target_path)

        # Build traceability map
        traceability = self._build_traceability(unit)

        # Compute deterministic hash
        temp_context = GenerationContext(
            artifact_execution_id=unit.artifact_execution_id,
            mission_id=self.plan.mission_id,
            project_objective=resolved_project_objective,
            artifact_objective=artifact_objective,
            artifact_type=unit.artifact_type,
            parent_contract_objective=resolved_parent_objective,
            sub_contract_objective=resolved_subcontract_objective,
            repository_scope=unit.repository_scope,
            target_path=normalized_path,
            path_type=unit.path_type,
            overwrite_policy=unit.overwrite_policy,
            language=unit.language,
            framework=unit.framework,
            file_format=unit.file_format,
            technology_context=tuple(unit.technology_context),
            generation_strategy=unit.generation_strategy,
            generation_priority=unit.generation_priority,
            dependencies=tuple(unit.dependencies),
            required_inputs=tuple(str(inp.source_artifact_id) for inp in unit.required_inputs),
            agent_profile_id=unit.agent_profile_id,
            skill_bundle_id=unit.skill_bundle_id,
            validation_checkpoints=tuple(unit.validation_checkpoints),
            acceptance_criteria_ids=tuple(unit.acceptance_criteria_ids),
            expected_outputs=(),  # To be populated from traceability if needed
            traceability=traceability,
            deterministic_hash="",  # Will be computed
        )

        # Compute and set deterministic hash
        context_hash = compute_generation_context_hash(temp_context)

        # Create final context with hash
        return GenerationContext(
            artifact_execution_id=temp_context.artifact_execution_id,
            mission_id=temp_context.mission_id,
            project_objective=temp_context.project_objective,
            artifact_objective=temp_context.artifact_objective,
            artifact_type=temp_context.artifact_type,
            parent_contract_objective=temp_context.parent_contract_objective,
            sub_contract_objective=temp_context.sub_contract_objective,
            repository_scope=temp_context.repository_scope,
            target_path=temp_context.target_path,
            path_type=temp_context.path_type,
            overwrite_policy=temp_context.overwrite_policy,
            language=temp_context.language,
            framework=temp_context.framework,
            file_format=temp_context.file_format,
            technology_context=temp_context.technology_context,
            generation_strategy=temp_context.generation_strategy,
            generation_priority=temp_context.generation_priority,
            dependencies=temp_context.dependencies,
            required_inputs=temp_context.required_inputs,
            agent_profile_id=temp_context.agent_profile_id,
            skill_bundle_id=temp_context.skill_bundle_id,
            validation_checkpoints=temp_context.validation_checkpoints,
            acceptance_criteria_ids=temp_context.acceptance_criteria_ids,
            expected_outputs=temp_context.expected_outputs,
            traceability=temp_context.traceability,
            deterministic_hash=context_hash,
        )

    def _build_artifact_objective(self, unit: ArtifactExecutionUnit) -> str:
        """Build artifact objective from unit data."""
        parts = [
            unit.artifact_type.title(),
            "artifact",
        ]

        if unit.language:
            parts.append(f"in {unit.language}")
        if unit.framework:
            parts.append(f"using {unit.framework}")
        if unit.artifact_execution_id:
            # Extract meaningful part from ID
            parts.append(f"({unit.artifact_execution_id})")

        return " ".join(parts)

    def _build_traceability(self, unit: ArtifactExecutionUnit) -> Dict[str, str]:
        """Build traceability map for context."""
        trace = dict(self.plan.traceability)
        trace.update({
            "artifact_execution_id": unit.artifact_execution_id,
            "artifact_id": unit.artifact_id,
            "sub_contract_id": unit.sub_contract_id,
            "parent_contract_id": unit.parent_contract_id,
            "plan_id": self.plan.plan_id,
            "wave": str(unit.execution_wave),
        })
        return trace

    def get_wave_context(
        self,
        wave_number: int,
    ) -> Optional[ArtifactExecutionWave]:
        """Get wave context for a specific wave number."""
        return self._wave_map.get(wave_number)

    def get_units_in_wave(
        self,
        wave_number: int,
    ) -> List[ArtifactExecutionUnit]:
        """Get all artifact execution units in a specific wave."""
        return [
            u for u in self.plan.execution_units
            if u.execution_wave == wave_number
        ]

    def get_units_by_strategy(
        self,
        strategy: GenerationStrategy,
    ) -> List[ArtifactExecutionUnit]:
        """Get all artifact execution units with a specific strategy."""
        return [
            u for u in self.plan.execution_units
            if u.generation_strategy == strategy
        ]


class GenerationRequestConstructor:
    """Constructs InvocationRequest for LLM-based artifact generation.

    Uses GenerationContext to build a complete request with enough
    information to produce the actual artifact.
    """

    def __init__(self, include_related_artifacts: bool = True):
        """Initialize the request constructor.

        Args:
            include_related_artifacts: If True, include context about related artifacts
        """
        self._counter = 0
        self._include_related = include_related_artifacts

    def construct(
        self,
        context: GenerationContext,
        related_units: Optional[List["ArtifactExecutionUnit"]] = None,
        skill_bundle_id: Optional[str] = None,
        agent_profile_id: Optional[str] = None,
    ) -> GenerationRequest:
        """Construct a generation request from context.

        Args:
            context: Generation context with all artifact information
            related_units: Optional list of related artifact execution units for context
            skill_bundle_id: Optional skill bundle ID for specialized generation
            agent_profile_id: Optional agent profile ID

        Returns:
            GenerationRequest ready for InvocationEngine
        """
        self._counter += 1
        request_id = f"genreq-{context.artifact_execution_id}-{self._counter:03d}"

        # Build system prompt
        system_prompt = self._build_system_prompt(context)

        # Build user prompt with enhanced context
        user_prompt = self._build_user_prompt(context, related_units)

        # Build generation constraints
        constraints = self._build_constraints(context, skill_bundle_id, agent_profile_id)

        # Create request
        request = GenerationRequest(
            request_id=request_id,
            artifact_execution_id=context.artifact_execution_id,
            mission_id=context.mission_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            language=context.language,
            framework=context.framework,
            file_format=context.file_format,
            expected_outputs=tuple(context.expected_outputs) if context.expected_outputs else (),
            generation_constraints=constraints,
            deterministic_hash="",  # Will be computed
        )

        # Compute hash
        request_hash = compute_generation_request_hash(request)

        # Return with hash
        return GenerationRequest(
            request_id=request.request_id,
            artifact_execution_id=request.artifact_execution_id,
            mission_id=request.mission_id,
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            language=request.language,
            framework=request.framework,
            file_format=request.file_format,
            expected_outputs=request.expected_outputs,
            generation_constraints=request.generation_constraints,
            deterministic_hash=request_hash,
        )

    def _build_system_prompt(self, context: GenerationContext) -> str:
        """Build system prompt for generation."""
        prompt_parts = [
            "You are an expert software engineer generating production-ready code artifacts.",
            "",
            f"You are generating a {context.artifact_type} artifact for a {context.project_objective}.",
            "",
            "IMPORTANT GUIDELINES:",
            "1. Produce ONLY complete, working source code",
            "2. Do NOT include markdown code blocks (```), explanations, or documentation",
            "3. Do NOT use placeholder comments like TODO, FIXME, PLACEHOLDER, or INSERT_CODE_HERE",
            "4. Do NOT use empty stubs or skeleton code",
            "5. The output must be syntactically correct and immediately usable",
            "6. Follow language and framework best practices",
            "",
        ]

        # Add technology context
        if context.language:
            prompt_parts.append(f"Target Language: {context.language}")
        if context.framework:
            prompt_parts.append(f"Framework: {context.framework}")
        if context.technology_context:
            prompt_parts.append(f"Tech Stack: {', '.join(context.technology_context)}")

        prompt_parts.extend([
            "",
            "OUTPUT FORMAT:",
            "Return ONLY the raw source code file content.",
            "Start with the first line of actual code.",
            "End with the last line of actual code.",
        ])

        return "\n".join(prompt_parts)

    def _build_user_prompt(
        self,
        context: GenerationContext,
        related_units: Optional[List["ArtifactExecutionUnit"]] = None,
    ) -> str:
        """Build user prompt with artifact specifics and related context."""
        prompt_parts = [
            f"## Mission",
            context.project_objective,
            "",
            f"## Artifact to Generate",
            f"Type: {context.artifact_type}",
            f"Target: {context.target_path}",
        ]

        if context.language:
            prompt_parts.append(f"Language: {context.language}")
        if context.framework:
            prompt_parts.append(f"Framework: {context.framework}")
        if context.file_format:
            prompt_parts.append(f"Format: {context.file_format}")

        prompt_parts.extend([
            "",
            f"## Objective",
            context.artifact_objective,
            "",
        ])

        # Add contract context
        if context.parent_contract_objective and context.parent_contract_objective != DEFAULT_CONTRACT_OBJECTIVE:
            prompt_parts.extend([
                f"## Contract Context",
                f"Parent: {context.parent_contract_objective}",
            ])
            if context.sub_contract_objective and context.sub_contract_objective != DEFAULT_SUBCONTRACT_OBJECTIVE:
                prompt_parts.append(f"Sub-Contract: {context.sub_contract_objective}")
            prompt_parts.append("")

        # Add expected outputs if available
        if context.expected_outputs:
            prompt_parts.extend([
                f"## Required Outputs",
                "This artifact must produce/provide:",
            ])
            for output in context.expected_outputs:
                prompt_parts.append(f"- {output}")
            prompt_parts.append("")

        # Add dependencies
        if context.required_inputs:
            prompt_parts.extend([
                f"## Dependencies",
                "This artifact will receive inputs from:",
            ])
            for inp in context.required_inputs:
                prompt_parts.append(f"- {inp}")
            prompt_parts.append("")

        # Add related artifacts for coherence
        if related_units and self._include_related:
            prompt_parts.extend([
                f"## Related Artifacts",
                "This project includes the following related files (for consistency):",
            ])
            for unit in related_units[:10]:  # Limit to avoid token explosion
                if unit.artifact_execution_id != context.artifact_execution_id:
                    rel_info = f"- {unit.target_path} ({unit.artifact_type}"
                    if unit.language:
                        rel_info += f", {unit.language}"
                    if unit.framework:
                        rel_info += f", {unit.framework}"
                    rel_info += ")"
                    prompt_parts.append(rel_info)
            prompt_parts.append("")

        # Add validation requirements
        if context.validation_checkpoints:
            prompt_parts.extend([
                f"## Quality Requirements",
                "Generated code must:",
            ])
            for cp in context.validation_checkpoints:
                prompt_parts.append(f"- {cp.description}")
            prompt_parts.append("")

        # Add generation priority context
        if context.generation_priority:
            priority_context = {
                "CRITICAL": "This is a critical artifact - code must be complete and correct.",
                "HIGH": "This is a high-priority artifact - code must be production-ready.",
                "MEDIUM": "This is a medium-priority artifact.",
                "LOW": "This is a low-priority artifact.",
            }.get(context.generation_priority, "")
            if priority_context:
                prompt_parts.extend(["", priority_context])

        prompt_parts.extend([
            "",
            f"## Task",
            "",
            f"Generate the complete source code for: {context.target_path}",
            "",
            "Return ONLY the raw file content - no markdown, no explanations.",
            "",
        ])

        return "\n".join(prompt_parts)

    def _build_constraints(
        self,
        context: GenerationContext,
        skill_bundle_id: Optional[str],
        agent_profile_id: Optional[str],
    ) -> Dict[str, Any]:
        """Build generation constraints."""
        return {
            "target_path": context.target_path,
            "file_format": context.file_format,
            "language": context.language,
            "framework": context.framework,
            "artifact_type": context.artifact_type,
            "overwrite_policy": context.overwrite_policy.value,
            "generation_priority": context.generation_priority,
            "skill_bundle_id": skill_bundle_id or context.skill_bundle_id,
            "agent_profile_id": agent_profile_id or context.agent_profile_id,
            "execution_wave": 0,  # Will be set by engine
            "mission_id": context.mission_id,
            "project_objective": context.project_objective,
            "artifact_objective": context.artifact_objective,
            "path_type": context.path_type.value if hasattr(context.path_type, 'value') else str(context.path_type),
            "technology_context": list(context.technology_context),
        }

    def to_invocation_request(
        self,
        generation_request: GenerationRequest,
    ):
        """Convert GenerationRequest to InvocationRequest for InvocationEngine.

        Args:
            generation_request: GenerationRequest to convert

        Returns:
            InvocationRequest for InvocationEngine.invoke()
        """
        from runtime.invocation.models import Message
        from runtime.models import Capability

        # Build messages
        messages = [
            Message(role="system", content=generation_request.system_prompt),
            Message(role="user", content=generation_request.user_prompt),
        ]

        # Build invocation request using the correct model fields
        return InvocationRequest(
            messages=tuple(messages),
            capabilities=frozenset([Capability.CODING]),
            metadata={
                "artifact_execution_id": generation_request.artifact_execution_id,
                "request_id": generation_request.request_id,
                "mission_id": generation_request.mission_id,
                "language": generation_request.language,
                "framework": generation_request.framework,
                "generation_constraints": generation_request.generation_constraints,
            },
        )


# Import InvocationRequest at module level to avoid circular import
from runtime.invocation.request import InvocationRequest
