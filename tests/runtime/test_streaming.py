"""Tests for Runtime Streaming subsystem (Phase E1.5).

All streaming paths are exercised against offline, deterministic fake provider
transports. No live API keys or real network calls are required for the core
suite; a single real-HTTP integration test is also provided.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.engineering import EngineeringWorkerEngine
from runtime.engineering.models import TaskContext, TaskState
from runtime.invocation import InvocationEngine, InvocationRequest, StreamChunk
from runtime.invocation.adapters import InterfaceOnlyAdapter, OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.exceptions import StreamConnectionError, StreamUnsupportedError
from runtime.invocation.models import StreamFinishReason, StreamUsage
from runtime.invocation.streaming import assemble_stream
from runtime.models import ModelManager, SelectionRequest

ROOT = Path(__file__).parents[2]
MODELS_YAML = ROOT / "config" / "models.yaml"


def _default_local_model():
    return ModelManager(MODELS_YAML).resolver.find_model("default-local")


# ---------------------------------------------------------------------------
# Offline fake transports
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Iterates canned provider lines, mimicking an HTTPResponse line stream."""

    def __init__(self, lines):
        self._lines = list(lines)
        self._index = 0

    def __iter__(self):
        idx = 0
        while idx < len(self._lines):
            yield self._lines[idx].encode("utf-8")
            idx += 1

    def close(self):
        pass


class FakeSSETransport:
    """Captures the outgoing payload and returns canned SSE lines."""

    def __init__(self, sse_lines):
        self.last_payload = None
        self.stream_calls = 0
        self._sse_lines = sse_lines

    def post(self, url, payload, headers, timeout):
        return {}

    def stream(self, url, payload, headers, timeout):
        self.last_payload = payload
        self.stream_calls += 1
        return _FakeResponse(self._sse_lines)


class FakeOllamaTransport:
    def __init__(self, ndjson_lines):
        self.last_payload = None
        self.stream_calls = 0
        self._lines = ndjson_lines

    def post(self, url, payload, headers, timeout):
        return {}

    def stream(self, url, payload, headers, timeout):
        self.last_payload = payload
        self.stream_calls += 1
        return _FakeResponse(self._lines)


