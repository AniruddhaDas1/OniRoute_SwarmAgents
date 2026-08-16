from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Iterator
from urllib.request import Request, urlopen

from runtime.models.models import ModelRecord
from .exceptions import InvocationError, StreamConnectionError, StreamUnsupportedError
from .models import StreamChunk, StreamFinishReason, StreamUsage, Usage
from .request import InvocationRequest
from .response import InvocationResponse


class HTTPTransport:
    def post(self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except Exception as exc:
            raise InvocationError(str(exc)) from exc

    def stream(self, url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float):
        """Open a streaming HTTP transport for incremental response reading.

        Returns an ``http.client.HTTPResponse``-like object that can be iterated
        line-by-line. The caller is responsible for closing the response.
        """
        request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            return urlopen(request, timeout=timeout)
        except Exception as exc:
            raise StreamConnectionError(str(exc)) from exc


class BaseAdapter:
    """Base adapter. ``stream`` is opt-in: adapters that genuinely support
    incremental provider streaming override ``stream()``. The base
    implementation signals that streaming is unsupported rather than simulating
    it by splitting a completed response."""
    protocol = "custom"

    def __init__(self, endpoint: str, headers: dict[str, str] | None = None, timeout: float = 60, transport: HTTPTransport | None = None):
        self.endpoint = endpoint.rstrip("/"); self.headers = headers or {}; self.timeout = timeout; self.transport = transport or HTTPTransport()

    def stream(self, model: ModelRecord, request: InvocationRequest) -> Iterator[StreamChunk]:
        raise StreamUnsupportedError(
            f"Provider '{model.provider}' (id={model.id}, protocol={model.protocol}) "
            f"does not provide a real streaming interface."
        )


class OpenAICompatibleAdapter(BaseAdapter):
    protocol = "openai-compatible"

    def _prepare_messages(self, request: InvocationRequest):
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(item.model_dump() for item in request.messages)
        if request.prompt:
            messages.append({"role": "user", "content": request.prompt})
        return messages

    def _build_payload(self, model: ModelRecord, request: InvocationRequest) -> dict[str, Any]:
        payload = {"model": model.id, "messages": self._prepare_messages(request), "stream": request.streaming}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop_sequences:
            payload["stop"] = list(request.stop_sequences)
        return payload

    def invoke(self, model: ModelRecord, request: InvocationRequest) -> InvocationResponse:
        messages = self._prepare_messages(request)
        payload = {"model": model.id, "messages": messages, "stream": False}
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop_sequences:
            payload["stop"] = list(request.stop_sequences)
        started = perf_counter(); data = self.transport.post(f"{self.endpoint}/chat/completions", payload, self.headers, self.timeout)
        latency = (perf_counter() - started) * 1000
        choice = (data.get("choices") or [{}])[0]; message = choice.get("message") or {}; usage = data.get("usage") or {}
        return InvocationResponse(
            text=message.get("content") or "",
            reasoning=message.get("reasoning_content"),
            usage=Usage(input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0), total_tokens=usage.get("total_tokens", 0)),
            latency_ms=latency,
            finish_reason=choice.get("finish_reason"),
            metadata={"protocol": self.protocol, "provider": model.provider, "model": model.id, "raw_id": data.get("id")},
        )

    def stream(self, model: ModelRecord, request: InvocationRequest) -> Iterator[StreamChunk]:
        """Genuine OpenAI-compatible Server-Sent Events streaming.

        Reads the HTTP response incrementally, parsing only real ``data: ``
        SSE events. A literal ``data: [DONE]`` terminates the stream and
        produces no output chunk. Provider deltas, finish reason, and usage
        (when present in the provider's terminal event) are yielded verbatim.
        """
        payload = self._build_payload(model, request)
        payload["stream"] = True
        response = self.transport.stream(f"{self.endpoint}/chat/completions", payload, self.headers, self.timeout)
        sequence = 0
        try:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
                if not line or line.startswith(":") or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                # data: [DONE] is a sentinel; never converted to a content chunk.
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                created = event.get("created")
                raw_id = event.get("id")
                for choice in event.get("choices", []):
                    delta = choice.get("delta") or {}
                    content = delta.get("content")
                    finish_reason = choice.get("finish_reason")
                    if content is None and finish_reason is None:
                        continue
                    chunk_usage: StreamUsage | None = None
                    event_usage = event.get("usage")
                    if event_usage:
                        chunk_usage = StreamUsage(
                            input_tokens=event_usage.get("prompt_tokens"),
                            output_tokens=event_usage.get("completion_tokens"),
                            total_tokens=event_usage.get("total_tokens"),
                        )
                    yield StreamChunk(
                        sequence=sequence,
                        delta=content or "",
                        provider=model.provider,
                        model=model.id,
                        protocol=self.protocol,
                        finish_reason=finish_reason,
                        usage=chunk_usage,
                        metadata={"raw_id": raw_id, "object": event.get("object"), "protocol": self.protocol, "created": created},
                    )
                    sequence += 1
        finally:
            try:
                response.close()
            except Exception:
                pass


