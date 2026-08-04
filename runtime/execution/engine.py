from __future__ import annotations

from datetime import datetime, timezone

from runtime.models import RepositoryRegistry

from .artifacts import ArtifactGenerator
from .events import EventBus
from .executor import DeterministicExecutor
from .history import ExecutionHistory
from .models import ExecutionPlan, ExecutionResult
from .planner import ExecutionPlanner
from .state import ExecutionStatus


class WorkflowEngine:
    def __init__(self, registry: RepositoryRegistry):
        self.registry = registry; self.planner = ExecutionPlanner(registry); self.events = EventBus(); self.history = ExecutionHistory(); self.artifacts = ArtifactGenerator(); self._counter = 0

    def plan(self, workflow_id: str) -> ExecutionPlan: return self.planner.plan(workflow_id)

    def run(self, workflow_id: str) -> ExecutionResult:
        self._counter += 1; execution_id = f"execution:{workflow_id}:{self._counter}"; started = datetime.now(timezone.utc); plan = self.plan(workflow_id)
        self.events.emit("WorkflowStarted", execution_id, workflow_id)
        try:
            steps = DeterministicExecutor(self.events).execute(execution_id, plan)
            artifacts = self.artifacts.generate(execution_id, plan, steps, self.registry.statistics())
            for artifact in artifacts: self.events.emit("ArtifactGenerated", execution_id, artifact.id, artifact_type=artifact.type)
            completed = datetime.now(timezone.utc); result = ExecutionResult(execution_id=execution_id, workflow_id=workflow_id, status=ExecutionStatus.COMPLETED, plan=plan.model_copy(update={"steps": tuple(steps)}), artifacts=artifacts, started_at=started, completed_at=completed, report={"placeholder_steps": sum(bool(step.skill) for step in steps)})
            self.events.emit("WorkflowCompleted", execution_id, workflow_id); self.history.add(result); return result
        except Exception as exc:
            self.events.emit("WorkflowFailed", execution_id, workflow_id, error=str(exc)); raise
