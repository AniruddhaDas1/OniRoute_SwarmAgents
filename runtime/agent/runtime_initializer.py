"""Deterministic Runtime Initializer for OniRoute Agent Runtime (ACR-006 Phase R2).

Establishes a RuntimeContext from a sealed ExecutionBlueprint. Read-only.
No AI invocation, no task execution, no scheduling.
"""

from __future__ import annotations

from datetime import datetime, timezone

from runtime.organization.blueprint import ExecutionBlueprint

from .contracts import RuntimeInitializerContract
from .models import RuntimeContext


class RuntimeInitializer(RuntimeInitializerContract):
    """Concrete RuntimeInitializer. Reads a sealed ExecutionBlueprint and
    produces an immutable RuntimeContext."""

    def initialize_runtime(self, blueprint: ExecutionBlueprint) -> RuntimeContext:
        """Establish runtime context from a sealed ExecutionBlueprint."""
        mission = blueprint.mission
        org = blueprint.organization

        # Consolidate runtime constraints from blueprint execution_constraints
        runtime_constraints: dict = {}
        if blueprint.execution_constraints:
            for cst in blueprint.execution_constraints:
                runtime_constraints[cst.get("constraint_id", "unknown")] = cst

        context_id = f"ctx-{blueprint.blueprint_id}"
        return RuntimeContext(
            context_id=context_id,
            blueprint_id=blueprint.blueprint_id,
            mission_id=mission.mission_id,
            organization_id=org.organization_id,
            workspace_root=str(mission.context.workspace_root),
            engine_root=str(mission.context.engine_root),
            active_session_ids=[],
            runtime_constraints=runtime_constraints,
            metadata={
                "total_members": len(org.members),
                "total_capabilities": len(blueprint.capabilities.capabilities),
                "swarm_graph_id": blueprint.dependencies.graph_id,
            },
            initialized_at=datetime.now(timezone.utc).isoformat(),
        )
