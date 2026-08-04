import json
from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from runtime.optimization import OptimizationEngine, OptimizationRequest
from runtime.optimization.artifact_optimizer import optimize_artifact
from runtime.optimization.benchmark import benchmark
from runtime.optimization.conversation_optimizer import optimize_conversation
from runtime.optimization.plugins import PluginRegistry
from runtime.optimization.prompt_optimizer import optimize_prompt
from runtime.optimization.repository_optimizer import lookup_symbols
from runtime.optimization.skill_optimizer import optimize_skills
from runtime.optimization.terminal_optimizer import summarize_terminal
from runtime.loader import RepositoryLoader
from runtime.execution.engine import WorkflowEngine

ROOT = Path(__file__).parents[2]


def test_context_optimization_preserves_protected_content():
    request = OptimizationRequest(
        source={"required": "keep", "copy": "keep", "empty": "", "useful": "data"},
        protected=frozenset({"required"}),
    )
    result = OptimizationEngine().optimize(request)
    assert result.envelope.payload == {"required": "keep", "useful": "data"}
    assert result.report.validated
    assert set(result.report.removed) == {"copy", "empty"}
    assert result.report.measurements.after_bytes < result.report.measurements.before_bytes


def test_prompt_skill_artifact_terminal_and_conversation_optimizers():
    prompt, actions, _ = optimize_prompt("  Explain   this\n clearly  ", budget=14)
    assert prompt == "Explain this c"
    assert "prompt budgeting" in actions
    skills, _, removed = optimize_skills([{"id": "one"}, {"id": "one"}, {"id": "two"}])
    assert [item["id"] for item in skills] == ["one", "two"] and removed == ["one"]
    assert optimize_artifact("# Title  \n\nBody  ", "markdown") == "# Title\nBody"
    assert optimize_artifact({"value": [1, 2]}, "json") == {"value": [1, 2]}
    summary = summarize_terminal("one\ntwo\n", "failure\n", "test")
    assert summary["stdout_lines"] == 2 and summary["stderr"] == ["failure"]
    messages, removed_messages = optimize_conversation([{"role": "user", "content": "a"}] * 2, 1)
    assert len(messages) == 1 and removed_messages


def test_repository_lookup_uses_native_ast(tmp_path: Path):
    source = tmp_path / "sample.py"
    source.write_text("def target_function():\n    pass\n\nclass TargetClass:\n    pass\n", encoding="utf-8")
    matches = lookup_symbols(tmp_path, "target")
    assert {(item["name"], item["kind"]) for item in matches} == {
        ("target_function", "FunctionDef"),
        ("TargetClass", "ClassDef"),
    }


def test_plugins_are_optional_and_benchmark_is_generated():
    plugins = {plugin.id: plugin for plugin in PluginRegistry().discover()}
    assert plugins["native"].health == "Healthy" and not plugins["native"].optional
    assert plugins["rtk"].optional and plugins["rtk"].health == "Unknown"
    optimized, record = benchmark("prompt", lambda value: optimize_prompt(value)[0], "  hello   world  ")
    assert optimized == "hello world"
    assert record.results[0].after_bytes < record.results[0].before_bytes


def test_optimization_cli_commands(tmp_path: Path):
    (tmp_path / "module.py").write_text("def searchable():\n    return True\n", encoding="utf-8")
    runner = CliRunner()
    commands = [
        ["optimize", "context", json.dumps({"a": "same", "b": "same"})],
        ["optimize", "prompt", "  hello   world  "],
        ["optimize", "repository", "searchable", "--repository-root", str(tmp_path)],
        ["optimize", "artifact", "# Title  \n\nBody", "--kind", "markdown"],
        ["optimize", "terminal", "--stdout", "ok\nok"],
        ["optimize", "conversation", json.dumps([{"role": "user", "content": "hello"}])],
        ["optimize", "benchmark"],
        ["optimize", "report", "--repository-root", str(ROOT)],
        ["optimize", "explain", "--repository-root", str(ROOT)],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output


def test_execution_integration_records_governed_optimization():
    engine = WorkflowEngine(RepositoryLoader(ROOT).load())
    workflow_id = next(iter(engine.registry.workflows))
    result = engine.run(workflow_id)
    trace = result.report["optimization"][0]
    assert trace["requested"] is True
    assert trace["applied"] is False
    assert trace["bypass_reason"] == "dry run"
    bypassed = engine.run(workflow_id, optimize=False)
    assert bypassed.report["optimization"][0]["bypass_reason"] == "explicit bypass"
