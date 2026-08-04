from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from runtime.execution.ai import AIStepRunner
from runtime.execution.engine import WorkflowEngine
from runtime.invocation.adapters import OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.engine import InvocationEngine
from runtime.loader import RepositoryLoader
from runtime.models import ModelManager
from tests.runtime.test_invocation import server

ROOT=Path(__file__).parents[2]

def test_ai_step_execution_model_resolution_and_history():
    http=server();manager=ModelManager(ROOT/"config/models.yaml");dispatcher=InvocationDispatcher();dispatcher.register("local-process",OpenAICompatibleAdapter(f"http://127.0.0.1:{http.server_port}"))
    engine=WorkflowEngine(RepositoryLoader(ROOT).load());engine.ai_runner=AIStepRunner(InvocationEngine(manager,dispatcher),"Automatic")
    result=engine.run("rest-api-design");assert result.ai_trace;assert result.ai_trace[0]["model"]=="local-metadata-placeholder";assert result.ai_trace[0]["provider"]=="custom";assert result.ai_trace[0]["usage"]["total_tokens"]==3;http.shutdown()

def test_approval_dry_run_is_visible():
    engine=WorkflowEngine(RepositoryLoader(ROOT).load());result=engine.run("rest-api-design")
    assert result.ai_trace[0]["approval"]=="Dry Run";assert result.ai_trace[0]["status"]=="Skipped"

def test_cli_explain_and_trace():
    runner=CliRunner();explained=runner.invoke(app,["explain","workflow","rest-api-design","--repository-root",str(ROOT)]);execution=runner.invoke(app,["explain","execution","--repository-root",str(ROOT)]);trace=runner.invoke(app,["trace","--repository-root",str(ROOT)])
    assert explained.exit_code==0;assert "Selected Model" in explained.stdout
    assert execution.exit_code==0;assert trace.exit_code==0
