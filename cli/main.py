import json
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.validator import ValidationEngine
from runtime.workspace import WorkspaceManager
from runtime.context.builder import ContextBuilder
from runtime.context.serializer import ContextSerializer
from runtime.execution.engine import WorkflowEngine
from runtime.models import Capability, ModelManager, SelectionRequest
from runtime.tools import Permission, PermissionPolicy, ToolCapability, ToolCatalog, ToolSelectionRequest
from runtime.tools.resolver import ToolResolver
from runtime.tools.selection import ToolSelector
from runtime.invocation.adapters import OllamaAdapter, OpenAICompatibleAdapter
from runtime.invocation.dispatcher import InvocationDispatcher
from runtime.invocation.engine import InvocationEngine
from runtime.invocation.request import InvocationRequest
from runtime.governance import AuditEngine,BudgetLimits,BudgetTracker,GovernanceRequest,PolicyEngine
from runtime.optimization import OptimizationEngine, OptimizationRequest
from runtime.optimization.artifact_optimizer import optimize_artifact
from runtime.optimization.benchmark import benchmark
from runtime.optimization.conversation_optimizer import optimize_conversation
from runtime.optimization.prompt_optimizer import optimize_prompt
from runtime.optimization.repository_optimizer import lookup_symbols
from runtime.optimization.terminal_optimizer import summarize_terminal

app = typer.Typer(help="Local OniRoute repository diagnostics.")
list_app = typer.Typer(help="List repository metadata.")
inspect_app = typer.Typer(help="Inspect one metadata record.")
context_app = typer.Typer(help="Inspect deterministic context metadata.")
run_app = typer.Typer(help="Run deterministic local workflows.")
plan_app = typer.Typer(help="Build deterministic execution plans.")
models_app = typer.Typer(help="List and test model metadata.", invoke_without_command=True)
explain_app = typer.Typer(help="Explain Workflow and execution resolution.")
policy_app = typer.Typer(help="Inspect governance policy.",invoke_without_command=True)
optimize_app = typer.Typer(help="Optimize context deterministically before invocation.")
app.add_typer(list_app, name="list")
app.add_typer(inspect_app, name="inspect")
app.add_typer(context_app, name="context")
app.add_typer(run_app, name="run")
app.add_typer(plan_app, name="plan")
app.add_typer(models_app, name="models")
app.add_typer(explain_app, name="explain")
app.add_typer(policy_app, name="policy")
app.add_typer(optimize_app, name="optimize")
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

def _governance(root:Path):
    config=yaml.safe_load((root/"config/policies.yaml").read_text(encoding="utf-8")) or {};audit=AuditEngine();budgets=BudgetTracker(BudgetLimits(**config.get("budget_limits",{})));return config,PolicyEngine(config,budgets,audit)


def _table(records):
    table = Table("ID", "Kind", "Name")
    for record in records:
        table.add_row(record.id, record.kind, str(record.data.get("display_name") or record.data.get("name") or record.data.get("id") or ""))
    console.print(table)


@app.command("workspace")
def workspace(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
) -> None:
    """Discover and display active workspace metadata and project detection."""
    manager = WorkspaceManager()
    ctx = manager.create_context(cwd=repository_root, explicit_workspace=workspace)

    table = Table(title="OniRoute Workspace Discovery")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")

    table.add_row("Workspace Root", str(ctx.workspace_root))
    table.add_row("Engine Root", str(ctx.engine_root))
    table.add_row("Project Type", str(ctx.project_type.value if hasattr(ctx.project_type, 'value') else ctx.project_type))
    method_str = ctx.discovery_method.name.lower() if hasattr(ctx.discovery_method, 'name') else str(ctx.discovery_source)
    table.add_row("Discovery Method", method_str)
    status_str = ctx.validation_status.value if hasattr(ctx.validation_status, 'value') else str(ctx.validation_status)
    table.add_row("Validation Status", status_str)

    console.print(table)


