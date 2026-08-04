from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from runtime.models import Capability
from .models import Message, ToolRequest


class InvocationRequest(BaseModel):
    model_config=ConfigDict(frozen=True)
    prompt:str|None=None; system_prompt:str|None=None; messages:tuple[Message,...]=(); context:dict[str,Any]=Field(default_factory=dict); artifacts:tuple[dict[str,Any],...]=(); tool_requests:tuple[ToolRequest,...]=(); capabilities:frozenset[Capability]=Field(default_factory=frozenset); temperature:float|None=None; max_tokens:int|None=None; stop_sequences:tuple[str,...]=(); streaming:bool=False; metadata:dict[str,Any]=Field(default_factory=dict)
