from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Decision(StrEnum): ALLOW="Allow"; DENY="Deny"; REQUIRE_APPROVAL="Require Approval"
class GovernanceRequest(BaseModel):
    kind:str; workflow:str|None=None; agent:str|None=None; skill:str|None=None; model:str|None=None; provider:str|None=None; protocol:str|None=None; tool:str|None=None; capabilities:frozenset[str]=Field(default_factory=frozenset); permissions:frozenset[str]=Field(default_factory=frozenset); estimated_tokens:int=0; estimated_runtime_ms:int=0; metadata:dict[str,Any]=Field(default_factory=dict)
class PolicyResult(BaseModel):
    model_config=ConfigDict(frozen=True); decision:Decision; reasons:tuple[str,...]=(); risk_score:int=0; approval:str="Automatic"
class AuditRecord(BaseModel):
    model_config=ConfigDict(frozen=True); id:str; timestamp:datetime; request:GovernanceRequest; result:PolicyResult; outcome:str