@app.command()
def doctor(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
) -> None:
    """Load and validate the local OniRoute repository and workspace."""
    config_path = repository_root / "config/default.yaml"
    if config_path.exists():
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
    registry = RepositoryLoader(repository_root).load()
    report = ValidationEngine(repository_root).validate(registry)

    # Workspace & Engine Discovery Diagnostics
    manager = WorkspaceManager()
    ctx = manager.create_context(cwd=repository_root, explicit_workspace=workspace)

    ws_table = Table(title="Workspace & Engine Context")
    ws_table.add_column("Diagnostic Item", style="bold cyan")
    ws_table.add_column("Status / Detail")

    ws_table.add_row("Workspace", str(ctx.workspace_root))
    ws_table.add_row("Engine", str(ctx.engine_root))
    proj_type_str = ctx.project_type.value if hasattr(ctx.project_type, 'value') else str(ctx.project_type)
    ws_table.add_row("Project", f"{proj_type_str} ({ctx.project_name})")
    val_status_str = ctx.validation_status.value if hasattr(ctx.validation_status, 'value') else str(ctx.validation_status)
    ws_table.add_row("Workspace Status", val_status_str.upper())
    read_only_confirmed = "CONFIRMED" if ctx.is_engine_read_only() else "FAILED"
    ws_table.add_row("Read-only Engine", f"[green]{read_only_confirmed}[/]" if ctx.is_engine_read_only() else f"[red]{read_only_confirmed}[/]")

    console.print(ws_table)

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
def run_workflow(identifier: str, optimization: bool | None = typer.Option(None, "--optimization/--no-optimization"), repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    result = _engine(repository_root).run(identifier, optimize=optimization)
    console.print(f"Execution: {result.execution_id}  Status: [green]{result.status}[/]  Artifacts: {len(result.artifacts)}")
    for step in result.plan.steps: console.print(f"{step.execution_order}. {step.description}: {step.result}")

@explain_app.command("workflow")
def explain_workflow(identifier:str,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    engine=_engine(repository_root)
    plan=engine.plan(identifier);console.print(f"Workflow: {identifier}")
    for step in plan.steps:console.print(f"{step.execution_order}. Agent={step.agent or '—'} Skill={step.skill or '—'} Context={step.context}")
    manager=_models(repository_root);model=manager.select_best_model(SelectionRequest());console.print(f"Selected Model={model.id} Provider={model.provider} Protocol={model.protocol} Capabilities={','.join(sorted(x.value for x in model.capabilities))}")

@explain_app.command("execution")
def explain_execution(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    records=_engine(repository_root).history.all();console.print_json(data=records[-1].model_dump(mode="json") if records else {"status":"No execution history"})

@app.command("trace")
def trace(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    for event in _engine(repository_root).events.events:console.print(f"{event.timestamp.isoformat()} {event.type} {event.subject_id}")

@policy_app.callback()
def policy_summary(ctx:typer.Context,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    if ctx.invoked_subcommand is not None:return
    config,_=_governance(repository_root);console.print_json(data={"allowed_models":config.get("allowed_models"),"allowed_tools":config.get("allowed_tools"),"approval_defaults":config.get("approval_defaults"),"risk_threshold":config.get("risk_threshold")})

@policy_app.command("workflow")
def policy_workflow(identifier:str,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    config,engine=_governance(repository_root);result=engine.evaluate(GovernanceRequest(kind="workflow",workflow=identifier));console.print_json(data={"workflow":identifier,"decision":result.model_dump(mode="json"),"configuration":{"approval":config.get("approval_defaults"),"token_limit":config.get("token_limit")}})

@app.command("audit")
def audit(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    _,engine=_governance(repository_root);console.print_json(data=[item.model_dump(mode="json") for item in engine.audit.records])

@app.command("approvals")
def approvals(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    config,_=_governance(repository_root);console.print_json(data={"default":config.get("approval_defaults"),"overrides":config.get("approval_overrides",{})})

@app.command("permissions")
def permissions(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    config,_=_governance(repository_root);console.print_json(data={"defaults":config.get("permission_defaults"),"security_rules":config.get("security_rules",{})})

@app.command("budget")
def budget(repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    config,engine=_governance(repository_root);console.print_json(data={"limits":config.get("budget_limits",{}),"usage":engine.budgets.snapshot()})

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

@models_app.callback()
def list_models(ctx:typer.Context,repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    if ctx.invoked_subcommand is not None:return
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

@app.command("invoke")
def invoke(prompt:str=typer.Option(...),model:str|None=typer.Option(None),provider:str|None=typer.Option(None),capability:list[Capability]=typer.Option([]),repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    manager=_models(repository_root);dispatcher=InvocationDispatcher();endpoint=manager.config.get("endpoint","http://127.0.0.1:11434")
    dispatcher.register("openai-compatible",OpenAICompatibleAdapter(endpoint));dispatcher.register("ollama",OllamaAdapter(endpoint));dispatcher.register("local-process",OllamaAdapter(endpoint))
    result=InvocationEngine(manager,dispatcher).invoke(InvocationRequest(prompt=prompt),SelectionRequest(capabilities=frozenset(capability),provider=provider),model_id=model)
    console.print(result.text)

@models_app.command("test")
def models_test(): console.print("Model catalog and adapter interfaces available; no network probe performed.")

@optimize_app.command("context")
def optimize_context(value: str = typer.Argument(..., help="Context as a JSON object."), budget: int | None = typer.Option(None), protected: list[str] = typer.Option([])):
    source = json.loads(value)
    if not isinstance(source, dict): raise typer.BadParameter("Context must be a JSON object")
    result = OptimizationEngine().optimize(OptimizationRequest(source=source, budget=budget, protected=frozenset(protected)))
    console.print_json(data=result.model_dump(mode="json"))

@optimize_app.command("prompt")
def optimize_prompt_command(prompt: str, budget: int | None = typer.Option(None)):
    optimized, actions, removed = optimize_prompt(prompt, budget)
    console.print_json(data={"optimized": optimized, "actions": actions, "removed": removed})

@optimize_app.command("repository")
def optimize_repository(query: str, repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    console.print_json(data={"query": query, "matches": lookup_symbols(repository_root, query)})

@optimize_app.command("artifact")
def optimize_artifact_command(value: str, kind: str = typer.Option("markdown")):
    source = json.loads(value) if kind == "json" else value
    console.print_json(data={"kind": kind, "optimized": optimize_artifact(source, kind)})

@optimize_app.command("terminal")
def optimize_terminal(stdout: str = typer.Option(""), stderr: str = typer.Option(""), kind: str = typer.Option("command")):
    console.print_json(data=summarize_terminal(stdout, stderr, kind))

@optimize_app.command("conversation")
def optimize_conversation_command(value: str = typer.Argument(..., help="Messages as a JSON array."), max_messages: int | None = typer.Option(None)):
    messages = json.loads(value)
    if not isinstance(messages, list): raise typer.BadParameter("Conversation must be a JSON array")
    optimized, removed = optimize_conversation(messages, max_messages)
    console.print_json(data={"optimized": optimized, "removed": removed})

@optimize_app.command("benchmark")
def optimize_benchmark(value: str = typer.Option('{"required":"keep","duplicate":"keep","empty":""}')):
    source = json.loads(value)
    result, record = benchmark("context", lambda item: OptimizationEngine().optimize(OptimizationRequest(source=item)).envelope.payload, source)
    console.print_json(data={"optimized": result, "benchmark": record.model_dump(mode="json")})

@optimize_app.command("report")
def optimize_report(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    records=_engine(repository_root).history.all(); traces=[item for record in records for item in record.report.get("optimization",())]
    console.print_json(data={"executions":len(records),"optimization_records":len(traces),"records":traces})

@optimize_app.command("explain")
def optimize_explain(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    manager=_models(repository_root); policy=manager.config.get("optimization",{})
    console.print_json(data={"pipeline":"Context Engine -> ICOE -> UMAL -> Invocation","policy":policy,"native_plugin":"Healthy","optional_plugins":{"rtk":"Unavailable","ast":"Unavailable","repository-graph":"Unavailable"},"bypass":"oniroute run workflow <id> --no-optimization"})

if __name__ == "__main__": app()
