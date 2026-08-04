from pathlib import Path

import yaml

from runtime.loader import RepositoryLoader
from runtime.registry import RegistryBuilder
from runtime.models import MetadataRecord
from runtime.resolver import Resolver
from runtime.validator import ValidationEngine
from typer.testing import CliRunner
from cli.main import app
from runtime.context.builder import ContextBuilder
from runtime.context.filter import ContextFilter
from runtime.context.router import ContextRouter
from runtime.context.serializer import ContextSerializer
from runtime.execution.engine import WorkflowEngine
from runtime.execution.executor import DeterministicExecutor
from runtime.execution.state import ExecutionStatus


ROOT = Path(__file__).parents[2]


def test_repository_loading_and_registry_creation():
    registry = RepositoryLoader(ROOT).load()
    assert registry.agents
    assert registry.skills
    assert len(registry.workflows) == 20
    assert registry.registry_records


def test_yaml_validation_and_registry_references():
    registry = RepositoryLoader(ROOT).load()
    report = ValidationEngine(ROOT).validate(registry)
    assert report.valid, report.errors


def test_duplicate_detection(tmp_path):
    builder = RegistryBuilder(tmp_path)
    record = MetadataRecord(id="same", kind="skill", path=tmp_path / "one.yaml", data={})
    builder.register(record)
    builder.register(record.model_copy(update={"path": tmp_path / "two.yaml"}))
    assert "skill:same" in builder.registry.duplicates


def test_reference_validation(tmp_path):
    (tmp_path / "workflows/official/example").mkdir(parents=True)
    (tmp_path / "workflows/registry").mkdir(parents=True)
    (tmp_path / "workflows/specification").mkdir(parents=True)
    (tmp_path / "workflows/official/example/workflow.yaml").write_text("workflow_id: example\n", encoding="utf-8")
    (tmp_path / "workflows/specification/WORKFLOW_SCHEMA.yaml").write_text("required: [workflow_id]\n", encoding="utf-8")
    index = {"workflows": [{"workflow_id": "missing"}]}
    (tmp_path / "workflows/registry/WORKFLOW_INDEX.yaml").write_text(yaml.safe_dump(index), encoding="utf-8")
    report = ValidationEngine(tmp_path).validate(RepositoryLoader(tmp_path).load())
    assert any(issue.code == "broken_reference" for issue in report.errors)


def test_read_only_resolver():
    resolver = Resolver(RepositoryLoader(ROOT).load())
    assert resolver.find_workflow("rest-api-design") is not None
    assert resolver.search_by_category("Backend")


def test_relationship_graph_creation():
    resolver = Resolver(RepositoryLoader(ROOT).load())
    assert resolver.graph.number_of_nodes() >= 20
    assert len(resolver.graph.nodes) == len(set(resolver.graph.nodes))
    assert resolver.workflow_relationships("rest-api-design")


def test_cli_inspection_and_search():
    runner = CliRunner()
    inspected = runner.invoke(app, ["inspect", "workflow", "rest-api-design", "--repository-root", str(ROOT)])
    searched = runner.invoke(app, ["search", "Backend", "--repository-root", str(ROOT)])
    assert inspected.exit_code == 0, inspected.stdout
    assert "REST API Design" in inspected.stdout
    assert searched.exit_code == 0, searched.stdout


def test_context_creation_and_contracts():
    registry = RepositoryLoader(ROOT).load(); context = ContextBuilder(registry).workflow("rest-api-design")
    assert context.kind == "workflow"; assert context.context_id == "workflow:rest-api-design"
    assert ContextSerializer.from_dict(type(context), ContextSerializer.to_dict(context)) == context


def test_context_routing_and_filtering():
    registry = RepositoryLoader(ROOT).load(); resolver = Resolver(registry)
    plan = ContextRouter(resolver).plan("rest-api-design")
    assert plan.workflow_id == "rest-api-design"; assert plan.steps
    context = ContextBuilder(registry).workflow("rest-api-design")
    filtered = ContextFilter().apply(context, allow={"category"}, summarize=True)
    assert "category" in filtered.data and "_summary" in filtered.data


def test_context_cli_inspection():
    result = CliRunner().invoke(app, ["context", "workflow", "rest-api-design", "--repository-root", str(ROOT)])
    assert result.exit_code == 0, result.stdout
    assert "workflow:rest-api-design" in result.stdout


def test_execution_planning_is_deterministic():
    engine = WorkflowEngine(RepositoryLoader(ROOT).load())
    first = engine.plan("rest-api-design"); second = engine.plan("rest-api-design")
    assert first == second; assert [step.execution_order for step in first.steps] == [1, 2, 3, 4, 5]


def test_execution_state_artifacts_history_and_events():
    engine = WorkflowEngine(RepositoryLoader(ROOT).load()); result = engine.run("rest-api-design")
    assert result.status == ExecutionStatus.COMPLETED
    assert all(step.status == ExecutionStatus.COMPLETED for step in result.plan.steps)
    assert any(step.result == DeterministicExecutor.PLACEHOLDER for step in result.plan.steps)
    assert len(result.artifacts) == 6; assert len(engine.history.all()) == 1
    assert engine.events.events[0].type == "WorkflowStarted"; assert engine.events.events[-1].type == "WorkflowCompleted"


def test_execution_cli_commands():
    runner = CliRunner()
    planned = runner.invoke(app, ["plan", "workflow", "rest-api-design", "--repository-root", str(ROOT)])
    ran = runner.invoke(app, ["run", "workflow", "rest-api-design", "--repository-root", str(ROOT)])
    assert planned.exit_code == 0, planned.stdout; assert "Resolve declared" in planned.stdout
    assert ran.exit_code == 0, ran.stdout; assert "Placeholder: AI execution" in ran.stdout
