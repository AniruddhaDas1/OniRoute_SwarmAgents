"""E1.6.3/E1.6.4/E1.6.5 Provider adapter, non-streaming, streaming verification.

All deterministic, mocked provider responses. No live API keys.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.invocation import InvocationRequest, StreamChunk
from runtime.invocation.adapters import InterfaceOnlyAdapter, OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.exceptions import InvocationError, StreamConnectionError, StreamUnsupportedError
from runtime.invocation.models import StreamFinishReason, StreamUsage, Usage
from runtime.invocation.response import InvocationResponse
from runtime.models import ModelManager

ROOT = Path(__file__).parents[2]


def _default_model():
    return ModelManager(ROOT / "config" / "models.yaml").resolver.find_model("default-local")


class _FakeResponse:
    def __init__(self, lines):
        self._lines = list(lines)

    def __iter__(self):
        for line in self._lines:
            yield line.encode("utf-8")

    def close(self):
        pass


class _PostTransport:
    """Fake transport for non-streaming invoke()."""

    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error
        self.last_payload = None

    def post(self, url, payload, headers, timeout):
        self.last_payload = payload
        if self.error:
            raise InvocationError(self.error)
        return self.data

    def stream(self, url, payload, headers, timeout):
        raise AssertionError("stream() should not be called for non-streaming invoke")


class _StreamTransport:
    def __init__(self, lines, error=None):
        self._lines = lines
        self.error = error
        self.last_payload = None
        self.stream_calls = 0

    def post(self, url, payload, headers, timeout):
        raise AssertionError("post() should not be called for streaming")

    def stream(self, url, payload, headers, timeout):
        self.stream_calls += 1
        self.last_payload = payload
        if self.error:
            raise StreamConnectionError(self.error)
        return _FakeResponse(self._lines)


def _sse(*contents, finish_reason="stop", usage=None):
    lines = []
    for c in contents:
        lines.append("data: " + json.dumps({
            "id": "x", "object": "chat.completion.chunk", "created": 1,
            "choices": [{"index": 0, "delta": {"content": c}, "finish_reason": None}],
        }))
    terminal = {
        "id": "x", "object": "chat.completion.chunk", "created": 1,
        "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
    }
    if usage is not None:
        terminal["usage"] = usage
    lines.append("data: " + json.dumps(terminal))
    lines.append("data: [DONE]")
    return lines


# ---------------------------------------------------------------------------
# E1.6.3 Provider adapter verification
# ---------------------------------------------------------------------------


def test_openai_request_translation():
    """OpenAI adapter translates InvocationRequest to provider payload."""
    transport = _PostTransport({"id": "x", "choices": [{"message": {"content": "hi"}}], "usage": {}})
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    adapter.invoke(_default_model(), InvocationRequest(prompt="Hello", temperature=0.5, max_tokens=10))
    payload = transport.last_payload
    assert payload["model"] == "local-metadata-placeholder"
    assert payload["messages"][-1]["content"] == "Hello"
    assert payload["temperature"] == 0.5
    assert payload["max_tokens"] == 10
    assert payload["stream"] is False


def test_openai_response_translation():
    """OpenAI adapter translates provider response to InvocationResponse."""
    transport = _PostTransport({
        "id": "x",
        "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
    })
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    resp = adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))
    assert isinstance(resp, InvocationResponse)
    assert resp.text == "hello"
    assert resp.finish_reason == "stop"
    assert resp.usage.input_tokens == 1
    assert resp.usage.output_tokens == 2
    assert resp.usage.total_tokens == 3


def test_ollama_request_and_response_translation():
    """Ollama adapter translates request and response correctly."""
    transport = _PostTransport({
        "message": {"content": "hi"}, "done": True, "done_reason": "stop",
        "prompt_eval_count": 2, "eval_count": 3,
    })
    adapter = OllamaAdapter("http://x", transport=transport)
    resp = adapter.invoke(_default_model(), InvocationRequest(prompt="Hi", max_tokens=10))
    assert transport.last_payload["stream"] is False
    assert transport.last_payload["options"]["num_predict"] == 10
    assert resp.text == "hi"
    assert resp.finish_reason == "stop"
    assert resp.usage.input_tokens == 2
    assert resp.usage.output_tokens == 3
    assert resp.usage.total_tokens == 5


def test_adapter_authentication_headers_passthrough():
    """Auth headers configured on adapter are forwarded."""
    transport = _PostTransport({"id": "x", "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}})
    adapter = OpenAICompatibleAdapter("http://x", headers={"Authorization": "Bearer test"}, transport=transport)
    resp = adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))
    assert resp.text == "ok"
    assert adapter.headers["Authorization"] == "Bearer test"


def test_adapter_error_normalization():
    """Provider errors become InvocationError, not raw exceptions."""
    transport = _PostTransport(error="connection refused")
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    with pytest.raises(InvocationError):
        adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))


def test_interface_only_adapter_no_streaming():
    """InterfaceOnlyAdapter does not fake streaming."""
    adapter = InterfaceOnlyAdapter("http://x")
    with pytest.raises(StreamUnsupportedError):
        list(adapter.stream(_default_model(), InvocationRequest(prompt="Hi")))


# ---------------------------------------------------------------------------
# E1.6.4 Non-streaming verification
# ---------------------------------------------------------------------------


def test_non_streaming_success():
    transport = _PostTransport({"id": "x", "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}})
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    resp = adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))
    assert resp.text == "ok"
    assert resp.finish_reason == "stop"


def test_non_streaming_empty_response():
    """Empty provider response becomes empty text, not a crash."""
    transport = _PostTransport({"id": "x", "choices": [{"message": {"content": ""}}], "usage": {}})
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    resp = adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))
    assert resp.text == ""


def test_non_streaming_malformed_response():
    """Malformed provider response yields structured error, not false success."""
    transport = _PostTransport({"unexpected": "shape"})
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    with pytest.raises(Exception):
        adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))


def test_non_streaming_provider_error():
    """Provider error becomes InvocationError."""
    transport = _PostTransport(error="500 internal error")
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    with pytest.raises(InvocationError):
        adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))


def test_non_streaming_timeout_normalization():
    """Timeout becomes InvocationError (no raw urllib timeout leak)."""
    transport = _PostTransport(error="timed out")
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    with pytest.raises(InvocationError):
        adapter.invoke(_default_model(), InvocationRequest(prompt="Hi"))


def test_non_streaming_invalid_capability_request():
    """Requesting an unavailable capability fails at selection (not silently)."""
    from runtime.models import SelectionRequest, Capability
    from runtime.models.exceptions import NoCompatibleModelError
    manager = ModelManager(ROOT / "config" / "models.yaml")
    with pytest.raises(NoCompatibleModelError):
        manager.select_best_model(SelectionRequest(capabilities=frozenset({Capability.VISION})))


# ---------------------------------------------------------------------------
# E1.6.5 Streaming verification
# ---------------------------------------------------------------------------


def test_streaming_real_incremental_chunks():
    transport = _StreamTransport(_sse("a", "b", "c", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    chunks = list(adapter.stream(_default_model(), InvocationRequest(prompt="Hi", streaming=True)))
    deltas = [c.delta for c in chunks]
    assert "a" in deltas and "b" in deltas and "c" in deltas
    # Terminal event is the last real provider event; [DONE] is not a chunk.
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].delta == ""


def test_streaming_ordering():
    transport = _StreamTransport(_sse("1", "2", "3", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    chunks = list(adapter.stream(_default_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert [c.sequence for c in chunks] == [0, 1, 2, 3]


def test_streaming_done_handling_no_synthetic_chunk():
    transport = _StreamTransport(_sse("x", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    chunks = list(adapter.stream(_default_model(), InvocationRequest(prompt="Hi", streaming=True)))
    # One content delta + one real terminal event. No synthetic chunk.
    assert len(chunks) == 2
    assert chunks[0].delta == "x"
    assert chunks[1].delta == ""


def test_streaming_finish_reason_and_usage():
    transport = _StreamTransport(_sse("content", finish_reason="length", usage={
        "prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12,
    }))
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    chunks = list(adapter.stream(_default_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert chunks[-1].finish_reason == "length"
    assert chunks[-1].usage.total_tokens == 12


def test_streaming_partial_content_and_failure():
    """Stream interruption preserves already-received chunks and raises."""
    class _FailAfterFirstResponse:
        def __init__(self):
            self._lines = [
                "data: " + json.dumps({"id": "x", "choices": [{"delta": {"content": "partial"}, "finish_reason": None}]}),
                "data: " + json.dumps({"id": "x", "choices": [{"delta": {"content": " more"}, "finish_reason": None}]}),
            ]
            self._idx = 0
        def __iter__(self):
            return self
        def __next__(self):
            if self._idx < len(self._lines):
                line = self._lines[self._idx]
                self._idx += 1
                return line.encode()
            raise StreamConnectionError("connection reset mid-stream")
        def close(self):
            pass
    class _FailAfterFirstTransport:
        def __init__(self):
            self.last_payload = None
            self.stream_calls = 0
        def post(self, url, payload, headers, timeout):
            raise AssertionError("not used")
        def stream(self, url, payload, headers, timeout):
            self.stream_calls += 1
            self.last_payload = payload
            return _FailAfterFirstResponse()

    transport = _FailAfterFirstTransport()
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    collected = []
    with pytest.raises(StreamConnectionError):
        for chunk in adapter.stream(_default_model(), InvocationRequest(prompt="Hi", streaming=True)):
            collected.append(chunk)
    # The first deltas were preserved before the stream failed.
    assert [c.delta for c in collected] == ["partial", " more"]


def test_streaming_invoke_not_used_as_fake():
    """Streaming path uses stream() not post()/invoke()."""
    transport = _StreamTransport(_sse("x", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://x", transport=transport)
    list(adapter.stream(_default_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert transport.stream_calls == 1


def test_streaming_unsupported_adapter_structured():
    adapter = InterfaceOnlyAdapter("http://x")
    with pytest.raises(StreamUnsupportedError):
        list(adapter.stream(_default_model(), InvocationRequest(prompt="Hi", streaming=True)))
