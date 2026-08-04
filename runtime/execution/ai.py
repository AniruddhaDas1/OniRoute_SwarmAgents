from runtime.invocation.engine import InvocationEngine
from runtime.invocation.request import InvocationRequest
from runtime.models import Capability, SelectionRequest
from runtime.optimization.prompt_optimizer import optimize_prompt
from runtime.optimization.report import measurements

class AIStepRunner:
    def __init__(self, invocation: InvocationEngine, approval: str = "Automatic", optimization: dict | None = None): self.invocation=invocation; self.approval=approval; self.optimization=optimization or {}
    def run(self, prompt: str, capabilities: set[Capability], model: str | None = None, optimize: bool | None = None):
        enabled=self.optimization.get("enabled",False) if optimize is None else optimize
        mode=self.optimization.get("mode","Enabled")
        protected=bool(self.optimization.get("protected_prompts",False))
        applied=enabled and mode not in ("Disabled","Dry Run") and not protected
        optimized,actions,_=optimize_prompt(prompt,self.optimization.get("prompt_budget")) if applied else (prompt,[],[])
        measure=measurements(prompt,optimized)
        optimization_trace={"requested":enabled,"applied":applied,"modules":["prompt"] if applied else [],"plugins":["native"] if applied else [],"protected_sections":["prompt"] if protected else [],"estimated_token_reduction":measure.estimated_tokens_before-measure.estimated_tokens_after,"estimated_context_reduction":measure.before_bytes-measure.after_bytes,"latency_overhead_ms":measure.latency_ms,"bypass_reason":None if applied else ("explicit bypass" if optimize is False else "protected prompt" if protected else mode.lower() if enabled else "policy disabled"),"report_reference":"inline:ai_trace.optimization","policy":{"enabled":enabled,"mode":mode},"actions":actions}
        if self.approval != "Automatic": return "AI step not invoked: approval required", {"approval": self.approval, "status": "Skipped", "optimization":optimization_trace}
        response=self.invocation.invoke(InvocationRequest(prompt=optimized, capabilities=frozenset(capabilities)), SelectionRequest(capabilities=frozenset(capabilities)), model_id=model)
        return response.text, {"approval": "Approved", "status": "Completed", "latency_ms": response.latency_ms, "usage": response.usage.model_dump(), "optimization":optimization_trace, **response.metadata}
