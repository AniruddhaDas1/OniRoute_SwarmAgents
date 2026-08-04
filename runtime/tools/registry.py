from .capabilities import ToolCapability
from .models import MCPServerRecord, ToolProtocol, ToolRecord


class ToolRegistry:
    def __init__(self):
        self.tools:dict[str,ToolRecord]={};self.local_tools:dict[str,ToolRecord]={};self.mcp_servers:dict[str,MCPServerRecord]={};self.protocols={item.value:item for item in ToolProtocol};self.capabilities={item.value:item for item in ToolCapability};self.aliases:dict[str,str]={}
    def add_tool(self,item:ToolRecord)->None:
        self.tools[item.id]=item
        if item.local:self.local_tools[item.id]=item
        for alias in item.aliases:self.aliases[alias]=item.id
    def add_mcp(self,item:MCPServerRecord)->None:self.mcp_servers[item.id]=item
