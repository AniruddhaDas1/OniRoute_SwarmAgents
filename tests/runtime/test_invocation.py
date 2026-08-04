import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from runtime.invocation.adapters import OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.engine import InvocationEngine
from runtime.invocation.request import InvocationRequest
from runtime.models import ModelManager, SelectionRequest

ROOT=Path(__file__).parents[2]

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path.endswith("chat/completions"):payload={"id":"x","choices":[{"message":{"content":"hello"},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":2,"total_tokens":3}}
        else:payload={"message":{"content":"hello"},"done":True,"done_reason":"stop","prompt_eval_count":1,"eval_count":2}
        data=json.dumps(payload).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
    def log_message(self,*args):pass

def server():
    http=HTTPServer(("127.0.0.1",0),Handler);threading.Thread(target=http.serve_forever,daemon=True).start();return http

def test_openai_compatible_and_ollama_adapters():
    http=server();endpoint=f"http://127.0.0.1:{http.server_port}"
    manager=ModelManager(ROOT/"config/models.yaml");model=manager.resolver.find_model("default-local");request=InvocationRequest(prompt="Hello")
    assert OpenAICompatibleAdapter(endpoint).invoke(model,request).text=="hello";assert OllamaAdapter(endpoint).invoke(model,request).text=="hello";http.shutdown()

def test_invocation_router_dispatch_and_streaming():
    http=server();endpoint=f"http://127.0.0.1:{http.server_port}";manager=ModelManager(ROOT/"config/models.yaml");dispatcher=InvocationDispatcher();dispatcher.register("local-process",OpenAICompatibleAdapter(endpoint));engine=InvocationEngine(manager,dispatcher)
    response=engine.invoke(InvocationRequest(prompt="Hi"),SelectionRequest());assert response.text=="hello";assert list(engine.stream(InvocationRequest(prompt="Hi"),SelectionRequest()))==["hello"];http.shutdown()

def test_invocation_cli_help():
    runner=CliRunner();result=runner.invoke(app,["--help"]);tested=runner.invoke(app,["models","test"])
    assert result.exit_code==0;assert "invoke" in result.stdout
    assert tested.exit_code==0;assert "no network probe" in tested.stdout
