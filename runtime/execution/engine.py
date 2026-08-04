from __future__ import annotations

from datetime import datetime, timezone

from runtime.core_models import RepositoryRegistry

from .artifacts import ArtifactGenerator
from .events import EventBus
from .executor import DeterministicExecutor
from .history import ExecutionHistory
from .models import ExecutionPlan, ExecutionResult
from .planner import ExecutionPlanner
from .state import ExecutionStatus
from runtime.models import ModelManager
from runtime.invocation.adapters import OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.engine import InvocationEngine
from .ai import AIStepRunner


class WorkflowEngine:
    def __init__(self, registry: RepositoryRegistry):
        self.registry = registry; self.planner = ExecutionPlanner(registry); self.events = EventBus(); self.history = ExecutionHistory(); self.artifacts = ArtifactGenerator(); self._counter = 0; self.ai_runner = None
        config=registry.root / "config/models.yaml"
        if config.exists():
            manager=ModelManager(config); dispatcher=InvocationDispatcher(); endpoint=manager.config.get("endpoint", "http://127.0.0.1:11434"); dispatcher.register("openai-compatible", OpenAICompatibleAdapter(endpoint)); dispatcher.register("ollama", OllamaAdapter(endpoint)); dispatcher.register("local-process", OllamaAdapter(endpoint)); self.ai_runner=AIStepRunner(InvocationEngine(manager, dispatcher), manager.config.get("approval_defaults", "Dry Run"), manager.config.get("optimization",{}))

    def plan(self, workflow_id: str) -> ExecutionPlan: return self.planner.plan(workflow_id)

    def run(self, workflow_id: str, optimize: bool | None = None) -> ExecutionResult:
        self._counter += 1; execution_id = f"execution:{workflow_id}:{self._counter}"; started = datetime.now(timezone.utc); plan = self.plan(workflow_id)
        self.events.emit("WorkflowStarted", execution_id, workflow_id)
        try:
            steps = DeterministicExecutor(self.events, self.ai_runner).execute(execution_id, plan, optimize)
            artifacts = self.artifacts.generate(execution_id, plan, steps, self.registry.statistics())
            for artifact in artifacts: self.events.emit("ArtifactGenerated", execution_id, artifact.id, artifact_type=artifact.type)
            optimization=tuple(step.ai_trace["optimization"] for step in steps if step.ai_trace and step.ai_trace.get("optimization")); completed = datetime.now(timezone.utc); result = ExecutionResult(execution_id=execution_id, workflow_id=workflow_id, status=ExecutionStatus.COMPLETED, plan=plan.model_copy(update={"steps": tuple(steps)}), artifacts=artifacts, started_at=started, completed_at=completed, report={"ai_steps": sum(bool(step.skill) for step in steps),"optimization":optimization}, ai_trace=tuple(step.ai_trace for step in steps if step.ai_trace))
            self.events.emit("WorkflowCompleted", execution_id, workflow_id); self.history.add(result); return result
        except Exception as exc:
            self.events.emit("WorkflowFailed", execution_id, workflow_id, error=str(exc)); raise
