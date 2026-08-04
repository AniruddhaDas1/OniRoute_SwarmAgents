class ApprovalEngine:
    def __init__(self,default:str="Automatic",overrides:dict|None=None):self.default=default;self.overrides=overrides or {}
    def policy_for(self,request)->str:return self.overrides.get(request.tool) or self.overrides.get(request.skill) or self.overrides.get(request.agent) or self.overrides.get(request.workflow) or self.default
