from .models import ExecutionPlan, ExecutionStep, GeneratedArtifact


class ArtifactGenerator:
    TYPES = ("Execution Report", "Validation Report", "Repository Snapshot", "Workflow Summary", "Artifact Manifest", "Decision Log")

    def generate(self, execution_id: str, plan: ExecutionPlan, steps: list[ExecutionStep], statistics: dict[str, int]) -> tuple[GeneratedArtifact, ...]:
        contents = (
            {"execution_id": execution_id, "status": "Completed", "steps": len(steps)},
            {"valid": True, "completed_steps": sum(s.status == "Completed" for s in steps)},
            {"statistics": statistics},
            {"workflow_id": plan.workflow_id, "plan_id": plan.plan_id},
            {"declared_artifacts": sorted({a for step in steps for a in step.artifacts})},
            {"decisions": [], "note": "No runtime decisions were made."},
        )
        return tuple(GeneratedArtifact(id=f"{execution_id}:artifact:{i}", type=kind, workflow_id=plan.workflow_id, content=content) for i, (kind, content) in enumerate(zip(self.TYPES, contents), 1))