def _sse(*contents, finish_reason="stop", usage=None):
    """Build a sequence of OpenAI-compatible SSE lines: one chunk per content,
    a real provider terminal event (empty delta + finish_reason + usage), then [DONE]."""
    lines = []
    for c in contents:
        event = {"id": "x", "object": "chat.completion.chunk", "created": 1,
                 "choices": [{"index": 0, "delta": {"content": c}, "finish_reason": None}]}
        lines.append("data: " + json.dumps(event))
    terminal = {"id": "x", "object": "chat.completion.chunk", "created": 1,
                "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}]}
    if usage is not None:
        terminal["usage"] = usage
    lines.append("data: " + json.dumps(terminal))
    lines.append("data: [DONE]")
    return lines


# ---------------------------------------------------------------------------
# E1.5.2: Protocol adapter streaming -- OpenAI-compatible SSE
# ---------------------------------------------------------------------------


def test_openai_sse_delta_parsing():
    """1. OpenAI SSE delta parsing yields a single content delta."""
    transport = FakeSSETransport(_sse("hello", finish_reason="stop", usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    chunks = list(adapter.stream(_default_local_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert len(chunks) == 2
    assert chunks[0].delta == "hello"
    assert chunks[1].finish_reason == "stop"


def test_openai_multiple_sse_chunks():
    """2. Multiple SSE chunks are emitted in order."""
    transport = FakeSSETransport(_sse("chunk A", "chunk B", "chunk C", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    chunks = list(adapter.stream(_default_local_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert [c.delta for c in chunks[:-1]] == ["chunk A", "chunk B", "chunk C"]


def test_openai_chunk_ordering_preserved():
    """3. Correct chunk ordering via monotonic sequence numbers."""
    transport = FakeSSETransport(_sse("a", "b", "c", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    chunks = list(adapter.stream(_default_local_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert [c.sequence for c in chunks] == [0, 1, 2, 3]


def test_openai_done_handling_terminates_stream():
    """4. Actual [DONE] handling: terminates the stream."""
    transport = FakeSSETransport(_sse("data", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    chunks = list(adapter.stream(_default_local_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert chunks[-1].finish_reason == "stop"
    # The [DONE] sentinel is consumed and never raised.
    assert transport.stream_calls == 1


def test_openai_no_synthetic_terminal_chunk():
    """5. No synthetic terminal chunk: [DONE] yields nothing; only real provider events are emitted."""
    transport = FakeSSETransport(_sse("A", "B", "C", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    chunks = list(adapter.stream(_default_local_model(), InvocationRequest(prompt="Hi", streaming=True)))
    # Three real content deltas + one real terminal event carrying finish_reason.
    assert len(chunks) == 4
    assert [c.delta for c in chunks] == ["A", "B", "C", ""]
    assert chunks[-1].delta == ""
    assert chunks[-1].finish_reason == "stop"


def test_openai_finish_reason_propagated():
    """6. Finish reason propagation from the provider terminal event."""
    transport = FakeSSETransport(_sse("hi", finish_reason="length"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    chunks = list(adapter.stream(_default_local_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert chunks[-1].finish_reason == "length"


def test_openai_provider_metadata_propagated():
    """7. Provider/model/protocol metadata propagation on chunks."""
    transport = FakeSSETransport(_sse("x", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    model = _default_local_model()
    chunks = list(adapter.stream(model, InvocationRequest(prompt="Hi", streaming=True)))
    assert chunks[0].provider == model.provider
    assert chunks[0].model == model.id
    assert chunks[0].protocol == adapter.protocol


def test_openai_streaming_request_propagated():
    """8. StreamingRequest propagation: the provider request carries stream=True."""
    transport = FakeSSETransport(_sse("x", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    list(adapter.stream(_default_local_model(), InvocationRequest(prompt="Hi", streaming=True)))
    assert transport.last_payload["stream"] is True


def test_engine_stream_yields_real_chunks_in_order():
    """9. InvocationEngine.stream() propagates real chunks with metadata."""
    transport = FakeSSETransport(_sse("hello ", "world", finish_reason="stop",
                                      usage={"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10}))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", adapter)
    engine = InvocationEngine(ModelManager(MODELS_YAML), dispatcher)
    chunks = list(engine.stream(InvocationRequest(prompt="Hi"), SelectionRequest()))
    assert "".join(c.delta for c in chunks) == "hello world"
    assert [c.sequence for c in chunks] == [0, 1, 2]
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage.total_tokens == 10
    assert chunks[-1].provider == "custom"
    assert chunks[-1].model == "local-metadata-placeholder"


def test_engine_stream_does_not_use_invoke():
    """InvocationEngine.stream() must never call invoke() to fake streaming."""
    transport = FakeSSETransport(_sse("x", finish_reason="stop"))
    adapter = OpenAICompatibleAdapter("http://openai.local", transport=transport)
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", adapter)
    engine = InvocationEngine(ModelManager(MODELS_YAML), dispatcher)
    list(engine.stream(InvocationRequest(prompt="Hi"), SelectionRequest()))
    # stream_post (not post) is what real streaming uses; invoke() uses post().
    assert transport.stream_calls == 1


def test_engine_stream_unsupported_provider():
    """16. Unsupported streaming provider returns a structured unsupported result."""
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", InterfaceOnlyAdapter("http://x.local"))
    engine = InvocationEngine(ModelManager(MODELS_YAML), dispatcher)
    chunks = list(engine.stream(InvocationRequest(prompt="Hi"), SelectionRequest()))
    assert len(chunks) == 1
    assert chunks[0].finish_reason == StreamFinishReason.STREAMING_UNSUPPORTED.value
    assert chunks[0].delta == ""
    assert chunks[0].metadata.get("unsupported") is True


# ---------------------------------------------------------------------------
# E1.5.3: Ollama native streaming
# ---------------------------------------------------------------------------


def test_ollama_native_streaming():
    """Ollama newline-delimited JSON streaming yields real deltas and final usage."""
    ndjson = [
        json.dumps({"model": "m", "created_at": "t", "message": {"role": "assistant", "content": "delta 1"}}),
        json.dumps({"model": "m", "created_at": "t", "message": {"role": "assistant", "content": " delta 2"}}),
        json.dumps({"model": "m", "created_at": "t", "done": True, "done_reason": "stop",
                    "prompt_eval_count": 5, "eval_count": 7}),
    ]
    transport = FakeOllamaTransport(ndjson)
    adapter = OllamaAdapter("http://ollama.local", transport=transport)
    model = _default_local_model()
    chunks = list(adapter.stream(model, InvocationRequest(prompt="Hi", streaming=True)))
    assert [c.sequence for c in chunks] == [0, 1, 2]
    assert "".join(c.delta for c in chunks) == "delta 1 delta 2"
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage.total_tokens == 12
    assert transport.last_payload["stream"] is True


# ---------------------------------------------------------------------------
# E1.5.5: EngineeringWorker streaming consumption
# ---------------------------------------------------------------------------


class _CapturingStreamAdapter:
    """Adapter that yields real staged chunks and records the request."""

    protocol = "local-process"

    def __init__(self, stages):
        # stages: list of chunk-dicts describing delta/finish_reason/usage
        self._stages = stages
        self.captured_request = None

    def stream(self, model, request):
        self.captured_request = request
        for stage in self._stages:
            yield StreamChunk(
                sequence=stage.get("sequence", 0),
                delta=stage.get("delta", ""),
                provider=stage.get("provider", model.provider),
                model=stage.get("model", model.id),
                protocol=self.protocol,
                finish_reason=stage.get("finish_reason"),
                usage=StreamUsage(**stage["usage"]) if stage.get("usage") else None,
            )

    def invoke(self, model, request):
        raise AssertionError("streaming worker must not call invoke()")


def _build_worker(stages):
    adapter = _CapturingStreamAdapter(stages)
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", adapter)
    engine = InvocationEngine(ModelManager(MODELS_YAML), dispatcher)
    worker = EngineeringWorkerEngine(invocation_engine=engine)
    return worker, adapter


def _single_contract():
    from runtime.contracts import EngineeringContract
    return EngineeringContract(
        contract_id="ctr-e15-001",
        target_path=str(Path("src/app/main.py")),
        target_type="file",
        assigned_profile_id="prof-backend",
        assigned_profile_role="Backend Engineer",
        engineering_discipline="Backend",
        output_artifacts=[],
        architecture_constraints=[],
        coding_standards=[],
        contract_hash="0" * 64,
    )


def test_engineering_worker_stream_consumption(tmp_path):
    """10. EngineeringWorker consumes real streaming output into a final result."""
    stages = [
        {"sequence": 0, "delta": "class App:", "provider": "test-provider", "model": "test-model"},
        {"sequence": 1, "delta": "\n    pass\n", "provider": "test-provider", "model": "test-model"},
        {"sequence": 2, "delta": "", "finish_reason": "stop", "provider": "test-provider", "model": "test-model",
         "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}},
    ]
    worker, adapter = _build_worker(stages)
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    result = worker.stream_execute_contract(_single_contract(), str(ws_root))

    assert result.provider == "test-provider"
    assert result.model == "test-model"
    assert result.token_usage["prompt_tokens"] == 10
    assert result.token_usage["completion_tokens"] == 5
    assert result.token_usage["total_tokens"] == 15
    assert result.evidence.get("streaming") is True
    assert "stop" in result.evidence.get("finish_reasons", [])
    # Final artifact was written only from fully streamed content.
    written = ws_root / "src/app/main.py"
    assert written.exists()
    assert written.read_text() == "class App:\n    pass\n"
    # StreamingRequest flag propagated to the invocation.
    assert adapter.captured_request.streaming is True


def test_streaming_request_context_propagation(tmp_path):
    """14. ExecutionContext (task/contract IDs) propagates to the streaming request."""
    stages = [{"delta": "content", "finish_reason": "stop", "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}}]
    worker, adapter = _build_worker(stages)
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    worker.stream_execute_contract(_single_contract(), str(ws_root))
    ctx = adapter.captured_request.context
    assert ctx["contract_id"] == "ctr-e15-001"
    assert ctx["task_id"].startswith("task-impl-")
    assert adapter.captured_request.streaming is True


def test_partial_content_preserved_on_stream_failure(tmp_path):
    """11. Partial content preserved on a mid-stream connection failure."""
    class _FailingAdapter:
        protocol = "local-process"
        def stream(self, model, request):
            yield StreamChunk(sequence=0, delta="partial-", provider=model.provider, model=model.id, protocol="local-process")
            raise StreamConnectionError("connection dropped mid-stream")
        def invoke(self, model, request):
            raise AssertionError("must not invoke()")
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", _FailingAdapter())
    engine = InvocationEngine(ModelManager(MODELS_YAML), dispatcher)
    worker = EngineeringWorkerEngine(invocation_engine=engine)
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    result = worker.stream_execute_contract(_single_contract(), str(ws_root))

    assert result.evidence.get("failed_during_streaming") is True
    assert result.evidence.get("partial_content", {}).get("task-impl-ctr-e15-001") == "partial-"
    # Partial content must NOT be certified as the final artifact.
    assert not (ws_root / "src/app/main.py").exists()


def test_stream_completion_assembles_artifact(tmp_path):
    """12. Stream completion writes the assembled artifact with finish_reason stop."""
    stages = [
        {"delta": "# ", "finish_reason": None},
        {"delta": "Real Estate Website\n", "finish_reason": None},
        {"delta": "", "finish_reason": "stop", "usage": {"input_tokens": 7, "output_tokens": 9, "total_tokens": 16}},
    ]
    worker, _ = _build_worker(stages)
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    result = worker.stream_execute_contract(_single_contract(), str(ws_root))
    assert result.evidence.get("streaming") is True
    content = (ws_root / "src/app/main.py").read_text()
    assert content == "# Real Estate Website\n"
    assert result.token_usage["total_tokens"] == 16


def test_stream_failure_unsupported_is_not_success(tmp_path):
    """13. Unsupported streaming cannot be reported as a successful generation."""
    dispatcher = InvocationDispatcher()
    dispatcher.register("local-process", InterfaceOnlyAdapter("http://x.local"))
    engine = InvocationEngine(ModelManager(MODELS_YAML), dispatcher)
    worker = EngineeringWorkerEngine(invocation_engine=engine)
    ws_root = tmp_path / "workspace"
    ws_root.mkdir()
    result = worker.stream_execute_contract(_single_contract(), str(ws_root))

    assert result.evidence.get("failed_during_streaming") is True
    assert result.evidence.get("partial_content_lengths", {}).get("task-impl-ctr-e15-001", -1) == 0
    # Partial content must NOT be certified as the final artifact.
    assert not (ws_root / "src/app/main.py").exists()
    # The structured failure must record the unsupported-streaming reason.
    failures = result.evidence.get("failures", [])
    assert any(f.get("error_message") == "streaming_unsupported" for f in failures)
