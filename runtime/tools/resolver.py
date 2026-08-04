from .registry import ToolRegistry


class ToolResolver:
    def __init__(self,registry:ToolRegistry):self.registry=registry
    def find_tool(self,identifier:str):return self.registry.tools.get(self.registry.aliases.get(identifier,identifier))
    def find_mcp(self,identifier:str):return self.registry.mcp_servers.get(identifier)
    def find_capability(self,identifier:str):return self.registry.capabilities.get(identifier)
