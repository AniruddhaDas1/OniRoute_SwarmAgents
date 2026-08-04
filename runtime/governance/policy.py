from .approvals import ApprovalEngine
from .auditing import AuditEngine
from .budgets import BudgetTracker
from .models import Decision,GovernanceRequest,PolicyResult
from .permissions import GovernancePermissions
from .risk import RiskEngine
from .security import SecurityEngine

class PolicyEngine:
    def __init__(self,config:dict,budgets:BudgetTracker,audit:AuditEngine):
        self.config=config;self.budgets=budgets;self.audit=audit;self.permissions=GovernancePermissions(set(config.get("permission_defaults",[])));self.approvals=ApprovalEngine(config.get("approval_defaults","Automatic"),config.get("approval_overrides"));self.security=SecurityEngine(config.get("security_rules",{}));self.risk=RiskEngine()
    def evaluate(self,request:GovernanceRequest)->PolicyResult:
        reasons=[];allowed_models=set(self.config.get("allowed_models",[]));blocked_models=set(self.config.get("blocked_models",[]));allowed_tools=set(self.config.get("allowed_tools",[]));denied_tools=set(self.config.get("denied_tools",[]))
        if request.model in blocked_models or allowed_models and request.model not in allowed_models:reasons.append("model policy")
        if request.tool in denied_tools or request.tool and allowed_tools and request.tool not in allowed_tools:reasons.append("tool policy")
        if not self.permissions.check(request.permissions):reasons.append("permission policy")
        reasons.extend(f"security:{x}" for x in self.security.violations(request.permissions));risk=self.risk.score(request.permissions)
        if risk>self.config.get("risk_threshold",100):reasons.append("risk threshold")
        try:self.budgets.check(request.kind,request.estimated_tokens,request.estimated_runtime_ms)
        except Exception:reasons.append("budget policy")
        approval=self.approvals.policy_for(request);decision=Decision.DENY if reasons else (Decision.REQUIRE_APPROVAL if approval not in ("Automatic","Approved") else Decision.ALLOW)
        result=PolicyResult(decision=decision,reasons=tuple(reasons),risk_score=risk,approval=approval);self.audit.record(request,result,"Evaluated");return result
    def authorize(self,request:GovernanceRequest)->PolicyResult:
        result=self.evaluate(request)
        if result.decision==Decision.ALLOW:self.budgets.record(request.kind,request.estimated_tokens,request.estimated_runtime_ms)
        return result
