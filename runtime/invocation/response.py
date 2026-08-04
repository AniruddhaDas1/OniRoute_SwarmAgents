from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import ToolCall, Usage


class InvocationResponse(BaseModel):
    model_config=ConfigDict(frozen=True)
    text:str=""; reasoning:str|None=None; tool_calls:tuple[ToolCall,...]=(); structured_output:Any=None; json_output:dict[str,Any]|list[Any]|None=None; images:tuple[str,...]=(); audio:tuple[str,...]=(); usage:Usage=Field(default_factory=Usage); latency_ms:float=0; finish_reason:str|None=None; metadata:dict[str,Any]=Field(default_factory=dict)
