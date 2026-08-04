from typing import Protocol

from .models import ToolRecord, ToolSelectionRequest


class ToolResolutionContract(Protocol):
    def find_tool(self,identifier:str)->ToolRecord|None:...
class ToolSelectionContract(Protocol):
    def recommend(self,request:ToolSelectionRequest)->ToolRecord:...