class OllamaAdapter(BaseAdapter):
    protocol = "ollama"

    def _prepare_messages(self, request: InvocationRequest):
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.extend(item.model_dump() for item in request.messages)
        if request.prompt:
            messages.append({"role": "user", "content": request.prompt})
        return messages

    def _build_payload(self, model: ModelRecord, request: InvocationRequest) -> dict[str, Any]:
        payload = {"model": model.id, "messages": self._prepare_messages(request), "stream": request.streaming, "options": {}}
        if request.temperature is not None:
            payload["options"]["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["options"]["num_predict"] = request.max_tokens
        return payload

    def invoke(self, model: ModelRecord, request: InvocationRequest) -> InvocationResponse:
        messages = self._prepare_messages(request)
        payload = {"model": model.id, "messages": messages, "stream": False, "options": {}}
        if request.temperature is not None:
            payload["options"]["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["options"]["num_predict"] = request.max_tokens
        started = perf_counter(); data = self.transport.post(f"{self.endpoint}/api/chat", payload, self.headers, self.timeout)
        latency = (perf_counter() - started) * 1000
        usage = Usage(
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        )
        return InvocationResponse(
            text=(data.get("message") or {}).get("content", ""),
            usage=usage,
            latency_ms=latency,
            finish_reason=data.get("done_reason"),
            metadata={"protocol": self.protocol, "provider": model.provider, "model": model.id, "done": data.get("done")},
        )

    def stream(self, model: ModelRecord, request: InvocationRequest) -> Iterator[StreamChunk]:
        """Genuine Ollama newline-delimited JSON streaming.

        Parses each real ndjson response object incrementally. The provider's
        final ``done`` event (which carries ``done_reason`` and token usage)
        is yielded as a terminal chunk carrying no content delta.
        """
        payload = self._build_payload(model, request)
        payload["stream"] = True
        response = self.transport.stream(f"{self.endpoint}/api/chat", payload, self.headers, self.timeout)
        sequence = 0
        try:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = event.get("message") or {}
                content = message.get("content")
                done = event.get("done")
                finish_reason = event.get("done_reason") if done else None
                chunk_usage: StreamUsage | None = None
                if done:
                    pe = event.get("prompt_eval_count"); ec = event.get("eval_count")
                    if pe is not None or ec is not None:
                        chunk_usage = StreamUsage(input_tokens=pe, output_tokens=ec, total_tokens=(pe or 0) + (ec or 0))
                yield StreamChunk(
                    sequence=sequence,
                    delta=content or "",
                    provider=model.provider,
                    model=model.id,
                    protocol=self.protocol,
                    finish_reason=finish_reason,
                    usage=chunk_usage,
                    metadata={"response_model": event.get("model"), "protocol": self.protocol, "created_at": event.get("created_at")},
                )
                sequence += 1
                if done:
                    break
        finally:
            try:
                response.close()
            except Exception:
                pass


class InterfaceOnlyAdapter(BaseAdapter):
    def invoke(self, model: ModelRecord, request: InvocationRequest) -> InvocationResponse:
        raise NotImplementedError(f"Protocol adapter '{self.protocol}' is interface-only")
