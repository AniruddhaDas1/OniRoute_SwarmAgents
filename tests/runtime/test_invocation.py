import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from runtime.invocation.adapters import OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.engine import InvocationEngine
from runtime.invocation.request import InvocationRequest
from runtime.models import ModelManager, SelectionRequest

ROOT=Path(__file__).parents[2]

# Captures the last request payload sent by an adapter so tests can assert
# that streaming flags and metadata propagate to the provider.
_last_request_payload: dict = {}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b"{}"
        _last_request_payload.clear()
        try:
            _last_request_payload.update(json.loads(body) if body else {})
        except Exception:
            pass

        if self.path.endswith("chat/completions"):
            if _last_request_payload.get("stream"):
                self._stream_openai_sse()
            else:
                payload = {"id": "x", "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}
                self._send_json(payload)
        else:
            payload = {"message": {"content": "hello"}, "done": True, "done_reason": "stop", "prompt_eval_count": 1, "eval_count": 2}
            self._send_json(payload)

    def _send_json(self, payload):
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _stream_openai_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Connection", "close")
        self.end_headers()
        events = [
            json.dumps({"id": "x", "object": "chat.completion.chunk", "created": 1, "choices": [{"index": 0, "delta": {"content": "hel"}, "finish_reason": None}]}),
            json.dumps({"id": "x", "object": "chat.completion.chunk", "created": 1, "choices": [{"index": 0, "delta": {"content": "lo"}, "finish_reason": None}]}),
            json.dumps({"id": "x", "object": "chat.completion.chunk", "created": 1, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}),
        ]
        for ev in events:
            self.wfile.write(f"data: {ev}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *args):
        pass


def server():
    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    return http


def test_openai_compatible_and_ollama_adapters():
    http = server(); endpoint = f"http://127.0.0.1:{http.server_port}"
    manager = ModelManager(ROOT / "config/models.yaml"); model = manager.resolver.find_model("default-local"); request = InvocationRequest(prompt="Hello")
    assert OpenAICompatibleAdapter(endpoint).invoke(model, request).text == "hello"; assert OllamaAdapter(endpoint).invoke(model, request).text == "hello"; http.shutdown()


def test_invocation_router_dispatch_and_streaming():
    http = server(); endpoint = f"http://127.0.0.1:{http.server_port}"; manager = ModelManager(ROOT / "config/models.yaml"); dispatcher = InvocationDispatcher(); dispatcher.register("local-process", OpenAICompatibleAdapter(endpoint)); engine = InvocationEngine(manager, dispatcher)
    response = engine.invoke(InvocationRequest(prompt="Hi"), SelectionRequest()); assert response.text == "hello"
    chunks = list(engine.stream(InvocationRequest(prompt="Hi"), SelectionRequest()))
    # Real SSE deltas must reconstruct the content; [DONE] must not become a chunk.
    assert [c.delta for c in chunks] == ["hel", "lo", ""]
    assert "".join(c.delta for c in chunks) == "hello"
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].usage.total_tokens == 3
    assert chunks[-1].provider == "custom"
    assert chunks[-1].model == "local-metadata-placeholder"
    assert _last_request_payload.get("stream") is True
    http.shutdown()


def test_invocation_cli_help():
    runner = CliRunner(); result = runner.invoke(app, ["--help"]); tested = runner.invoke(app, ["models", "test"])
    assert result.exit_code == 0; assert "invoke" in result.stdout
    assert tested.exit_code == 0; assert "no network probe" in tested.stdout
