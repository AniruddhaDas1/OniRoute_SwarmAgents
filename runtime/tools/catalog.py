from pathlib import Path

import yaml

from .models import MCPServerRecord, ToolRecord
from .registry import ToolRegistry


class ToolCatalog:
    @staticmethod
    def load(path:Path)->ToolRegistry:
        data=yaml.safe_load(path.read_text(encoding="utf-8")) or {};registry=ToolRegistry();disabled=set(data.get("disabled_tools",[]))
        for item in data.get("tools",[]):
            if item.get("id") not in disabled:registry.add_tool(ToolRecord.model_validate(item))
        allowed=set(data.get("allowed_mcp_servers",[]))
        for item in data.get("mcp_servers",[]):
            if not allowed or item.get("id") in allowed:registry.add_mcp(MCPServerRecord.model_validate(item))
        return registry
