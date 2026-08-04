from runtime.models import ModelManager, SelectionRequest


class InvocationRouter:
    def __init__(self,manager:ModelManager):self.manager=manager
    def route(self,request:SelectionRequest,model_id:str|None=None):
        if model_id:
            model=self.manager.resolver.find_model(model_id)
            if model:return model
        return self.manager.select_best_model(request)
