from time import perf_counter

from .events import EventBus
from .models import ExecutionPlan, ExecutionStep
from .state import ExecutionStatus


class DeterministicExecutor:
    PLACEHOLDER = "Placeholder: AI execution not yet implemented"

    def __init__(self, events: EventBus): self.events = events

    def execute(self, execution_id: str, plan: ExecutionPlan) -> list[ExecutionStep]:
        executed: list[ExecutionStep] = []
        for original in sorted(plan.steps, key=lambda step: step.execution_order):
            step = original.model_copy(deep=True); started = perf_counter(); step.status = ExecutionStatus.RUNNING
            self.events.emit("StepStarted", execution_id, step.id)
            step.result = self.PLACEHOLDER if step.skill else "Deterministic metadata step completed"
            step.status = ExecutionStatus.COMPLETED; step.duration_ms = round((perf_counter() - started) * 1000, 3)
            self.events.emit("StepCompleted", execution_id, step.id, result=step.result); executed.append(step)
        return executed
