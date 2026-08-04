from runtime.invocation.engine import InvocationEngine
from runtime.invocation.request import InvocationRequest
from runtime.models import Capability, SelectionRequest

class AIStepRunner:
    def __init__(self, invocation: InvocationEngine, approval: str = "Automatic"): self.invocation=invocation; self.approval=approval
    def run(self, prompt: str, capabilities: set[Capability], model: str | None = None):
        if self.approval != "Automatic": return "AI step not invoked: approval required", {"approval": self.approval, "status": "Skipped"}
        response=self.invocation.invoke(InvocationRequest(prompt=prompt, capabilities=frozenset(capabilities)), SelectionRequest(capabilities=frozenset(capabilities)), model_id=model)
        return response.text, {"approval": "Approved", "status": "Completed", "latency_ms": response.latency_ms, "usage": response.usage.model_dump(), **response.metadata}
