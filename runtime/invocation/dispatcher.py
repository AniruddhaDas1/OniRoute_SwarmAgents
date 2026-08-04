from .exceptions import AdapterNotFoundError


class InvocationDispatcher:
    def __init__(self):self.adapters={}
    def register(self,protocol:str,adapter)->None:self.adapters[protocol]=adapter
    def dispatch(self,protocol:str):
        if protocol not in self.adapters:raise AdapterNotFoundError(protocol)
        return self.adapters[protocol]
