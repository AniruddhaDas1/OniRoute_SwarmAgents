from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from .capabilities import Capability


class HealthStatus(StrEnum):
    HEALTHY="Healthy"; UNAVAILABLE="Unavailable"; DISABLED="Disabled"; DEPRECATED="Deprecated"; EXPERIMENTAL="Experimental"; UNKNOWN="Unknown"


class ProtocolRecord(BaseModel):
    model_config=ConfigDict(frozen=True); id:str; display_name:str

class ProviderRecord(BaseModel):
    model_config=ConfigDict(frozen=True); id:str; display_name:str; protocols:tuple[str,...]=(); status:HealthStatus=HealthStatus.UNKNOWN; local:bool=False

class ModelRecord(BaseModel):
    model_config=ConfigDict(frozen=True)
    id:str; display_name:str; provider:str; protocol:str; capabilities:frozenset[Capability]
    context_window:int=0; max_output:int=0; supports_streaming:bool=False; supports_vision:bool=False; supports_audio:bool=False; supports_tools:bool=False; supports_embeddings:bool=False; supports_structured_output:bool=False; supports_images:bool=False; supports_reasoning:bool=False; supports_json:bool=False
    status:HealthStatus=HealthStatus.UNKNOWN; priority:int=0; cost_class:str="unknown"; local:bool=False; aliases:tuple[str,...]=()

class SelectionRequest(BaseModel):
    capabilities:frozenset[Capability]=Field(default_factory=frozenset); protocol:str|None=None; provider:str|None=None; local_only:bool=False; local_preference:bool=False; user_preference:tuple[str,...]=(); environment_preference:tuple[str,...]=()
