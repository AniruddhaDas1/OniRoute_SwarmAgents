from runtime.models import ModelManager, SelectionRequest

from .dispatcher import InvocationDispatcher
from .request import InvocationRequest
from .retry import RetryPolicy, with_retry
from .router import InvocationRouter
from runtime.governance import AuditEngine,BudgetLimits,BudgetTracker,Decision,GovernanceRequest,PolicyEngine


class InvocationEngine:
    def __init__(self,manager:ModelManager,dispatcher:InvocationDispatcher,governance:PolicyEngine|None=None):
        self.manager=manager;self.dispatcher=dispatcher;self.router=InvocationRouter(manager)
        self.governance=governance or PolicyEngine({"permission_defaults":[],"approval_defaults":"Automatic","risk_threshold":100},BudgetTracker(BudgetLimits()),AuditEngine())
    def invoke(self,request:InvocationRequest,selection:SelectionRequest,model_id:str|None=None,retry:RetryPolicy|None=None):
        model=self.router.route(selection,model_id);decision=self.governance.authorize(GovernanceRequest(kind="model",model=model.id,provider=model.provider,protocol=model.protocol,capabilities=frozenset(x.value for x in request.capabilities),estimated_tokens=request.max_tokens or 0))
        if decision.decision!=Decision.ALLOW:raise PermissionError(f"Invocation denied: {decision.decision}: {decision.reasons}")
        adapter=self.dispatcher.dispatch(model.protocol)
        response=with_retry(lambda:adapter.invoke(model,request),retry or RetryPolicy())
        return response.model_copy(update={"metadata": {**response.metadata, "model": model.id, "provider": model.provider, "protocol": model.protocol}})
    def stream(self,request:InvocationRequest,selection:SelectionRequest,model_id:str|None=None):
        model=self.router.route(selection,model_id);decision=self.governance.authorize(GovernanceRequest(kind="model",model=model.id,provider=model.provider,protocol=model.protocol,capabilities=frozenset(x.value for x in request.capabilities),estimated_tokens=request.max_tokens or 0))
        if decision.decision!=Decision.ALLOW:raise PermissionError(f"Invocation denied: {decision.decision}")
        return self.dispatcher.dispatch(model.protocol).stream(model,request)
