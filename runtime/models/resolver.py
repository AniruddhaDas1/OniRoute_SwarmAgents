from .capabilities import Capability
from .registry import ModelRegistry


class ModelResolver:
    def __init__(self,registry:ModelRegistry):self.registry=registry
    def find_model(self,identifier:str):return self.registry.models.get(self.registry.aliases.get(identifier,identifier))
    def find_provider(self,identifier:str):return self.registry.providers.get(identifier)
    def find_capability(self,identifier:str):return self.registry.capabilities.get(identifier)
    def find_protocol(self,identifier:str):return self.registry.protocols.get(identifier)
