from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .capabilities import ToolCapability
from .permissions import Permission


class ToolHealth(StrEnum): HEALTHY="Healthy"; UNAVAILABLE="Unavailable"; DISABLED="Disabled"; DEPRECATED="Deprecated"; EXPERIMENTAL="Experimental"; UNKNOWN="Unknown"
class ToolProtocol(StrEnum): LOCAL_PYTHON="local-python"; CLI="cli"; MCP="mcp"; HTTP="http"; OPENAPI="openapi"; CUSTOM="custom"

class ToolRecord(BaseModel):
    model_config=ConfigDict(frozen=True)
    id:str; display_name:str; description:str; category:str; capabilities:frozenset[ToolCapability]; protocol:ToolProtocol; provider:str
    input_contract:dict[str,Any]=Field(default_factory=dict); output_contract:dict[str,Any]=Field(default_factory=dict); permissions:frozenset[Permission]=Field(default_factory=frozenset); risk_level:str="low"; lifecycle:str="Experimental"; validation:str="Unvalidated"; trust:str="Unknown"
    supports_streaming:bool=False; supports_async:bool=False; supports_files:bool=False; supports_images:bool=False; supports_network:bool=False; supports_shell:bool=False; supports_database:bool=False; supports_browser:bool=False
    health:ToolHealth=ToolHealth.UNKNOWN; priority:int=0; aliases:tuple[str,...]=(); local:bool=False

class MCPServerRecord(BaseModel):
    model_config=ConfigDict(frozen=True)
    id:str; display_name:str; capabilities:frozenset[ToolCapability]; available_tools:tuple[str,...]=(); authentication_type:str="none"; transport:str="stdio"; lifecycle:str="Experimental"; health:ToolHealth=ToolHealth.UNKNOWN; version:str="0.0.0"; priority:int=0

class ToolSelectionRequest(BaseModel):
    capabilities:frozenset[ToolCapability]; permissions:frozenset[Permission]=Field(default_factory=frozenset); protocol:ToolProtocol|None=None; provider:str|None=None
