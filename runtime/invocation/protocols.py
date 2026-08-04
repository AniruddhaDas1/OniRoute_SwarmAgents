from typing import Iterator, Protocol

from runtime.models.models import ModelRecord
from .request import InvocationRequest
from .response import InvocationResponse


class ProtocolAdapter(Protocol):
    protocol:str
    def invoke(self,model:ModelRecord,request:InvocationRequest)->InvocationResponse:...
    def stream(self,model:ModelRecord,request:InvocationRequest)->Iterator[str]:...
