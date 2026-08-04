from __future__ import annotations

from datetime import datetime, timezone

from runtime.context.builder import ContextBuilder
from runtime.context.router import ContextRouter
from runtime.core_models import RepositoryRegistry
from runtime.resolver import Resolver

from .models import ExecutionPlan, ExecutionStep


class ExecutionPlanner:
    def __init__(self, registry: RepositoryRegistry):
        self.registry = registry; self.resolver = Resolver(registry); self.contexts = ContextBuilder(registry)

    def plan(self, workflow_id: str) -> ExecutionPlan:
        workflow = self.resolver.find_workflow(workflow_id)
        if not workflow: raise KeyError(workflow_id)
        context = self.contexts.workflow(workflow_id); route = ContextRouter(self.resolver).plan(workflow_id); data = workflow.data
        steps: list[ExecutionStep] = []
        descriptions = ("Load and resolve Workflow metadata", "Resolve declared participants and Skills", "Prepare immutable Workflow context", "Process deterministic orchestration placeholder", "Generate deterministic artifacts and report")
        for order, description in enumerate(descriptions, 1):
            steps.append(ExecutionStep(id=f"{workflow_id}:step:{order}", description=description, workflow=workflow_id, agent=str(data.get("entry_agent")) if order in (2, 4) else None, skill=str(data.get("compatible_skills", [None])[0]) if order == 4 and data.get("compatible_skills") else None, context=context.context_id, inputs=tuple(map(str, data.get("required_inputs", []))), outputs=tuple(map(str, data.get("expected_outputs", []))), dependencies=() if order == 1 else (f"{workflow_id}:step:{order-1}",), artifacts=tuple(map(str, data.get("produced_artifacts", []))) if order == 5 else (), execution_order=order))
        return ExecutionPlan(plan_id=f"plan:{workflow_id}:v1", workflow_id=workflow_id, steps=tuple(steps), created_at=datetime(1970, 1, 1, tzinfo=timezone.utc))
