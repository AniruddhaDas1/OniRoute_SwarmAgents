from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.validator import ValidationEngine
from runtime.context.builder import ContextBuilder
from runtime.context.serializer import ContextSerializer
from runtime.execution.engine import WorkflowEngine
from runtime.models import Capability, ModelManager, SelectionRequest
from runtime.tools import Permission, PermissionPolicy, ToolCapability, ToolCatalog, ToolSelectionRequest
from runtime.tools.resolver import ToolResolver
from runtime.tools.selection import ToolSelector

app = typer.Typer(help="Local OniRoute repository diagnostics.")
list_app = typer.Typer(help="List repository metadata.")
inspect_app = typer.Typer(help="Inspect one metadata record.")
context_app = typer.Typer(help="Inspect deterministic context metadata.")
run_app = typer.Typer(help="Run deterministic local workflows.")
plan_app = typer.Typer(help="Build deterministic execution plans.")
app.add_typer(list_app, name="list")
app.add_typer(inspect_app, name="inspect")
app.add_typer(context_app, name="context")
app.add_typer(run_app, name="run")
app.add_typer(plan_app, name="plan")
_session_engines: dict[str, WorkflowEngine] = {}
console = Console()


def _resolver(root: Path) -> Resolver:
    return Resolver(RepositoryLoader(root).load())


def _engine(root: Path) -> WorkflowEngine:
    key = str(root.resolve())
    if key not in _session_engines: _session_engines[key] = WorkflowEngine(RepositoryLoader(root).load())
    return _session_engines[key]

def _models(root: Path) -> ModelManager: return ModelManager(root / "config/models.yaml")
def _tools(root:Path):
    config=yaml.safe_load((root/"config/tools.yaml").read_text(encoding="utf-8")) or {};registry=ToolCatalog.load(root/"config/tools.yaml");policy=PermissionPolicy({Permission(item) for item in config.get("permission_policy",[])})
    return registry,ToolResolver(registry),ToolSelector(registry,policy,tuple(config.get("preferred_local_tools",[])))


def _table(records):
    table = Table("ID", "Kind", "Name")
    for record in records:
        table.add_row(record.id, record.kind, str(record.data.get("display_name") or record.data.get("name") or record.data.get("id") or ""))
    console.print(table)


@app.command()
def doctor(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)) -> None:
    """Load and validate the local OniRoute repository."""
    config_path = repository_root / "config/default.yaml"
    if config_path.exists():
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
    registry = RepositoryLoader(repository_root).load()
    report = ValidationEngine(repository_root).validate(registry)
    table = Table(title="OniRoute Repository")
    table.add_column("Record type"); table.add_column("Count", justify="right")
    for name, count in registry.statistics().items(): table.add_row(name.replace("_", " ").title(), str(count))
    console.print(table)
    console.print(f"Validation: [{'green' if report.valid else 'red'}]{'PASS' if report.valid else 'FAIL'}[/]")
    console.print(f"Errors: {len(report.errors)}  Warnings: {len(report.warnings)}  Duplicates: {len(registry.duplicates)}")
    if not report.valid: raise typer.Exit(1)


@list_app.command("agents")
def list_agents(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)): _table([*_resolver(repository_root).registry.agents.values(), *_resolver(repository_root).registry.sub_agents.values()])

@list_app.command("skills")
def list_skills(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)): _table(_resolver(repository_root).registry.skills.values())

@list_app.command("workflows")
def list_workflows(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)): _table(_resolver(repository_root).registry.workflows.values())

def _inspect(kind: str, identifier: str, root: Path):
    resolver = _resolver(root); record = getattr(resolver, f"find_{kind}")(identifier)
    if record is None: raise typer.BadParameter(f"Unknown {kind}: {identifier}")
    console.print_json(data=record.data)

@inspect_app.command("agent")
def inspect_agent(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)): _inspect("agent", identifier, repository_root)
@inspect_app.command("workflow")
def inspect_workflow(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)): _inspect("workflow", identifier, repository_root)
@inspect_app.command("skill")
def inspect_skill(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)): _inspect("skill", identifier, repository_root)

