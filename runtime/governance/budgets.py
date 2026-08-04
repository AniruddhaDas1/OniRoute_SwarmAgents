from pydantic import BaseModel

from .exceptions import BudgetExceededError

class BudgetLimits(BaseModel):invocations:int=100;estimated_tokens:int=100000;tool_invocations:int=100;runtime_ms:int=3600000
class BudgetTracker:
    def __init__(self,limits:BudgetLimits):self.limits=limits;self.invocations=0;self.estimated_tokens=0;self.tool_invocations=0;self.runtime_ms=0
    def check(self,kind:str,tokens:int=0,runtime_ms:int=0)->None:
        if self.invocations+(kind=="model")>self.limits.invocations or self.estimated_tokens+tokens>self.limits.estimated_tokens or self.tool_invocations+(kind=="tool")>self.limits.tool_invocations or self.runtime_ms+runtime_ms>self.limits.runtime_ms:raise BudgetExceededError("Session budget exceeded")
    def record(self,kind:str,tokens:int=0,runtime_ms:int=0)->None:self.invocations+=kind=="model";self.tool_invocations+=kind=="tool";self.estimated_tokens+=tokens;self.runtime_ms+=runtime_ms
    def snapshot(self):return {"invocations":self.invocations,"estimated_tokens":self.estimated_tokens,"tool_invocations":self.tool_invocations,"runtime_ms":self.runtime_ms}
