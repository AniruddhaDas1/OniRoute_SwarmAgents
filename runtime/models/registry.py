from .capabilities import Capability
from .models import ModelRecord, ProtocolRecord, ProviderRecord


class ModelRegistry:
    def __init__(self):
        self.models:dict[str,ModelRecord]={}; self.providers:dict[str,ProviderRecord]={}; self.protocols:dict[str,ProtocolRecord]={}; self.capabilities={item.value:item for item in Capability}; self.aliases:dict[str,str]={}
    def add_model(self, model:ModelRecord)->None:
        self.models[model.id]=model
        for alias in model.aliases:self.aliases[alias]=model.id
    def add_provider(self, provider:ProviderRecord)->None:self.providers[provider.id]=provider
    def add_protocol(self, protocol:ProtocolRecord)->None:self.protocols[protocol.id]=protocol
