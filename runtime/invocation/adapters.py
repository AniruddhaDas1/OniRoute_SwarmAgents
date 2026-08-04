from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Iterator
from urllib.request import Request, urlopen

from runtime.models.models import ModelRecord
from .exceptions import InvocationError
from .models import Usage
from .request import InvocationRequest
from .response import InvocationResponse


class HTTPTransport:
    def post(self,url:str,payload:dict[str,Any],headers:dict[str,str],timeout:float)->dict[str,Any]:
        request=Request(url,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json",**headers},method="POST")
        try:
            with urlopen(request,timeout=timeout) as response:return json.loads(response.read().decode())
        except Exception as exc:raise InvocationError(str(exc)) from exc


class BaseAdapter:
    protocol="custom"
    def __init__(self,endpoint:str,headers:dict[str,str]|None=None,timeout:float=60,transport:HTTPTransport|None=None):self.endpoint=endpoint.rstrip("/");self.headers=headers or {};self.timeout=timeout;self.transport=transport or HTTPTransport()
    def stream(self,model:ModelRecord,request:InvocationRequest)->Iterator[str]:
        response=self.invoke(model,request.model_copy(update={"streaming":False}));yield response.text


class OpenAICompatibleAdapter(BaseAdapter):
    protocol="openai-compatible"
    def invoke(self,model:ModelRecord,request:InvocationRequest)->InvocationResponse:
        messages=[]
        if request.system_prompt:messages.append({"role":"system","content":request.system_prompt})
        messages.extend(item.model_dump() for item in request.messages)
        if request.prompt:messages.append({"role":"user","content":request.prompt})
        payload={"model":model.id,"messages":messages,"stream":False}
        if request.temperature is not None:payload["temperature"]=request.temperature
        if request.max_tokens is not None:payload["max_tokens"]=request.max_tokens
        if request.stop_sequences:payload["stop"]=list(request.stop_sequences)
        started=perf_counter();data=self.transport.post(f"{self.endpoint}/chat/completions",payload,self.headers,self.timeout);latency=(perf_counter()-started)*1000
        choice=(data.get("choices") or [{}])[0];message=choice.get("message") or {};usage=data.get("usage") or {}
        return InvocationResponse(text=message.get("content") or "",reasoning=message.get("reasoning_content"),usage=Usage(input_tokens=usage.get("prompt_tokens",0),output_tokens=usage.get("completion_tokens",0),total_tokens=usage.get("total_tokens",0)),latency_ms=latency,finish_reason=choice.get("finish_reason"),metadata={"protocol":self.protocol,"raw_id":data.get("id")})


class OllamaAdapter(BaseAdapter):
    protocol="ollama"
    def invoke(self,model:ModelRecord,request:InvocationRequest)->InvocationResponse:
        messages=[]
        if request.system_prompt:messages.append({"role":"system","content":request.system_prompt})
        messages.extend(item.model_dump() for item in request.messages)
        if request.prompt:messages.append({"role":"user","content":request.prompt})
        payload={"model":model.id,"messages":messages,"stream":False,"options":{}}
        if request.temperature is not None:payload["options"]["temperature"]=request.temperature
        if request.max_tokens is not None:payload["options"]["num_predict"]=request.max_tokens
        started=perf_counter();data=self.transport.post(f"{self.endpoint}/api/chat",payload,self.headers,self.timeout);latency=(perf_counter()-started)*1000
        usage=Usage(input_tokens=data.get("prompt_eval_count",0),output_tokens=data.get("eval_count",0),total_tokens=data.get("prompt_eval_count",0)+data.get("eval_count",0))
        return InvocationResponse(text=(data.get("message") or {}).get("content", ""),usage=usage,latency_ms=latency,finish_reason=data.get("done_reason"),metadata={"protocol":self.protocol,"done":data.get("done")})


class InterfaceOnlyAdapter(BaseAdapter):
    def invoke(self,model:ModelRecord,request:InvocationRequest)->InvocationResponse:raise NotImplementedError(f"Protocol adapter '{self.protocol}' is interface-only")
