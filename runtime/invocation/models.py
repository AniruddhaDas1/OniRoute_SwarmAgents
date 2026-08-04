from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config=ConfigDict(frozen=True); role:str; content:str
class ToolRequest(BaseModel):
    model_config=ConfigDict(frozen=True); name:str; arguments:dict[str,Any]=Field(default_factory=dict)
class ToolCall(BaseModel):
    model_config=ConfigDict(frozen=True); id:str|None=None; name:str; arguments:dict[str,Any]=Field(default_factory=dict)
class Usage(BaseModel):
    model_config=ConfigDict(frozen=True); input_tokens:int=0; output_tokens:int=0; total_tokens:int=0