@inspect_app.command("context")
def inspect_context(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    registry = RepositoryLoader(repository_root).load(); context = ContextBuilder(registry).workflow(identifier)
    console.print_json(data=ContextSerializer.to_dict(context))

@context_app.command("workflow")
def context_workflow(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    registry = RepositoryLoader(repository_root).load(); context = ContextBuilder(registry).workflow(identifier)
    console.print(f"Context: {context.context_id}  Relationships: {len(context.relationships)}  Artifacts: {len(context.artifacts)}  Dependencies: {len(context.dependencies)}  Estimated size: {context.estimated_size} bytes")

@context_app.command("agent")
def context_agent(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    context = ContextBuilder(RepositoryLoader(repository_root).load()).agent(identifier)
    console.print_json(data=ContextSerializer.to_dict(context))

@context_app.command("skill")
def context_skill(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    context = ContextBuilder(RepositoryLoader(repository_root).load()).skill(identifier)
    console.print_json(data=ContextSerializer.to_dict(context))

@app.command()
def search(query: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    _table(_resolver(repository_root).search(query))

@plan_app.command("workflow")
def plan_workflow(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    plan = _engine(repository_root).plan(identifier); table = Table("Order", "Step", "Agent", "Skill", "Status")
    for step in plan.steps: table.add_row(str(step.execution_order), step.description, step.agent or "—", step.skill or "—", step.status)
    console.print(table)

@run_app.command("workflow")
def run_workflow(identifier: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    result = _engine(repository_root).run(identifier)
    console.print(f"Execution: {result.execution_id}  Status: [green]{result.status}[/]  Artifacts: {len(result.artifacts)}")
    for step in result.plan.steps: console.print(f"{step.execution_order}. {step.description}: {step.result}")

@app.command()
def history(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    table = Table("Execution", "Workflow", "Status")
    for item in _engine(repository_root).history.all(): table.add_row(item.execution_id, item.workflow_id, item.status)
    console.print(table)

@app.command()
def events(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    table = Table("Type", "Execution", "Subject")
    for event in _engine(repository_root).events.events: table.add_row(event.type, event.execution_id, event.subject_id)
    console.print(table)

@app.command("models")
def list_models(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    table=Table("ID","Name","Provider","Protocol","Status")
    for item in _models(repository_root).registry.models.values():table.add_row(item.id,item.display_name,item.provider,item.protocol,item.status)
    console.print(table)

@app.command("providers")
def list_providers(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    table=Table("ID","Name","Status","Local")
    for item in _models(repository_root).registry.providers.values():table.add_row(item.id,item.display_name,item.status,"yes" if item.local else "no")
    console.print(table)

@app.command("capabilities")
def list_capabilities():
    for item in Capability:console.print(item.value)

@inspect_app.command("model")
def inspect_model(identifier:str,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    item=_models(repository_root).resolver.find_model(identifier)
    if not item:raise typer.BadParameter(f"Unknown model: {identifier}")
    console.print_json(data=item.model_dump(mode="json"))

@inspect_app.command("provider")
def inspect_provider(identifier:str,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    item=_models(repository_root).resolver.find_provider(identifier)
    if not item:raise typer.BadParameter(f"Unknown provider: {identifier}")
    console.print_json(data=item.model_dump(mode="json"))

@app.command("recommend-model")
def recommend_model(capability:list[Capability]=typer.Option(...),local:bool=False,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    manager=_models(repository_root); item=manager.select_best_model(SelectionRequest(capabilities=frozenset(capability),local_only=local,local_preference=manager.config.get("local_first",False)))
    console.print_json(data=item.model_dump(mode="json"))

@app.command("tools")
def list_tools(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    registry,_,_=_tools(repository_root);table=Table("ID","Name","Protocol","Trust","Health")
    for item in registry.tools.values():table.add_row(item.id,item.display_name,item.protocol,item.trust,item.health)
    console.print(table)

@app.command("mcp")
def list_mcp(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    registry,_,_=_tools(repository_root);table=Table("ID","Name","Transport","Health")
    for item in registry.mcp_servers.values():table.add_row(item.id,item.display_name,item.transport,item.health)
    console.print(table)

@inspect_app.command("tool")
def inspect_tool(identifier:str,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    _,resolver,_=_tools(repository_root);item=resolver.find_tool(identifier)
    if not item:raise typer.BadParameter(f"Unknown tool: {identifier}")
    console.print_json(data=item.model_dump(mode="json"))

@inspect_app.command("mcp")
def inspect_mcp(identifier:str,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    _,resolver,_=_tools(repository_root);item=resolver.find_mcp(identifier)
    if not item:raise typer.BadParameter(f"Unknown MCP server: {identifier}")
    console.print_json(data=item.model_dump(mode="json"))

@app.command("recommend-tool")
def recommend_tool(capability:list[ToolCapability]=typer.Option(...),repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    _,_,selector=_tools(repository_root);item=selector.recommend(ToolSelectionRequest(capabilities=frozenset(capability)))
    console.print_json(data=item.model_dump(mode="json"))

if __name__ == "__main__": app()
