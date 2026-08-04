from .exceptions import NoCompatibleToolError
from .models import ToolHealth, ToolRecord, ToolSelectionRequest
from .permissions import PermissionPolicy
from .registry import ToolRegistry
from runtime.governance import AuditEngine,BudgetLimits,BudgetTracker,Decision,GovernanceRequest,PolicyEngine


class ToolSelector:
    def __init__(self,registry:ToolRegistry,policy:PermissionPolicy,preferred_local:tuple[str,...]=(),governance:PolicyEngine|None=None):
        self.registry=registry;self.policy=policy;self.preferred_local=preferred_local;self.governance=governance or PolicyEngine({"permission_defaults":[x.value for x in policy.allowed],"approval_defaults":"Automatic","risk_threshold":100},BudgetTracker(BudgetLimits()),AuditEngine())
    def recommend(self,request:ToolSelectionRequest)->ToolRecord:
        candidates=[]
        for tool in self.registry.tools.values():
            if tool.health in (ToolHealth.DISABLED,ToolHealth.UNAVAILABLE,ToolHealth.DEPRECATED):continue
            if not request.capabilities.issubset(tool.capabilities) or not request.permissions.issubset(tool.permissions):continue
            if not self.policy.permits(tool.permissions):continue
            if request.protocol and tool.protocol!=request.protocol:continue
            if request.provider and tool.provider!=request.provider:continue
            trust={"Official":3,"Verified":2,"Community":1}.get(tool.trust,0);health={ToolHealth.HEALTHY:3,ToolHealth.EXPERIMENTAL:1,ToolHealth.UNKNOWN:0}.get(tool.health,-1);preferred=len(self.preferred_local)-self.preferred_local.index(tool.id) if tool.id in self.preferred_local else 0
            candidates.append(((preferred,health,trust,tool.priority,tool.id),tool))
        if not candidates:raise NoCompatibleToolError("No compatible tool metadata found")
        selected=max(candidates,key=lambda item:item[0])[1];decision=self.governance.authorize(GovernanceRequest(kind="tool",tool=selected.id,provider=selected.provider,protocol=selected.protocol.value,capabilities=frozenset(x.value for x in request.capabilities),permissions=frozenset(x.value for x in selected.permissions)))
        if decision.decision!=Decision.ALLOW:raise PermissionError(f"Tool denied: {decision.decision}: {decision.reasons}")
        return selected
