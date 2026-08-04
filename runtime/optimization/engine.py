from .context_optimizer import optimize_context
from .models import OptimizationPlan, OptimizationReport, OptimizationRequest, OptimizationResult, OptimizedContextEnvelope
from .plugins import PluginRegistry
from .report import measurements
from .validators import validate


class OptimizationEngine:
    def __init__(self): self.plugins=PluginRegistry(); self.plugins.discover()
    def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        source=request.source; actions=[]; removed=[]
        if isinstance(source,dict): payload,actions,removed=optimize_context(source,request.protected,request.budget)
        else: payload=source
        valid=validate(source,payload,request.protected) if isinstance(source,dict) else True
        report=OptimizationReport(request_id=request.metadata.get("request_id","optimization:1"),actions=tuple(actions),removed=tuple(removed),preserved=tuple(request.protected),measurements=measurements(source,payload),validated=valid)
        envelope=OptimizedContextEnvelope(request_id=report.request_id,payload=payload,provenance=tuple(request.metadata.get("provenance",())),report=report)
        return OptimizationResult(envelope=envelope,report=report)
    def plan(self, request: OptimizationRequest) -> OptimizationPlan:
        return OptimizationPlan(request_id=request.metadata.get("request_id","optimization:1"),modules=request.modules or ("context",),plugins=("native",),budget=request.budget)
