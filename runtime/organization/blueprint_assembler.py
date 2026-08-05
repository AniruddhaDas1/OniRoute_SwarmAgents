"""Deterministic Execution Blueprint Assembler for OniRoute Organization Builder (ACR-005 Phase S4).

Transforms an ExecutionRequest, validated CapabilityReport, Organization, and SwarmGraph
into a sealed, immutable ExecutionBlueprint ready for future Agent Runtime handoff.

Contains NO runtime execution steps, NO task scheduler, and NO AI model calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.mission.models import ExecutionRequest

from .blueprint import ExecutionBlueprint, ExecutionReadiness
from .blueprint_validator import BlueprintValidator
from .capability import CapabilityReport
from .capability_resolver import CapabilityResolver
from .contracts import ExecutionBlueprintBuilderContract
from .models import Organization
from .organization_assembler import OrganizationAssembler
from .swarm_graph import SwarmGraph
from .swarm_graph_builder import SwarmGraphBuilder


class ExecutionBlueprintAssembler(ExecutionBlueprintBuilderContract):
    """Deterministic Execution Blueprint Assembler engine."""

    def __init__(self, repository_root: Path | str | None = None) -> None:
        self.repository_root = Path(repository_root).resolve() if repository_root else Path.cwd()

    def create_blueprint(
        self,
        execution_request: ExecutionRequest,
        organization: Organization,
        capability_report: CapabilityReport,
        swarm_graph: SwarmGraph,
    ) -> ExecutionBlueprint:
        """Consolidate pipeline outputs into an immutable ExecutionBlueprint."""
        mission = execution_request.mission
        blueprint_id = f"blp-{mission.mission_id}"

        # Consolidate execution dependencies
        exec_deps: list[dict[str, Any]] = [
            {
                "dependency_id": dep.dependency_id,
                "source_member_id": dep.source_member_id,
                "target_member_id": dep.target_member_id,
                "dependency_type": dep.dependency_type.value,
                "description": dep.description,
            }
            for dep in organization.dependencies
        ]

        # Consolidate execution constraints
        exec_constraints: list[dict[str, Any]] = [
            {
                "constraint_id": cst.constraint_id,
                "capability_id": cst.capability_id,
                "local_only": cst.local_only,
                "allowed_providers": cst.allowed_providers,
                "max_duration_seconds": cst.max_duration_seconds,
            }
            for cst in capability_report.capability_constraints
        ]

        # Consolidate evidence logs
        consolidated_evidence: list[dict[str, Any]] = []
        for ev_cap in capability_report.evidence:
            consolidated_evidence.append(ev_cap.model_dump(mode="python"))
        for ev_org in organization.evidence:
            consolidated_evidence.append(ev_org.model_dump(mode="python"))

        blueprint_unvalidated = ExecutionBlueprint(
            blueprint_id=blueprint_id,
            organization=organization,
            mission=mission,
            execution_request=execution_request,
            capabilities=capability_report,
            dependencies=swarm_graph,
            department_structure=organization.departments,
            reporting_hierarchy=organization.hierarchy.model_dump(mode="python"),
            execution_dependencies=exec_deps,
            execution_constraints=exec_constraints,
            evidence=consolidated_evidence,
            execution_metadata={
                "workspace_root": str(mission.context.workspace_root),
                "engine_root": str(mission.context.engine_root),
                "intent_category": mission.requirements.intent_category,
                "total_members": len(organization.members),
                "total_capabilities": len(capability_report.capabilities),
            },
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Validate blueprint & readiness
        validator = BlueprintValidator()
        readiness, val_report = validator.validate_blueprint(blueprint_unvalidated)

        blueprint_unvalidated.readiness = readiness
        blueprint_unvalidated.validation_report = val_report

        return blueprint_unvalidated

    def assemble_blueprint(
        self, execution_request: ExecutionRequest, repository_root: Path | str | None = None
    ) -> ExecutionBlueprint:
        """End-to-end assembly pipeline: ExecutionRequest -> CapabilityReport -> Organization -> SwarmGraph -> ExecutionBlueprint."""
        root = Path(repository_root).resolve() if repository_root else self.repository_root

        # 1. Capability Resolution
        cap_resolver = CapabilityResolver(repository_root=root)
        capability_report = cap_resolver.resolve_capabilities(execution_request)

        # 2. Organization Assembly
        org_assembler = OrganizationAssembler(repository_root=root)
        organization = org_assembler.assemble_organization(
            capability_report, mission_id=execution_request.mission.mission_id
        )

        # 3. Swarm Graph Construction
        sg_builder = SwarmGraphBuilder()
        swarm_graph = sg_builder.build_swarm_graph(organization)

        # 4. Blueprint Assembly & Sealing
        return self.create_blueprint(execution_request, organization, capability_report, swarm_graph)
