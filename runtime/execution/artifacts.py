from __future__ import annotations

import json
from typing import Any

from runtime.workspace import ArtifactCategory, ArtifactRouter, WorkspaceMetadata
from .models import ExecutionPlan, ExecutionStep, GeneratedArtifact


class ArtifactGenerator:
    """Deterministic artifact generator with optional workspace persistence.

    When an :class:`ArtifactRouter` and :class:`WorkspaceMetadata` are
    supplied, generated artifacts are also written to ``.oniroute/artifacts/``
    via the router, with every write guarded by engine-safety assertions.
    """

    TYPES = ("Execution Report", "Validation Report", "Repository Snapshot", "Workflow Summary", "Artifact Manifest", "Decision Log")

    def __init__(
        self,
        artifact_router: ArtifactRouter | None = None,
        workspace_metadata: WorkspaceMetadata | None = None,
    ) -> None:
        self._artifact_router = artifact_router
        self._workspace_metadata = workspace_metadata

    def generate(self, execution_id: str, plan: ExecutionPlan, steps: list[ExecutionStep], statistics: dict[str, int]) -> tuple[GeneratedArtifact, ...]:
        contents = (
            {"execution_id": execution_id, "status": "Completed", "steps": len(steps)},
            {"valid": True, "completed_steps": sum(s.status == "Completed" for s in steps)},
            {"statistics": statistics},
            {"workflow_id": plan.workflow_id, "plan_id": plan.plan_id},
            {"declared_artifacts": sorted({a for step in steps for a in step.artifacts})},
            {"decisions": [], "note": "No runtime decisions were made."},
        )
        artifacts = tuple(
            GeneratedArtifact(id=f"{execution_id}:artifact:{i}", type=kind, workflow_id=plan.workflow_id, content=content)
            for i, (kind, content) in enumerate(zip(self.TYPES, contents), 1)
        )

        if self._artifact_router is not None and self._workspace_metadata is not None:
            from runtime.workspace import ExecutionContext

            ctx = ExecutionContext(
                engine_root=self._workspace_metadata.engine_root,
                workspace_root=self._workspace_metadata.workspace_root,
                cwd=self._workspace_metadata.workspace_root,
                workspace_metadata=self._workspace_metadata,
            )
            for artifact in artifacts:
                dest = self._artifact_router.route_artifact(ctx, ArtifactCategory.REPORTS, f"{artifact.id}.json")
                dest.absolute_path.write_text(
                    json.dumps(artifact.model_dump(mode="json"), indent=2, default=str),
                    encoding="utf-8",
                )

        return artifacts
