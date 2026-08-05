import json
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.validator import ValidationEngine
from runtime.workspace import ArtifactRouter, ReportStorage, WorkspaceManager, WorkspaceStorage
from runtime.workspace import SessionStorage, ExecutionHistoryStorage, TraceStorage, LogStorage
from runtime.workspace import WorkspaceContext, WorkspaceIntelligence, WorkspaceState
from runtime.workspace import RepositoryContext, RepositoryIntelligence
from runtime.workspace import EngineeringExecutionPlan, EngineeringPlanGenerator, RepositoryStrategy
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
from runtime.mission import (
    MissionIntake,
    MissionIntakeError,
    MissionOrchestrationError,
    MissionOrchestrator,
    MissionResolutionError,
    MissionResolver,
)
from runtime.intent import EmptyRequestError, IntentAnalysisError, IntentAnalyzer, IntentReport
from runtime.agent import AgentExecutionEngine, SessionCoordinator
from runtime.agent.recovery import (
    FailureCategory,
    FailureClassifier,
    RecoveryOrchestrator,
    RetryPolicy,
    ReviewDecision,
)
from runtime.organization import CapabilityResolver, ExecutionBlueprintAssembler, OrganizationAssembler
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillBundlingEngine,
    AgentProfileBuilderEngine,
    SkillSelectionReport,
    RankedSkillReport,
    ExecutionSkillBundleReport,
    ExecutionSkillBundle,
    AgentProfileReport,
    AgentProfile,
)
from runtime.deployment import MissionDeploymentPlan, MissionDeploymentPlanner
from runtime.swarm import AutonomousExecutionEngine, ExecutionTaskQueue, RuntimeExecutionSnapshot, SwarmCoordinationEngine, SwarmExecutionResult, SwarmInitializationEngine
from runtime.scaffold import WorkspaceScaffoldEngine, WorkspaceScaffoldReport, WorkspaceScaffoldError
from runtime.blueprint import ProjectBlueprintEngine, ProjectBlueprintReport, ProjectBlueprintError
from runtime.allocation import ImplementationAllocationEngine, ImplementationAllocationReport, ImplementationAllocationError






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
mission_app = typer.Typer(help="Mission Orchestrator inspection and orchestration commands.", invoke_without_command=True)
skills_app = typer.Typer(help="Automatic skill discovery and reporting.", invoke_without_command=True)
app.add_typer(list_app, name="list")
app.add_typer(inspect_app, name="inspect")
app.add_typer(context_app, name="context")
app.add_typer(run_app, name="run")
app.add_typer(plan_app, name="plan")
app.add_typer(models_app, name="models")
app.add_typer(explain_app, name="explain")
app.add_typer(policy_app, name="policy")
app.add_typer(optimize_app, name="optimize")
app.add_typer(mission_app, name="mission")
app.add_typer(skills_app, name="skills")


_session_engines: dict[str, WorkflowEngine] = {}
console = Console()


def _workspace_meta(root: Path, explicit_workspace: Path | None = None):
    """Resolve workspace metadata for *root*.

    Returns the metadata only when the workspace root is physically separate
    from the engine root (i.e. writes are safe).  Returns ``None`` otherwise,
    indicating an in-memory fallback is required.
    """
    manager = WorkspaceManager()
    ctx = manager.create_context(cwd=root, explicit_workspace=explicit_workspace)
    if ctx.workspace_metadata is not None and ctx.is_engine_read_only():
        return ctx.workspace_metadata
    return None


def _resolver(root: Path) -> Resolver:
    return Resolver(RepositoryLoader(root).load())


def _engine(root: Path, explicit_workspace: Path | None = None) -> WorkflowEngine:
    ws_key = f"::ws::{explicit_workspace.resolve()}" if explicit_workspace else ""
    key = str(root.resolve()) + ws_key
    if key not in _session_engines:
        registry = RepositoryLoader(root).load()
        ws_meta = _workspace_meta(root, explicit_workspace)
        if ws_meta is not None:
            _session_engines[key] = WorkflowEngine(registry, workspace_metadata=ws_meta)
        else:
            _session_engines[key] = WorkflowEngine(registry)
    return _session_engines[key]

def _models(root: Path) -> ModelManager: return ModelManager(root / "config/models.yaml")
def _tools(root:Path):
    config=yaml.safe_load((root/"config/tools.yaml").read_text(encoding="utf-8")) or {};registry=ToolCatalog.load(root/"config/tools.yaml");policy=PermissionPolicy({Permission(item) for item in config.get("permission_policy",[])})
    return registry,ToolResolver(registry),ToolSelector(registry,policy,tuple(config.get("preferred_local_tools",[])))

def _governance(root: Path, explicit_workspace: Path | None = None):
    config=yaml.safe_load((root/"config/policies.yaml").read_text(encoding="utf-8")) or {}
    report_storage = ReportStorage(meta) if (meta := _workspace_meta(root, explicit_workspace)) else None
    budgets=BudgetTracker(BudgetLimits(**config.get("budget_limits",{})))
    audit=AuditEngine(report_storage=report_storage)
    return config, PolicyEngine(config, budgets, audit)


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

    # ── Storage diagnostics ────────────────────────────────────────────
    if ctx.workspace_metadata is not None:
        storage = manager.create_storage(ctx.workspace_metadata)
        sessions = SessionStorage(ctx.workspace_metadata)
        history = ExecutionHistoryStorage(ctx.workspace_metadata)
        traces = TraceStorage(ctx.workspace_metadata)
        logs = LogStorage(ctx.workspace_metadata)

        status_table = Table(title="Workspace Storage")
        status_table.add_column("Item", style="bold cyan")
        status_table.add_column("Value", justify="right")

        status_table.add_row(".oniroute/", str(storage.root))
        status_table.add_row("Sessions", str(sessions.session_count()))
        status_table.add_row("Artifacts", str(storage.count_entries("artifacts")))
        status_table.add_row("History", str(history.count()))
        status_table.add_row("Traces", str(traces.count()))
        status_table.add_row("Logs", str(logs.count()))
        initialized = "YES" if storage.exists() else "NO"
        status_table.add_row("Storage Initialized", f"[green]{initialized}[/]" if storage.exists() else f"[red]{initialized}[/]")

        console.print(status_table)

        # Detailed subdirectory status
        detail = Table(title="Storage Directory Status")
        detail.add_column("Directory", style="bold cyan")
        detail.add_column("Exists", justify="right")
        detail.add_column("Entries", justify="right")
        dir_status = storage.storage_status()
        for name in storage.all_subdir_names:
            exists = dir_status.get(name, False)
            count = storage.count_entries(name) if exists else 0
            mark = "[green]\u2713[/]" if exists else "[dim]\u2014[/]"
            detail.add_row(f".oniroute/{name}/", mark, str(count))
        console.print(detail)

        # ── Runtime statistics ────────────────────────────────────────────
        reports = ReportStorage(ctx.workspace_metadata)
        runtime_table = Table(title="Runtime Statistics")
        runtime_table.add_column("Metric", style="bold cyan")
        runtime_table.add_column("Value", justify="right")
        runtime_table.add_row("Plans", str(storage.count_entries("plans")))
        runtime_table.add_row("Reports", str(reports.count()))
        runtime_table.add_row("Memory", str(storage.count_entries("memory")))
        runtime_table.add_row("Context Snapshots", str(storage.count_entries("context")))
        runtime_table.add_row("Runtime Files", str(storage.count_entries("runtime")))
        runtime_table.add_row("Knowledge", str(storage.count_entries("knowledge")))
        runtime_table.add_row("Cache", str(storage.count_entries("cache")))
        runtime_table.add_row("Approvals", str(storage.count_entries("approvals")))
        runtime_table.add_row("Locks", str(storage.count_entries("locks")))
        console.print(runtime_table)


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

@plan_app.callback(invoke_without_command=True)
def plan_default(
    ctx: typer.Context,
    request: list[str] = typer.Argument(None, help="Natural language request string to plan."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return

    if request and request[0] == "workflow":
        wf_id = request[1] if len(request) > 1 else ""
        plan_workflow(identifier=wf_id, workspace=workspace, repository_root=repository_root)
        return

    raw_prompt = " ".join(request) if request else "Build CRM"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build CRM"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    if json_output:
        console.print_json(data=plan.model_dump(mode="json"))
        return

    table = Table(title=f"Engineering Execution Plan: {plan.plan_id}")
    table.add_column("Category", style="bold cyan")
    table.add_column("Property")
    table.add_column("Value")

    table.add_row("Overview", "Plan ID", plan.plan_id)
    table.add_row("Overview", "Mission ID", plan.mission_id)
    table.add_row("Overview", "Project Goal", plan.project_goal)
    table.add_row("Overview", "Project Type", plan.project_type)

    strat_val = plan.repository_strategy.value if hasattr(plan.repository_strategy, "value") else str(plan.repository_strategy)
    table.add_row("Strategy", "Repository Strategy", strat_val)
    table.add_row("Strategy", "Current State", plan.current_project_state)
    table.add_row("Strategy", "Target State", plan.target_project_state)

    table.add_row("Stack", "Technology Stack", ", ".join(plan.technology_stack) if plan.technology_stack else "None")
    table.add_row("Disciplines", "Required Disciplines", ", ".join(plan.required_disciplines) if plan.required_disciplines else "None")
    table.add_row("Deliverables", "Planned Deliverables", ", ".join(plan.required_deliverables) if plan.required_deliverables else "None")

    table.add_row("Milestones", "High-Level Milestones", f"{len(plan.high_level_milestones)} milestones planned")
    for m in plan.high_level_milestones:
        table.add_row("Milestones", f"Stage {m['step']}: {m['name']}", m["objective"])

    table.add_row("Constraints", "Known Constraints", ", ".join(plan.known_constraints) if plan.known_constraints else "None")
    table.add_row("Risks", "Identified Risks", ", ".join(plan.risks) if plan.risks else "None")
    table.add_row("Missing Info", "Missing Information", ", ".join(plan.missing_information) if plan.missing_information else "None")

    console.print(table)


@plan_app.command("workflow")
def plan_workflow(
    identifier: str,
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    plan = _engine(repository_root, workspace).plan(identifier)
    table = Table("Order", "Step", "Agent", "Skill", "Status")
    for step in plan.steps:
        table.add_row(str(step.execution_order), step.description, step.agent or "—", step.skill or "—", step.status)
    console.print(table)

@run_app.command("workflow")
def run_workflow(
    identifier: str,
    optimization: bool | None = typer.Option(None, "--optimization/--no-optimization"),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    result = _engine(repository_root, workspace).run(identifier, optimize=optimization)
    console.print(f"Execution: {result.execution_id}  Status: [green]{result.status}[/]  Artifacts: {len(result.artifacts)}")
    for step in result.plan.steps:
        console.print(f"{step.execution_order}. {step.description}: {step.result}")

@explain_app.command("workflow")
def explain_workflow(identifier:str,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    engine=_engine(repository_root)
    plan=engine.plan(identifier);console.print(f"Workflow: {identifier}")
    for step in plan.steps:console.print(f"{step.execution_order}. Agent={step.agent or '—'} Skill={step.skill or '—'} Context={step.context}")
    manager=_models(repository_root);model=manager.select_best_model(SelectionRequest());console.print(f"Selected Model={model.id} Provider={model.provider} Protocol={model.protocol} Capabilities={','.join(sorted(x.value for x in model.capabilities))}")

@explain_app.command("execution")
def explain_execution(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Explain the most recent execution, inspecting persisted workspace state."""
    meta = _workspace_meta(repository_root, workspace)
    if meta is not None:
        records = ExecutionHistoryStorage(meta).load_all()
    else:
        records = [r.model_dump(mode="json") for r in _engine(repository_root).history.all()]
    if records:
        console.print_json(data=records[-1])
    else:
        console.print_json(data={"status": "No execution history"})

@app.command("trace")
def trace(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Display execution trace events from persisted workspace state."""
    meta = _workspace_meta(repository_root, workspace)
    if meta is not None:
        trace_storage = TraceStorage(meta)
        for execution_id in trace_storage.list_traces():
            for event in trace_storage.read_trace(execution_id):
                console.print(f"{event.get('timestamp', '')} {event.get('type', '')} {event.get('subject_id', '')}")
    else:
        for event in _engine(repository_root).events.events:
            console.print(f"{event.timestamp.isoformat()} {event.type} {event.subject_id}")


@app.command("traces")
def traces(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Inspect persisted trace event streams in the workspace."""
    meta = _workspace_meta(repository_root, workspace)
    if meta is None:
        console.print_json(data={"error": "No workspace storage available (workspace root equals engine root)"})
        return
    trace_storage = TraceStorage(meta)
    table = Table("Execution ID", "Events")
    for execution_id in trace_storage.list_traces():
        count = len(trace_storage.read_trace(execution_id))
        table.add_row(execution_id, str(count))
    console.print(table)


@app.command("reports")
def reports(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Inspect persisted optimization, audit, and planning reports in the workspace."""
    meta = _workspace_meta(repository_root, workspace)
    if meta is None:
        console.print_json(data={"error": "No workspace storage available (workspace root equals engine root)"})
        return
    report_storage = ReportStorage(meta)
    table = Table("Report ID", "Type")
    for record in report_storage.load_all_reports():
        table.add_row(record.get("report_id", ""), record.get("report_type", ""))
    console.print(table)


@app.command("sessions")
def sessions(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Inspect persisted workspace sessions."""
    meta = _workspace_meta(repository_root, workspace)
    if meta is None:
        console.print_json(data={"error": "No workspace storage available (workspace root equals engine root)"})
        return
    session_storage = SessionStorage(meta)
    table = Table("Session ID", "File Count")
    for session_id in session_storage.list_sessions():
        session_dir = session_storage.sessions_root / session_id
        file_count = len(list(session_dir.iterdir())) if session_dir.is_dir() else 0
        table.add_row(session_id, str(file_count))
    console.print(table)

@policy_app.callback()
def policy_summary(ctx:typer.Context,repository_root:Path=typer.Option(Path.cwd(),exists=True,file_okay=False)):
    if ctx.invoked_subcommand is not None:return
    config,_=_governance(repository_root);console.print_json(data={"allowed_models":config.get("allowed_models"),"allowed_tools":config.get("allowed_tools"),"approval_defaults":config.get("approval_defaults"),"risk_threshold":config.get("risk_threshold")})

@policy_app.command("workflow")
def policy_workflow(
    identifier: str,
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    config, engine = _governance(repository_root, workspace)
    result = engine.evaluate(GovernanceRequest(kind="workflow", workflow=identifier))
    console.print_json(data={"workflow": identifier, "decision": result.model_dump(mode="json"), "configuration": {"approval": config.get("approval_defaults"), "token_limit": config.get("token_limit")}})

@app.command("audit")
def audit(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Inspect persisted governance audit records from the workspace."""
    _, engine = _governance(repository_root, workspace)
    console.print_json(data=[item.model_dump(mode="json") for item in engine.audit.records])

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
def history(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Inspect persisted execution history in the workspace."""
    meta = _workspace_meta(repository_root, workspace)
    if meta is not None:
        records = ExecutionHistoryStorage(meta).load_all()
    else:
        records = [r.model_dump(mode="json") for r in _engine(repository_root).history.all()]
    table = Table("Execution", "Workflow", "Status")
    for record in records:
        table.add_row(str(record.get("execution_id", "")), str(record.get("workflow_id", "")), str(record.get("status", "")))
    console.print(table)

@app.command()
def events(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Inspect execution events from persisted workspace traces."""
    meta = _workspace_meta(repository_root, workspace)
    table = Table("Type", "Execution", "Subject")
    if meta is not None:
        trace_storage = TraceStorage(meta)
        for execution_id in trace_storage.list_traces():
            for event in trace_storage.read_trace(execution_id):
                table.add_row(str(event.get("type", "")), str(event.get("execution_id", "")), str(event.get("subject_id", "")))
    else:
        for event in _engine(repository_root).events.events:
            table.add_row(event.type, event.execution_id, event.subject_id)
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
def optimize_context(
    value: str = typer.Argument(..., help="Context as a JSON object."),
    budget: int | None = typer.Option(None),
    protected: list[str] = typer.Option([]),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    source = json.loads(value)
    if not isinstance(source, dict):
        raise typer.BadParameter("Context must be a JSON object")
    meta = _workspace_meta(repository_root, workspace)
    report_storage = ReportStorage(meta) if meta else None
    result = OptimizationEngine(report_storage).optimize(OptimizationRequest(source=source, budget=budget, protected=frozenset(protected)))
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
def optimize_report(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
):
    """Inspect optimization reports from persisted workspace state."""
    meta = _workspace_meta(repository_root, workspace)
    if meta is not None:
        report_storage = ReportStorage(meta)
        reports = report_storage.load_reports_by_type("optimization")
        traces = []
        for r in reports:
            data = r.get("data", {})
            traces.extend(data.get("optimization_traces", []))
        console.print_json(data={"executions": len(reports), "optimization_records": len(traces), "records": traces})
    else:
        records = _engine(repository_root).history.all()
        traces = [item for record in records for item in record.report.get("optimization", ())]
        console.print_json(data={"executions": len(records), "optimization_records": len(traces), "records": traces})

@optimize_app.command("explain")
def optimize_explain(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)):
    manager=_models(repository_root); policy=manager.config.get("optimization",{})
    console.print_json(data={"pipeline":"Context Engine -> ICOE -> UMAL -> Invocation","policy":policy,"native_plugin":"Healthy","optional_plugins":{"rtk":"Unavailable","ast":"Unavailable","repository-graph":"Unavailable"},"bypass":"oniroute run workflow <id> --no-optimization"})


@mission_app.callback()
def mission_default(
    ctx: typer.Context,
    command: list[str] = typer.Argument(None, help="Natural language mission command."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    if command and "--json" in command:
        json_output = True
        command = [c for c in command if c != "--json"]
    if command and command[0] == "orchestrate":
        mission_orchestrate(command=command[1:], workspace=workspace, json_output=json_output)
        return
    raw_prompt = " ".join(command) if command else "Inspect workspace mission status"
    try:
        intake = MissionIntake()
        mission_request = intake.process_intake(raw_prompt, explicit_workspace=workspace)
        resolver = MissionResolver()
        resolved_mission = resolver.resolve_mission(mission_request)

        if json_output:
            console.print_json(data=resolved_mission.model_dump(mode="json"))
            return

        table = Table(title=f"Resolved Mission: {resolved_mission.mission_id}")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Mission ID", resolved_mission.mission_id)
        table.add_row("Name", resolved_mission.name)
        table.add_row("Primary Goal", resolved_mission.requirements.primary_goal)
        table.add_row("Intent Category", resolved_mission.requirements.intent_category)
        table.add_row("Workspace Root", str(resolved_mission.context.workspace_root))
        table.add_row("Project Type", str(resolved_mission.context.project_type))
        table.add_row("Status", str(resolved_mission.status.current_state.value if hasattr(resolved_mission.status.current_state, "value") else resolved_mission.status.current_state))
        table.add_row("Read-only Engine", "CONFIRMED" if resolved_mission.context.read_only_engine_confirmed else "FAILED")
        table.add_row("Evidence Stages Recorded", str(len(resolved_mission.report.evidence_summary) if resolved_mission.report else 0))

        console.print(table)
    except (MissionIntakeError, MissionResolutionError) as exc:
        console.print(f"[red]Mission Resolution Error:[/] {getattr(exc, 'message', str(exc))}")
        raise typer.Exit(1)


@mission_app.command("orchestrate")
def mission_orchestrate(
    command: list[str] = typer.Argument(None, help="Natural language mission command."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON ExecutionRequest."),
) -> None:
    """Orchestrate a validated Mission and display the prepared ExecutionRequest without executing."""
    if command and "--json" in command:
        json_output = True
        command = [c for c in command if c != "--json"]
    raw_prompt = " ".join(command) if command else "Orchestrate workspace mission"

    try:
        intake = MissionIntake()
        mission_request = intake.process_intake(raw_prompt, explicit_workspace=workspace)
        resolver = MissionResolver()
        resolved_mission = resolver.resolve_mission(mission_request)
        orchestrator = MissionOrchestrator()
        exec_request = orchestrator.orchestrate_mission(resolved_mission)

        if json_output:
            console.print_json(data=exec_request.model_dump(mode="json"))
            return

        table = Table(title=f"Prepared ExecutionRequest: {exec_request.request_id}")
        table.add_column("Component", style="bold cyan")
        table.add_column("Status / Detail")

        table.add_row("Request ID", exec_request.request_id)
        table.add_row("Mission ID", exec_request.mission.mission_id)
        table.add_row("Execution State", str(exec_request.execution_state.value if hasattr(exec_request.execution_state, "value") else exec_request.execution_state).upper())
        table.add_row("Planning Request", f"PREPARED ({exec_request.planning_request.get('primary_goal', '')})")
        table.add_row("Governance Request", f"PREPARED ({exec_request.governance_request.get('approvals', '')})")
        table.add_row("Workspace Preparation", f"PREPARED ({len(exec_request.workspace_metadata)} metadata keys)")
        table.add_row("UMAL Request", f"PREPARED ({len(exec_request.umal_request.get('capabilities_required', []))} capabilities)")
        table.add_row("Invocation Request", f"PREPARED (Streaming: {exec_request.invocation_request.get('streaming', False)})")
        table.add_row("Prepared Evidence Stages", str(len(exec_request.execution_evidence.model_dump(mode="python"))))

        console.print(table)
    except (MissionIntakeError, MissionResolutionError, MissionOrchestrationError) as exc:
        console.print(f"[red]Mission Orchestration Error:[/] {getattr(exc, 'message', str(exc))}")
        raise typer.Exit(1)


@app.command("capability")
def capability_command(
    command: list[str] = typer.Argument(None, help="Natural language command or prompt for capability resolution."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON CapabilityReport."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
) -> None:
    """Resolve and display required engineering capabilities for a mission without execution."""
    if command and "--json" in command:
        json_output = True
        command = [c for c in command if c != "--json"]
    raw_prompt = " ".join(command) if command else "Resolve capabilities for workspace"

    try:
        intake = MissionIntake()
        mission_request = intake.process_intake(raw_prompt, explicit_workspace=workspace)
        resolver = MissionResolver()
        resolved_mission = resolver.resolve_mission(mission_request)
        orchestrator = MissionOrchestrator()
        exec_request = orchestrator.orchestrate_mission(resolved_mission)
        cap_resolver = CapabilityResolver(repository_root=repository_root)
        cap_report = cap_resolver.resolve_capabilities(exec_request)

        if json_output:
            console.print_json(data=cap_report.model_dump(mode="json"))
            return

        table = Table(title=f"Resolved Capability Report: {cap_report.report_id}")
        table.add_column("Capability ID", style="bold cyan")
        table.add_column("Domain", style="bold yellow")
        table.add_column("Capability Name")
        table.add_column("Priority")
        table.add_column("Confidence")
        table.add_column("Dependencies")

        for cap in cap_report.capabilities:
            table.add_row(
                cap.capability_id,
                cap.domain.upper(),
                cap.name,
                cap.priority.value.upper(),
                f"{cap.confidence * 100:.0f}%",
                ", ".join(cap.dependencies) if cap.dependencies else "None",
            )

        console.print(table)

        summary_table = Table(title="Capability Validation & Readiness Summary")
        summary_table.add_column("Metric", style="bold green")
        summary_table.add_column("Value")
        summary_table.add_row("Total Capabilities", str(cap_report.total_capabilities_analyzed))
        summary_table.add_row("Total Groups", str(len(cap_report.groups)))
        summary_table.add_row("Total Requirements Mapped", str(len(cap_report.requirements)))
        summary_table.add_row("Evidence Records Attached", str(len(cap_report.evidence)))
        summary_table.add_row("Validation Status", "PASSED" if cap_report.readiness.get("is_ready", True) else "FAILED")

        console.print(summary_table)

    except (MissionIntakeError, MissionResolutionError, MissionOrchestrationError) as exc:
        console.print(f"[red]Capability Resolution Error:[/] {getattr(exc, 'message', str(exc))}")
        raise typer.Exit(1)


@app.command("organization")
def organization_command(
    command: list[str] = typer.Argument(None, help="Natural language command or prompt for organization assembly."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON Organization."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
) -> None:
    """Assemble and display required engineering organization for a mission without execution."""
    if command and "--json" in command:
        json_output = True
        command = [c for c in command if c != "--json"]
    raw_prompt = " ".join(command) if command else "Assemble organization for workspace"

    try:
        intake = MissionIntake()
        mission_request = intake.process_intake(raw_prompt, explicit_workspace=workspace)
        resolver = MissionResolver()
        resolved_mission = resolver.resolve_mission(mission_request)
        orchestrator = MissionOrchestrator()
        exec_request = orchestrator.orchestrate_mission(resolved_mission)
        cap_resolver = CapabilityResolver(repository_root=repository_root)
        cap_report = cap_resolver.resolve_capabilities(exec_request)
        org_assembler = OrganizationAssembler(repository_root=repository_root)
        org = org_assembler.assemble_organization(cap_report, mission_id=exec_request.mission.mission_id)

        if json_output:
            console.print_json(data=org.model_dump(mode="json"))
            return

        table = Table(title=f"Assembled Organization: {org.organization_id} ({org.name})")
        table.add_column("Member ID", style="bold cyan")
        table.add_column("Role Title", style="bold yellow")
        table.add_column("Department", style="bold green")
        table.add_column("Capabilities")
        table.add_column("Status")

        for member in org.members:
            dept_found = "Engineering"
            for d_name, m_list in org.departments.items():
                if member.member_id in m_list:
                    dept_found = d_name
                    break
            table.add_row(
                member.member_id,
                member.role.title,
                dept_found,
                str(len(member.capability_ids)),
                member.status.value.upper(),
            )

        console.print(table)

        summary_table = Table(title="Organization Structural Integrity & Readiness Summary")
        summary_table.add_column("Metric", style="bold green")
        summary_table.add_column("Value")
        summary_table.add_row("Total Members Allocated", str(len(org.members)))
        summary_table.add_row("Total Roles Defined", str(len(org.roles)))
        summary_table.add_row("Total Departments Assembled", str(len(org.departments)))
        summary_table.add_row("Total Dependencies Mapped", str(len(org.dependencies)))
        summary_table.add_row("Structural Integrity Status", "PASSED" if org.readiness.get("is_ready", True) else "FAILED")

        console.print(summary_table)

    except (MissionIntakeError, MissionResolutionError, MissionOrchestrationError) as exc:
        console.print(f"[red]Organization Assembly Error:[/] {getattr(exc, 'message', str(exc))}")
        raise typer.Exit(1)


@app.command("blueprint")
def blueprint_command(
    command: list[str] = typer.Argument(None, help="Natural language command or prompt for execution blueprint assembly."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON ExecutionBlueprint."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
) -> None:
    """Assemble and display sealed Execution Blueprint for a mission without execution."""
    if command and "--json" in command:
        json_output = True
        command = [c for c in command if c != "--json"]
    raw_prompt = " ".join(command) if command else "Assemble execution blueprint for workspace"

    try:
        intake = MissionIntake()
        mission_request = intake.process_intake(raw_prompt, explicit_workspace=workspace)
        resolver = MissionResolver()
        resolved_mission = resolver.resolve_mission(mission_request)
        orchestrator = MissionOrchestrator()
        exec_request = orchestrator.orchestrate_mission(resolved_mission)
        bp_assembler = ExecutionBlueprintAssembler(repository_root=repository_root)
        blueprint = bp_assembler.assemble_blueprint(exec_request, repository_root=repository_root)

        if json_output:
            console.print_json(data=blueprint.model_dump(mode="json"))
            return

        table = Table(title=f"Sealed Execution Blueprint: {blueprint.blueprint_id}")
        table.add_column("Blueprint Attribute", style="bold cyan")
        table.add_column("Specification / Value")

        table.add_row("Blueprint ID", blueprint.blueprint_id)
        table.add_row("Mission ID", blueprint.mission.mission_id)
        table.add_row("Mission Primary Goal", blueprint.mission.requirements.primary_goal)
        table.add_row("Organization ID", blueprint.organization.organization_id)
        table.add_row("Swarm Graph ID", blueprint.dependencies.graph_id)
        table.add_row("Allocated Swarm Members", str(len(blueprint.organization.members)))
        table.add_row("Swarm Graph Nodes / Edges", f"{len(blueprint.dependencies.nodes)} nodes / {len(blueprint.dependencies.edges)} edges")
        table.add_row("Assessed Capabilities", str(blueprint.capabilities.total_capabilities_analyzed))
        table.add_row("Execution Readiness Verdict", "PASSED" if blueprint.readiness.is_ready else "FAILED")

        console.print(table)

        summary_table = Table(title="Execution Blueprint Readiness Verification")
        summary_table.add_column("Verification Check", style="bold green")
        summary_table.add_column("Status")

        for check_name, status in blueprint.readiness.validation_checks.items():
            summary_table.add_row(check_name.replace("_", " ").title(), "PASSED" if status else "FAILED")

        console.print(summary_table)

    except (MissionIntakeError, MissionResolutionError, MissionOrchestrationError) as exc:
        console.print(f"[red]Execution Blueprint Assembly Error:[/] {getattr(exc, 'message', str(exc))}")
        raise typer.Exit(1)


@app.command("session")
def session_command(
    command: list[str] = typer.Argument(None, help="Natural language mission command for session initialization."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON RuntimeReport."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
) -> None:
    """Initialize agent sessions from a sealed Execution Blueprint without execution."""
    if command and "--json" in command:
        json_output = True
        command = [c for c in command if c != "--json"]
    raw_prompt = " ".join(command) if command else "Initialize sessions for workspace"

    try:
        intake = MissionIntake()
        mission_request = intake.process_intake(raw_prompt, explicit_workspace=workspace)
        resolver = MissionResolver()
        resolved_mission = resolver.resolve_mission(mission_request)
        orchestrator = MissionOrchestrator()
        exec_request = orchestrator.orchestrate_mission(resolved_mission)
        bp_assembler = ExecutionBlueprintAssembler(repository_root=repository_root)
        blueprint = bp_assembler.assemble_blueprint(exec_request, repository_root=repository_root)
        coordinator = SessionCoordinator()
        context, sessions, report = coordinator.initialize_sessions(blueprint)

        if json_output:
            console.print_json(data=report.model_dump(mode="json"))
            return

        table = Table(title=f"Agent Sessions: {blueprint.blueprint_id}")
        table.add_column("Session ID", style="bold cyan")
        table.add_column("Member ID", style="bold yellow")
        table.add_column("Role", style="bold green")
        table.add_column("State")
        table.add_column("Capabilities")
        table.add_column("Events")

        for session in sessions:
            table.add_row(
                session.session_id,
                session.member_id,
                session.role_title,
                session.state.value.upper(),
                str(len(session.capability_ids)),
                str(len(session.events)),
            )

        console.print(table)

        summary_table = Table(title="Session Initialization Runtime Report")
        summary_table.add_column("Metric", style="bold green")
        summary_table.add_column("Value")
        summary_table.add_row("Blueprint ID", report.blueprint_id)
        summary_table.add_row("Mission ID", report.mission_id)
        summary_table.add_row("Total Sessions", str(report.total_sessions))
        summary_table.add_row("Total Events", str(report.total_events))
        summary_table.add_row("Initialization Status", "READY" if report.total_sessions > 0 else "EMPTY")

        console.print(summary_table)

    except (MissionIntakeError, MissionResolutionError, MissionOrchestrationError) as exc:
        console.print(f"[red]Session Initialization Error:[/] {getattr(exc, 'message', str(exc))}")
        raise typer.Exit(1)


@app.command("execute")
def execute_command(
    command: list[str] = typer.Argument(None, help="Natural language mission command to execute."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON RuntimeReport."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
) -> None:
    """Execute a mission end-to-end: Blueprint → Sessions → Execution → RuntimeReport."""
    if command and "--json" in command:
        json_output = True
        command = [c for c in command if c != "--json"]
    raw_prompt = " ".join(command) if command else "Execute workspace mission"

    try:
        # 1. Full pipeline: intake → resolve → orchestrate → blueprint
        intake = MissionIntake()
        mission_request = intake.process_intake(raw_prompt, explicit_workspace=workspace)
        resolver = MissionResolver()
        resolved_mission = resolver.resolve_mission(mission_request)
        orchestrator = MissionOrchestrator()
        exec_request = orchestrator.orchestrate_mission(resolved_mission)
        bp_assembler = ExecutionBlueprintAssembler(repository_root=repository_root)
        blueprint = bp_assembler.assemble_blueprint(exec_request, repository_root=repository_root)

        # 2. Session initialization
        coordinator = SessionCoordinator()
        context, sessions, _session_report = coordinator.initialize_sessions(blueprint)

        # 3. Execute all READY sessions
        engine = AgentExecutionEngine(repository_root=repository_root)
        results, report = engine.execute_all(blueprint, coordinator.registry)

        if json_output:
            console.print_json(data=report.model_dump(mode="json"))
            return

        # 4. Render rich output
        result_table = Table(title=f"Execution Results: {blueprint.blueprint_id}")
        result_table.add_column("Session ID", style="bold cyan")
        result_table.add_column("Role", style="bold green")
        result_table.add_column("State")
        result_table.add_column("Status")
        result_table.add_column("Artifacts")
        result_table.add_column("Events")

        for session in coordinator.registry.list_sessions():
            result_table.add_row(
                session.session_id,
                session.role_title,
                session.state.value.upper(),
                session.status.value.upper(),
                str(len(session.artifacts)),
                str(len(session.events)),
            )
        console.print(result_table)

        summary_table = Table(title="Runtime Execution Report")
        summary_table.add_column("Metric", style="bold green")
        summary_table.add_column("Value")
        summary_table.add_row("Blueprint ID", report.blueprint_id)
        summary_table.add_row("Mission ID", report.mission_id)
        summary_table.add_row("Total Sessions", str(report.total_sessions))
        summary_table.add_row("Completed", str(report.completed_sessions))
        summary_table.add_row("Failed", str(report.failed_sessions))
        summary_table.add_row("Total Artifacts", str(report.total_artifacts))
        summary_table.add_row("Total Events", str(report.total_events))
        console.print(summary_table)

    except (MissionIntakeError, MissionResolutionError, MissionOrchestrationError) as exc:
        console.print(f"[red]Execution Error:[/] {getattr(exc, 'message', str(exc))}")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Recovery CLI commands (ACR-006 Phase R4)
# ---------------------------------------------------------------------------

@app.command("review")
def review_command(
    session_id: str = typer.Argument("", help="Session ID under review or filter ID."),
    approve: bool = typer.Option(False, "--approve", help="Approve the review (Recovery mode)."),
    reject: bool = typer.Option(False, "--reject", help="Reject the review (Recovery mode)."),
    request_changes: bool = typer.Option(False, "--request-changes", help="Request changes (Recovery mode)."),
    actor: str = typer.Option("cli-operator", "--actor", help="Identity of the reviewer."),
    notes: str = typer.Option("", "--notes", help="Optional reviewer notes."),
    policy_name: str = typer.Option("default", "--policy", help="Review policy: default, strict, permissive, security, infrastructure, deployment."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    decisions_given = sum([approve, reject, request_changes])

    # If session_id is provided without decision flags in recovery mode:
    if session_id and decisions_given == 0:
        console.print("[red]Error:[/] Specify exactly one of --approve, --reject, --request-changes.")
        raise typer.Exit(1)

    # If a decision flag is explicitly passed, run ACR-006 Recovery Review decision logic
    if decisions_given > 0:
        if decisions_given != 1:
            console.print("[red]Error:[/] Specify exactly one of --approve, --reject, --request-changes.")
            raise typer.Exit(1)

        if not session_id:
            console.print("[red]Error:[/] Session ID required for recovery review decision.")
            raise typer.Exit(1)

        if approve:
            decision = ReviewDecision.APPROVE
        elif reject:
            decision = ReviewDecision.REJECT
        else:
            decision = ReviewDecision.REQUEST_CHANGES

        from runtime.agent.recovery.policy import (
            DEPLOYMENT_POLICY,
            INFRASTRUCTURE_POLICY,
            SECURITY_POLICY,
            DefaultReviewPolicy,
            PermissiveReviewPolicy,
            StrictReviewPolicy,
        )
        policy_map = {
            "default": DefaultReviewPolicy(),
            "strict": StrictReviewPolicy(),
            "permissive": PermissiveReviewPolicy(),
            "security": SECURITY_POLICY,
            "infrastructure": INFRASTRUCTURE_POLICY,
            "deployment": DEPLOYMENT_POLICY,
        }
        selected_policy = policy_map.get(policy_name.lower(), DefaultReviewPolicy())

        from runtime.agent.recovery.review import RuntimeReviewEngine
        review_engine = RuntimeReviewEngine(policy=selected_policy)

        from runtime.agent.recovery.models import ReviewRecord
        review_id = f"rev-{session_id}-cli"
        pending = ReviewRecord(
            review_id=review_id,
            session_id=session_id,
            member_id="cli-member",
            review_reason=f"CLI-submitted review decision under policy '{selected_policy.policy_name()}'",
            evidence={"source": "cli", "actor": actor, "policy": selected_policy.policy_name()},
        )
        review_engine._pending_reviews[review_id] = pending

        closed = review_engine.submit_decision(
            review_id=review_id,
            decision=decision,
            actor=actor,
            notes=notes,
        )

        if json_output:
            data = closed.model_dump(mode="json")
            data["policy"] = selected_policy.policy_name()
            console.print_json(data=data)
            return

        table = Table(title=f"Review Decision: {session_id}")
        table.add_column("Field", style="bold cyan")
        table.add_column("Value")
        table.add_row("Review ID", closed.review_id)
        table.add_row("Session ID", closed.session_id)
        table.add_row("Policy", selected_policy.policy_name())
        table.add_row("Decision", closed.outcome.decision.value.upper() if closed.outcome else "—")
        table.add_row("Actor", closed.outcome.actor if closed.outcome else "—")
        table.add_row("Notes", closed.outcome.notes if closed.outcome else "—")
        table.add_row("Decided At", closed.outcome.decided_at if closed.outcome else "—")
        console.print(table)
        return

    # Collaboration Peer Review inspection mode (ACR-007 Phase C4)
    from runtime.agent.models import ArtifactRecord, ArtifactType
    from runtime.collaboration import ReviewCoordinator, SharedArtifactManager

    art_mgr = SharedArtifactManager()
    rev_coord = ReviewCoordinator(timeline=art_mgr.timeline)

    art = ArtifactRecord(
        artifact_id="art-api-spec-001",
        artifact_type=ArtifactType.DOCUMENTATION,
        owner_session_id="sess-lead-001",
        owner_member_id="mem-lead",
        capability_id="cap-doc-gen",
        name="REST API Spec v1",
        references=["docs/api_spec.yaml"],
    )
    ref = art_mgr.create_reference(art, version=1, checksum="sha256-f1e2")

    r1 = rev_coord.create_review(
        author_session_id="sess-lead-001",
        reviewer_session_id="sess-qa-001",
        artifact_references=[ref],
        reason="Peer review API spec for REST endpoints",
        conversation_id="conv-arch-01",
        thread_id="th-api-01",
    )
    rev_coord.start_review(r1.review_id, "sess-qa-001")
    rev_coord.approve_review(r1.review_id, "sess-qa-001", comments="API spec LGTM.")

    reviews = rev_coord.get_all_reviews()

    if json_output:
        data = [r.model_dump(mode="json") for r in reviews]
        console.print_json(data=data)
        return

    table = Table(title="Inter-Agent Peer Reviews")
    table.add_column("Review ID", style="bold cyan")
    table.add_column("Author")
    table.add_column("Reviewer")
    table.add_column("Status", style="green")
    table.add_column("Artifact Count", justify="right")
    table.add_column("Reason")
    table.add_column("Requested At", style="dim")

    for r in reviews:
        table.add_row(
            r.review_id,
            r.author_session_id,
            r.reviewer_session_id,
            r.status.value.upper(),
            str(len(r.artifact_references)),
            r.reason,
            r.requested_at,
        )
    console.print(table)


@app.command("approval")
def approval_command(
    session_id: str = typer.Option("", "--session", help="Filter approvals by requester/approver session ID."),
    policy_name: str = typer.Option("security", "--policy", help="Filter/evaluate under policy: security, infrastructure, deployment, default."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Inspect governance approval requests, policy decisions, and pending approvals."""
    from runtime.agent.models import ArtifactRecord, ArtifactType
    from runtime.agent.recovery.policy import DEPLOYMENT_POLICY, INFRASTRUCTURE_POLICY, SECURITY_POLICY, DefaultReviewPolicy
    from runtime.collaboration import ApprovalCoordinator, SharedArtifactManager

    policy_map = {
        "security": SECURITY_POLICY,
        "infrastructure": INFRASTRUCTURE_POLICY,
        "deployment": DEPLOYMENT_POLICY,
        "default": DefaultReviewPolicy(),
    }
    selected_policy = policy_map.get(policy_name.lower(), SECURITY_POLICY)

    art_mgr = SharedArtifactManager()
    appr_coord = ApprovalCoordinator(timeline=art_mgr.timeline, default_policy=selected_policy)

    art = ArtifactRecord(
        artifact_id="art-sec-config-001",
        artifact_type=ArtifactType.CONFIG,
        owner_session_id="sess-dev-001",
        owner_member_id="mem-dev",
        capability_id="cap-sec-gen",
        name="Security Policy Config",
        references=["config/security.json"],
    )
    ref = art_mgr.create_reference(art, version=1, checksum="sha256-s1e2")

    a1 = appr_coord.request_approval(
        requester_session_id="sess-dev-001",
        approver_session_id="sess-sec-lead",
        artifact_references=[ref],
        reason="Prod security policy update approval",
        policy=selected_policy,
    )
    appr_coord.approve(a1.approval_id, "sess-sec-lead", reason="Approved per security policy.")

    approvals = appr_coord.get_all_approvals()

    if json_output:
        data = [a.model_dump(mode="json") for a in approvals]
        console.print_json(data=data)
        return

    table = Table(title=f"Governance Approvals (Policy: {selected_policy.policy_name()})")
    table.add_column("Approval ID", style="bold cyan")
    table.add_column("Requester")
    table.add_column("Approver")
    table.add_column("Policy", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Reason")
    table.add_column("Requested At", style="dim")

    for a in approvals:
        table.add_row(
            a.approval_id,
            a.requester_session_id,
            a.approver_session_id or "ANY",
            a.policy_name,
            a.status.value.upper(),
            a.reason,
            a.requested_at,
        )
    console.print(table)


@app.command("retry")
def retry_command(
    session_id: str = typer.Argument(..., help="Session ID to retry."),
    max_retries: int = typer.Option(3, "--max-retries", help="Maximum retry attempts."),
    base_delay: float = typer.Option(1.0, "--base-delay", help="Base retry delay (seconds)."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Inspect retry eligibility and policy for a session."""
    policy = RetryPolicy(max_retries=max_retries, base_delay_seconds=base_delay)
    orchestrator = RecoveryOrchestrator(retry_policy=policy)
    rm = orchestrator.retry_manager

    # Simulate a transient failure classification for display
    classifier = FailureClassifier()
    sample_exc = ConnectionError("Simulated network timeout")
    classification = classifier.classify(sample_exc, context={"session_id": session_id})

    eligible = rm.can_retry(session_id, classification)
    computed_delay = rm.compute_delay(session_id)
    remaining = rm.remaining_retries(session_id)

    if json_output:
        console.print_json(data={
            "session_id": session_id,
            "eligible": eligible,
            "computed_delay_seconds": computed_delay,
            "remaining_retries": remaining,
            "policy": policy.model_dump(),
            "sample_classification": classification.to_dict(),
        })
        return

    table = Table(title=f"Retry Eligibility: {session_id}")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")
    table.add_row("Session ID", session_id)
    table.add_row("Eligible for Retry", "[green]YES[/]" if eligible else "[red]NO[/]")
    table.add_row("Remaining Retries", str(remaining))
    table.add_row("Computed Delay (s)", f"{computed_delay:.2f}")
    table.add_row("Max Retries", str(policy.max_retries))
    table.add_row("Base Delay (s)", f"{policy.base_delay_seconds:.2f}")
    table.add_row("Backoff Factor", str(policy.backoff_factor))
    table.add_row("Max Delay (s)", str(policy.max_delay_seconds))
    table.add_row("Sample Category", classification.category.value)
    table.add_row("Retryable", str(classification.is_retryable))
    console.print(table)


@app.command("resume")
def resume_command(
    session_id: str = typer.Argument(..., help="Session ID to resume from WAITING."),
    pause_id: str | None = typer.Option(None, "--pause-id", help="Specific pause record ID to close."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Inspect or display resume readiness for a WAITING session."""
    if json_output:
        console.print_json(data={
            "session_id": session_id,
            "action": "resume",
            "pause_id": pause_id,
            "note": (
                "Call RecoveryOrchestrator.resume(session, pause_id) on the live session object. "
                "CLI resume shows policy; use the Python API for live session recovery."
            ),
        })
        return

    table = Table(title=f"Resume Request: {session_id}")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")
    table.add_row("Session ID", session_id)
    table.add_row("Requested Pause ID", pause_id or "(most recent)")
    table.add_row("Action", "WAITING → RUNNING")
    table.add_row(
        "Note",
        "Use RecoveryOrchestrator.resume() on the live session for in-process recovery.",
    )
    console.print(table)
    console.print("[dim]To resume a live session, call:[/] [cyan]orchestrator.resume(session)[/]")


@app.command("recovery")
def recovery_command(
    session_id: str = typer.Argument(..., help="Session ID to show recovery report for."),
    blueprint_id: str = typer.Option("bp-cli", "--blueprint-id", help="Blueprint ID reference."),
    mission_id: str = typer.Option("msn-cli", "--mission-id", help="Mission ID reference."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON RecoveryReport."),
) -> None:
    """Generate and display a RecoveryReport for a session."""
    from runtime.agent.models import AgentSession, ExecutionStatus, RuntimeState
    from runtime.agent.recovery.models import RecoveryMetrics, RecoveryReport
    import uuid

    # Build a sample report for display (real report requires live session)
    metrics = RecoveryMetrics(
        total_failures=0,
        total_retries=0,
        successful_retries=0,
        failed_retries=0,
        total_pauses=0,
        total_resumes=0,
        total_reviews_requested=0,
        total_reviews_approved=0,
        total_reviews_rejected=0,
        total_recoveries=0,
    )
    report = RecoveryReport(
        report_id=f"recovery-report-{session_id}-{uuid.uuid4().hex[:8]}",
        session_id=session_id,
        blueprint_id=blueprint_id,
        mission_id=mission_id,
        failures=[],
        retries=[],
        pauses=[],
        review_requests=[],
        review_outcomes=[],
        metrics=metrics,
        recovery_status="pending",
        summary=(
            f"Session: {session_id}. Status: pending. "
            "No failures or retries recorded (live session required for full report)."
        ),
    )

    if json_output:
        console.print_json(data=report.model_dump(mode="json"))
        return

    table = Table(title=f"Recovery Report: {session_id}")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", justify="right")
    table.add_row("Report ID", report.report_id)
    table.add_row("Session ID", report.session_id)
    table.add_row("Blueprint ID", report.blueprint_id)
    table.add_row("Mission ID", report.mission_id)
    table.add_row("Recovery Status", report.recovery_status.upper())
    table.add_row("Total Failures", str(report.metrics.total_failures))
    table.add_row("Total Retries", str(report.metrics.total_retries))
    table.add_row("Successful Retries", str(report.metrics.successful_retries))
    table.add_row("Failed Retries", str(report.metrics.failed_retries))
    table.add_row("Total Pauses", str(report.metrics.total_pauses))
    table.add_row("Total Resumes", str(report.metrics.total_resumes))
    table.add_row("Reviews Requested", str(report.metrics.total_reviews_requested))
    table.add_row("Reviews Approved", str(report.metrics.total_reviews_approved))
    table.add_row("Reviews Rejected", str(report.metrics.total_reviews_rejected))
    table.add_row("Generated At", report.generated_at)
    console.print(table)
    console.print(f"[dim]Summary:[/] {report.summary}")


# ---------------------------------------------------------------------------
# Collaboration CLI commands (ACR-007 Phase C2)
# ---------------------------------------------------------------------------

@app.command("collaborate")
def collaborate_command(
    prompt: str = typer.Argument("Establish collaboration session", help="Objective or topic for collaboration."),
    blueprint_id: str = typer.Option("bp-collab-001", "--blueprint-id", help="ExecutionBlueprint ID."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Initialize a collaboration session with conversation, threads, and message bus routing."""
    from runtime.agent.models import AgentSession, RuntimeState
    from runtime.collaboration import MessageBus, Message, MessageType

    bus = MessageBus(blueprint_id=blueprint_id)

    # Register demonstration agent sessions
    s1 = AgentSession(
        session_id="sess-lead-001", member_id="mem-lead", role_id="role-architect",
        role_title="Lead Architect", blueprint_id=blueprint_id, state=RuntimeState.RUNNING,
    )
    s2 = AgentSession(
        session_id="sess-dev-001", member_id="mem-dev", role_id="role-backend",
        role_title="Backend Developer", blueprint_id=blueprint_id, state=RuntimeState.RUNNING,
        metadata={"department": "engineering"},
    )
    s3 = AgentSession(
        session_id="sess-qa-001", member_id="mem-qa", role_id="role-qa",
        role_title="QA Engineer", blueprint_id=blueprint_id, state=RuntimeState.RUNNING,
        metadata={"department": "engineering"},
    )
    bus.register_sessions([s1, s2, s3])

    # Create conversation and thread
    conv = bus.create_conversation(
        title=f"Collaboration: {prompt}",
        mission_id="msn-collab-001",
        participants=[s1.session_id, s2.session_id, s3.session_id],
    )
    th = bus.create_thread(
        topic=f"Initial Discussion: {prompt}",
        participant_session_ids=[s1.session_id, s2.session_id],
        conversation_id=conv.conversation_id,
    )

    # Publish initial message
    msg = Message(
        message_id="msg-init-001",
        conversation_id=conv.conversation_id,
        thread_id=th.thread_id,
        sender_session_id=s1.session_id,
        sender_member_id=s1.member_id,
        recipient_sessions=["role:backend"],
        message_type=MessageType.TASK,
        subject="Task Assignment",
        content=f"Please begin initial architecture work for '{prompt}'.",
    )
    bus.publish_message(msg)

    session_snap = bus.get_collaboration_session()

    if json_output:
        console.print_json(data=session_snap.model_dump(mode="json"))
        return

    table = Table(title=f"Collaboration Session: {session_snap.collaboration_id}")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value")
    table.add_row("Blueprint ID", session_snap.blueprint_id)
    table.add_row("Active Conversations", str(len(session_snap.active_conversations)))
    table.add_row("Open Threads", str(len(session_snap.open_threads)))
    table.add_row("Total Participants", str(len(session_snap.participants)))
    table.add_row("Participants", ", ".join(session_snap.participants))
    table.add_row("Total Messages", str(session_snap.statistics.get("total_messages", 0)))
    table.add_row("Timeline Events", str(len(session_snap.timeline.events)))
    console.print(table)


@app.command("conversation")
def conversation_command(
    action: str = typer.Argument("list", help="Action: list or show."),
    conversation_id: str = typer.Option("", "--id", help="Conversation ID to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Inspect collaboration conversations and their participant threads."""
    from runtime.collaboration import MessageBus

    bus = MessageBus(blueprint_id="bp-cli-demo")
    c1 = bus.create_conversation(
        title="CRM Service System Architecture",
        mission_id="msn-crm-001",
        participants=["sess-architect-01", "sess-backend-01", "sess-qa-01"],
    )
    bus.create_thread(
        topic="Database Schema Review",
        participant_session_ids=["sess-architect-01", "sess-backend-01"],
        conversation_id=c1.conversation_id,
    )

    if conversation_id:
        target = bus.get_conversation(conversation_id) or c1
    else:
        target = c1

    if json_output:
        console.print_json(data=target.model_dump(mode="json"))
        return

    table = Table(title=f"Conversation: {target.conversation_id}")
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    table.add_row("Title", target.title)
    table.add_row("Mission ID", target.mission_id)
    table.add_row("Status", target.status.value.upper())
    table.add_row("Participants", ", ".join(target.participants))
    table.add_row("Threads Count", str(len(target.threads)))
    table.add_row("Created At", target.created_at)
    console.print(table)


@app.command("thread")
def thread_command(
    thread_id: str = typer.Argument("", help="Thread ID to inspect (omit for default)."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Inspect message threads and message history."""
    from runtime.collaboration import MessageBus, Message, MessageType

    bus = MessageBus(blueprint_id="bp-cli-demo")
    c = bus.create_conversation(title="Backend Service Handoff", participants=["sess-arch-01", "sess-dev-01"])
    th = bus.create_thread(topic="API Contracts", participant_session_ids=["sess-arch-01", "sess-dev-01"], conversation_id=c.conversation_id)

    bus.publish_message(Message(
        message_id="msg-th-001",
        conversation_id=c.conversation_id,
        thread_id=th.thread_id,
        sender_session_id="sess-arch-01",
        sender_member_id="mem-arch",
        recipient_sessions=["sess-dev-01"],
        message_type=MessageType.QUESTION,
        subject="API Format",
        content="Should we use OpenAPI v3 for REST contracts?",
    ))

    target_th = bus.get_thread(thread_id) if thread_id else bus.get_thread(th.thread_id)
    if not target_th:
        target_th = th

    if json_output:
        console.print_json(data=target_th.model_dump(mode="json"))
        return

    table = Table(title=f"Thread: {target_th.thread_id}")
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    table.add_row("Topic", target_th.topic)
    table.add_row("Thread Type", target_th.thread_type.value.upper())
    table.add_row("Status", target_th.status.value.upper())
    table.add_row("Participants", ", ".join(target_th.participant_session_ids))
    table.add_row("Message Count", str(len(target_th.messages)))
    console.print(table)

    if target_th.messages:
        msg_table = Table(title="Messages in Thread")
        msg_table.add_column("Message ID", style="dim")
        msg_table.add_column("Sender")
        msg_table.add_column("Type", style="yellow")
        msg_table.add_column("Subject")
        msg_table.add_column("Content")
        for m in target_th.messages:
            msg_table.add_row(m.message_id, m.sender_session_id, m.message_type.value.upper(), m.subject, m.content)
        console.print(msg_table)


@app.command("handoff")
def handoff_command(
    session_id: str = typer.Option("", "--session", help="Filter handoffs by session ID."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Inspect deliverable and task handoffs between collaborating agent sessions."""
    from runtime.agent.models import ArtifactRecord, ArtifactType
    from runtime.collaboration import HandoffManager, SharedArtifactManager

    art_mgr = SharedArtifactManager()
    hdf_mgr = HandoffManager(timeline=art_mgr.timeline)

    # Demo handoff record for CLI demonstration
    art = ArtifactRecord(
        artifact_id="art-db-schema-001",
        artifact_type=ArtifactType.SCHEMA,
        owner_session_id="sess-arch-001",
        owner_member_id="mem-arch",
        capability_id="cap-schema-gen",
        name="Database Schema v1.0",
        references=["artifacts/schema.sql"],
    )
    ref = art_mgr.create_reference(art, checksum="sha256-a1b2c3d4", version=1)
    hdf = hdf_mgr.create_handoff(
        producer_session_id="sess-arch-001",
        consumer_session_id="sess-dev-001",
        artifact_reference=ref,
        reason="Database schema ready for REST API implementation",
    )

    handoffs = hdf_mgr.get_handoffs(session_id) if session_id else hdf_mgr.get_all_handoffs()

    if json_output:
        data = [h.model_dump(mode="json") for h in handoffs]
        console.print_json(data=data)
        return

    table = Table(title="Inter-Session Handoffs")
    table.add_column("Handoff ID", style="bold cyan")
    table.add_column("Producer")
    table.add_column("Consumer")
    table.add_column("Artifact ID", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Reason")
    table.add_column("Timestamp", style="dim")

    for h in handoffs:
        table.add_row(
            h.handoff_id,
            h.producer_session_id,
            h.consumer_session_id,
            h.artifact_reference.artifact_id,
            h.status.value.upper(),
            h.reason,
            h.timestamp,
        )
    console.print(table)


@app.command("artifact")
def artifact_command(
    reference_id: str = typer.Option("", "--id", help="Artifact Reference ID to inspect."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Inspect shared artifact references, ownership, checksums, versioning, and lineage."""
    from runtime.agent.models import ArtifactRecord, ArtifactType
    from runtime.collaboration import SharedArtifactManager

    art_mgr = SharedArtifactManager()
    art1 = ArtifactRecord(
        artifact_id="art-spec-001",
        artifact_type=ArtifactType.DOCUMENTATION,
        owner_session_id="sess-lead-001",
        owner_member_id="mem-lead",
        capability_id="cap-doc-gen",
        name="System Architecture Spec",
        references=["docs/spec.md"],
    )
    ref1 = art_mgr.create_reference(art1, version=1, checksum="sha256-f1e2d3c4")

    refs = [art_mgr.resolve_reference(reference_id)] if reference_id else art_mgr.get_all_references()

    if json_output:
        data = [r.model_dump(mode="json") for r in refs]
        console.print_json(data=data)
        return

    table = Table(title="Shared Artifact References (Zero-Duplication Pointers)")
    table.add_column("Reference ID", style="bold cyan")
    table.add_column("Artifact ID", style="yellow")
    table.add_column("Owner Session")
    table.add_column("Type")
    table.add_column("Checksum", style="dim")
    table.add_column("Version", justify="right")
    table.add_column("Path / URI")

    for r in refs:
        table.add_row(
            r.reference_id,
            r.artifact_id,
            r.owner_session_id,
            r.artifact_type.upper(),
            r.checksum,
            str(r.version),
            r.workspace_path,
        )
    console.print(table)
    console.print("[dim]Note: Shared artifact references do not copy or duplicate workspace file contents.[/]")


@app.command("intent")
def intent_cmd(
    request: list[str] = typer.Argument(..., help="Natural language request string to analyze."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Analyze natural language request and display the resulting IntentReport."""
    raw_prompt = " ".join(request)
    if not raw_prompt.strip():
        console.print("[red]Error:[/] Request string cannot be empty.")
        raise typer.Exit(1)

    try:
        analyzer = IntentAnalyzer()
        report = analyzer.analyze(raw_prompt, explicit_workspace=workspace)

        if json_output:
            console.print_json(data=report.model_dump(mode="json"))
            return

        table = Table(title=f"Intent Report: {report.intent_id}")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Intent ID", report.intent_id)
        table.add_row("Original Request", report.original_request)
        table.add_row("Normalized Request", report.normalized_request)
        table.add_row("Primary Intent", report.primary_intent)
        table.add_row("Project Category", report.project_category)
        table.add_row("Application Type", report.application_type)
        table.add_row("Confidence Score", f"{report.confidence_score:.2f}")
        table.add_row("Detected Technologies", ", ".join(report.detected_technologies) if report.detected_technologies else "None")
        table.add_row("Detected Frameworks", ", ".join(report.detected_frameworks) if report.detected_frameworks else "None")
        table.add_row("Detected Languages", ", ".join(report.detected_languages) if report.detected_languages else "None")
        table.add_row("Detected Database", ", ".join(report.detected_database) if report.detected_database else "None")
        table.add_row("Detected Cloud", ", ".join(report.detected_cloud) if report.detected_cloud else "None")
        table.add_row("Detected Authentication", ", ".join(report.detected_authentication) if report.detected_authentication else "None")
        table.add_row("Detected Integrations", ", ".join(report.detected_integrations) if report.detected_integrations else "None")
        table.add_row("Detected Features", ", ".join(report.detected_features) if report.detected_features else "None")
        table.add_row("Detected Constraints", ", ".join(report.detected_constraints) if report.detected_constraints else "None")
        table.add_row("Unknown Items", ", ".join(report.unknown_items) if report.unknown_items else "None")
        table.add_row("Timestamp", report.timestamp)

        console.print(table)
    except EmptyRequestError as exc:
        console.print(f"[red]Error:[/] {exc.message}")
        raise typer.Exit(1)


@app.command("workspace-context")
def workspace_context_cmd(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Analyze and display detailed Workspace Context intelligence."""
    intelligence = WorkspaceIntelligence()
    ctx = intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    if json_output:
        console.print_json(data=ctx.model_dump(mode="json"))
        return

    table = Table(title=f"Workspace Context: {ctx.workspace_id}")
    table.add_column("Category", style="bold cyan")
    table.add_column("Property")
    table.add_column("Value")

    table.add_row("Workspace", "Workspace Root", str(ctx.workspace_root))
    table.add_row("Workspace", "Repository Root", str(ctx.repository_root))
    table.add_row("Workspace", "Engine Root", str(ctx.engine_root))

    proj_type_str = ctx.project_type.value if hasattr(ctx.project_type, "value") else str(ctx.project_type)
    table.add_row("Project", "Project Type", proj_type_str)
    table.add_row("Project", "Primary Language", ctx.primary_language)
    table.add_row("Project", "Framework Hint", ctx.framework_hint or "None")
    table.add_row("Project", "Workspace State", ctx.workspace_state.value if hasattr(ctx.workspace_state, "value") else str(ctx.workspace_state))

    table.add_row("Git", "Git Available", "YES" if ctx.git_available else "NO")
    table.add_row("Git", "Repository Root", str(ctx.repository_root))

    table.add_row("Manifests", "Build Tool", ctx.build_tool or "None")
    table.add_row("Manifests", "Package Manager", ctx.package_manager or "None")
    table.add_row("Manifests", "Detected Manifests", ", ".join(ctx.detected_manifests) if ctx.detected_manifests else "None")
    table.add_row("Manifests", "Has .oniroute", "YES" if ctx.has_oniroute_dir else "NO")

    val_style = "[green]PASS[/]" if ctx.validation.valid else "[red]FAIL[/]"
    table.add_row("Validation", "Validation Status", val_style)
    table.add_row("Validation", "Read-only Engine", "CONFIRMED" if ctx.read_only_validation else "FAILED")
    table.add_row("Validation", "Validation Issues", str(len(ctx.validation.issues)))

    console.print(table)


@app.command("repository")
def repository_cmd(
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Analyze and display detailed Repository Intelligence and directory topology."""
    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    if json_output:
        console.print_json(data=repo_ctx.model_dump(mode="json"))
        return

    table = Table(title=f"Repository Intelligence: {repo_ctx.repository_id}")
    table.add_column("Category", style="bold cyan")
    table.add_column("Property")
    table.add_column("Value")

    table.add_row("Topology", "Layout Pattern", repo_ctx.project_layout)
    top_dirs = [k for k in repo_ctx.directory_topology.keys() if k != "."]
    table.add_row("Topology", "Main Directories", ", ".join(top_dirs) if top_dirs else "None")

    table.add_row("Roots", "Source Root", repo_ctx.detected_roots.get("source_root") or "None")
    table.add_row("Roots", "Test Root", repo_ctx.detected_roots.get("test_root") or "None")
    table.add_row("Roots", "Config Root", repo_ctx.detected_roots.get("configuration_root") or "None")
    table.add_row("Roots", "Doc Root", repo_ctx.detected_roots.get("documentation_root") or "None")
    table.add_row("Roots", "API Root", repo_ctx.detected_roots.get("api_root") or "None")
    table.add_row("Roots", "Component Root", repo_ctx.detected_roots.get("component_root") or "None")

    table.add_row("Entry Points", "Detected Entries", ", ".join(repo_ctx.entry_points) if repo_ctx.entry_points else "None")
    table.add_row("Config", "Config Files Count", str(len(repo_ctx.configuration_files)))
    table.add_row("Config", "Config Files", ", ".join(repo_ctx.configuration_files[:5]) if repo_ctx.configuration_files else "None")
    table.add_row("Docs", "Doc Files Count", str(len(repo_ctx.documentation_files)))
    table.add_row("Docs", "Doc Files", ", ".join(repo_ctx.documentation_files[:5]) if repo_ctx.documentation_files else "None")

    table.add_row("Tests", "Test Presence", "YES" if repo_ctx.test_presence else "NO")
    table.add_row("Tests", "Test File Count", str(repo_ctx.test_summary.get("test_file_count", 0)))
    table.add_row("Assets", "Total Assets", str(repo_ctx.asset_summary.get("total_assets", 0)))

    table.add_row("Repository Size", "Total Files", str(repo_ctx.repository_size.get("file_count", 0)))
    table.add_row("Repository Size", "Total Directories", str(repo_ctx.repository_size.get("directory_count", 0)))
    table.add_row("Repository Size", "Total Size (bytes)", str(repo_ctx.repository_size.get("total_size_bytes", 0)))

    console.print(table)


@skills_app.callback(invoke_without_command=True)
def skills_default(
    ctx: typer.Context,
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Discover skills required to execute the EngineeringExecutionPlan."""
    if ctx.invoked_subcommand is not None:
        return

    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)
    engine = SkillDiscoveryEngine(registry, resolver)
    report = engine.discover_skills(plan)

    if json_output:
        console.print_json(data=report.model_dump(mode="json"))
        return

    console.print(f"\n[bold cyan]Skill Discovery Report:[/] {report.report_id} (Plan: {report.execution_plan_id})")

    # 1. Skills Table
    skills_table = Table(title="Discovered Skills")
    skills_table.add_column("Skill ID", style="bold cyan")
    skills_table.add_column("Category")
    skills_table.add_column("Display Name")
    skills_table.add_column("Discovery Reason")

    for skill in report.discovered_skills:
        skills_table.add_row(skill.skill_id, skill.category, skill.display_name, skill.discovery_reason)
    console.print(skills_table)

    # 2. Coverage Table
    cov_table = Table(title="Skill Coverage")
    cov_table.add_column("Metric", style="bold cyan")
    cov_table.add_column("Value")

    cov_table.add_row("Coverage Percentage", f"{report.coverage.coverage_percent}%")
    cov_table.add_row("Registry Hits", str(report.coverage.registry_hits))
    cov_table.add_row("Required Domains", ", ".join(report.coverage.required_skills) if report.coverage.required_skills else "None")
    cov_table.add_row("Missing Skills", ", ".join(report.coverage.missing_skills) if report.coverage.missing_skills else "None")
    cov_table.add_row("Selection Confidence", f"{report.confidence * 100:.1f}%")
    console.print(cov_table)

    # 3. Knowledge Table
    know_table = Table(title="Required Knowledge Sources")
    know_table.add_column("Knowledge Source ID", style="bold cyan")
    if report.required_knowledge:
        for k in report.required_knowledge:
            know_table.add_row(k)
    else:
        know_table.add_row("None required")
    console.print(know_table)

    # 4. Packages Table
    pkg_table = Table(title="Required Packages & Dependencies")
    pkg_table.add_column("Package / Dependency ID", style="bold cyan")
    if report.required_packages:
        for p in report.required_packages:
            pkg_table.add_row(p)
    else:
        pkg_table.add_row("None required")
    console.print(pkg_table)

    # 5. MCP Table
    mcp_table = Table(title="Required MCP Tools")
    mcp_table.add_column("MCP Tool / Capability", style="bold cyan")
    if report.required_mcp_tools:
        for m in report.required_mcp_tools:
            mcp_table.add_row(m)
    else:
        mcp_table.add_row("None required")
    console.print(mcp_table)


@app.command("rank-skills")
@skills_app.command("rank")
def rank_skills_command(
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Deterministically rank discovered skills for an EngineeringExecutionPlan."""
    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)

    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    selection_report = discovery_engine.discover_skills(plan)

    ranking_engine = SkillRankingEngine(registry, resolver)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    if json_output:
        console.print_json(data=ranked_report.model_dump(mode="json"))
        return

    console.print(
        f"\n[bold cyan]Ranked Skill Report:[/] {ranked_report.report_id} "
        f"(Selection Report: {ranked_report.selection_report_id}, Plan: {ranked_report.execution_plan_id})"
    )

    # 1. Ranked Skills Table
    skills_table = Table(title="Ranked Skills")
    skills_table.add_column("Rank", justify="right", style="bold yellow")
    skills_table.add_column("Priority", style="bold green")
    skills_table.add_column("Score", justify="right")
    skills_table.add_column("Skill ID", style="bold cyan")
    skills_table.add_column("Category")
    skills_table.add_column("Dependencies")
    skills_table.add_column("Ranking Reason")

    for skill in ranked_report.ranked_skills:
        prio_str = skill.priority.value if hasattr(skill.priority, "value") else str(skill.priority)
        deps_str = ", ".join(skill.dependencies) if skill.dependencies else "None"
        skills_table.add_row(
            str(skill.rank),
            prio_str,
            f"{skill.score:.1f}",
            skill.skill_id,
            skill.category,
            deps_str,
            skill.ranking_reason,
        )
    console.print(skills_table)

    # 2. Priority Groups & Dependency Summary Table
    summary_table = Table(title="Priority & Dependency Summary")
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value")

    for prio_name, sid_list in ranked_report.priority_groups.items():
        summary_table.add_row(f"Priority [{prio_name}]", f"{len(sid_list)} skills ({', '.join(sid_list)})")

    summary_table.add_row("Recommended Execution Order", ", ".join(ranked_report.recommended_execution_order))
    summary_table.add_row("Blocking Skills", ", ".join(ranked_report.blocking_skills) if ranked_report.blocking_skills else "None")
    summary_table.add_row("Independent Skills", ", ".join(ranked_report.independent_skills) if ranked_report.independent_skills else "None")
    summary_table.add_row("Coverage Percentage", f"{ranked_report.coverage.coverage_percent}%")
    summary_table.add_row("Ranking Confidence", f"{ranked_report.confidence * 100:.1f}%")

    console.print(summary_table)


@app.command("bundles")
@skills_app.command("bundles")
def bundles_command(
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Group ranked skills into execution-ready ExecutionSkillBundles."""
    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)

    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    selection_report = discovery_engine.discover_skills(plan)

    ranking_engine = SkillRankingEngine(registry, resolver)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    bundling_engine = SkillBundlingEngine(registry, resolver)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    if json_output:
        console.print_json(data=bundle_report.model_dump(mode="json"))
        return

    console.print(
        f"\n[bold cyan]Execution Skill Bundle Report:[/] {bundle_report.report_id} "
        f"(Ranked Report: {bundle_report.ranked_report_id}, Plan: {bundle_report.execution_plan_id})"
    )

    # 1. Bundles Table
    bundles_table = Table(title="Execution Skill Bundles")
    bundles_table.add_column("Bundle ID", style="bold cyan")
    bundles_table.add_column("Discipline", style="bold yellow")
    bundles_table.add_column("Priority", style="bold green")
    bundles_table.add_column("Skills Count", justify="right")
    bundles_table.add_column("Deliverables")
    bundles_table.add_column("Dependencies")
    bundles_table.add_column("Coverage", justify="right")

    for bundle in bundle_report.bundles:
        prio_str = bundle.priority.value if hasattr(bundle.priority, "value") else str(bundle.priority)
        deliv_str = ", ".join(bundle.expected_deliverables) if bundle.expected_deliverables else "None"
        deps_str = ", ".join(bundle.dependency_bundles) if bundle.dependency_bundles else "None"
        bundles_table.add_row(
            bundle.bundle_id,
            bundle.engineering_discipline,
            prio_str,
            str(len(bundle.ranked_skills)),
            deliv_str,
            deps_str,
            f"{bundle.coverage:.1f}%",
        )
    console.print(bundles_table)

    # 2. Bundle Ordering & Validation Summary Table
    summary_table = Table(title="Bundle Execution Ordering & Integrity")
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value")

    summary_table.add_row("Recommended Bundle Ordering", ", ".join(bundle_report.bundle_ordering))
    summary_table.add_row("Total Bundles Assembled", str(len(bundle_report.bundles)))
    summary_table.add_row("Total Skills Bundled", str(sum(len(b.ranked_skills) for b in bundle_report.bundles)))
    summary_table.add_row(
        "Validation Status",
        "PASSED" if bundle_report.evidence.get("validation", {}).get("no_orphan_skills") else "FAILED",
    )
    summary_table.add_row("Coverage Percentage", f"{bundle_report.coverage.coverage_percent}%")
    summary_table.add_row("Bundling Confidence", f"{bundle_report.confidence * 100:.1f}%")

    console.print(summary_table)


@app.command("profiles")
@skills_app.command("profiles")
def profiles_command(
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Synthesize execution-ready Agent Profiles from ExecutionSkillBundleReport."""
    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)

    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    selection_report = discovery_engine.discover_skills(plan)

    ranking_engine = SkillRankingEngine(registry, resolver)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    bundling_engine = SkillBundlingEngine(registry, resolver)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    profile_builder = AgentProfileBuilderEngine(registry, resolver)
    profile_report = profile_builder.build_profiles(bundle_report, plan)

    if json_output:
        console.print_json(data=profile_report.model_dump(mode="json"))
        return

    console.print(
        f"\n[bold cyan]Agent Profile Report:[/] {profile_report.report_id} "
        f"(Bundle Report: {profile_report.bundle_report_id}, Plan: {profile_report.execution_plan_id})"
    )

    # 1. Agent Profiles Table
    profiles_table = Table(title="Synthesized Agent Profiles")
    profiles_table.add_column("Profile ID", style="bold cyan")
    profiles_table.add_column("Agent Role", style="bold yellow")
    profiles_table.add_column("Discipline")
    profiles_table.add_column("Priority", style="bold green")
    profiles_table.add_column("Assigned Bundles")
    profiles_table.add_column("Deliverables")
    profiles_table.add_column("Dependencies")

    for profile in profile_report.profiles:
        prio_str = profile.priority.value if hasattr(profile.priority, "value") else str(profile.priority)
        bundles_str = ", ".join(profile.assigned_bundle_references)
        deliv_str = ", ".join(profile.expected_deliverables) if profile.expected_deliverables else "None"
        deps_str = ", ".join(profile.dependency_profiles) if profile.dependency_profiles else "None"
        profiles_table.add_row(
            profile.profile_id,
            profile.agent_role,
            profile.primary_discipline,
            prio_str,
            bundles_str,
            deliv_str,
            deps_str,
        )
    console.print(profiles_table)

    # 2. Profile Execution Graph & Validation Summary Table
    summary_table = Table(title="Profile Execution Ordering & Validation Summary")
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value")

    summary_table.add_row("Recommended Profile Execution Order", ", ".join(profile_report.recommended_profile_ordering))
    summary_table.add_row("Total Agent Profiles", str(len(profile_report.profiles)))
    summary_table.add_row("Total Bundles Mapped", str(len(profile_report.bundle_mapping)))
    val = profile_report.validation
    summary_table.add_row("Every Bundle Assigned", "YES" if val.get("every_bundle_assigned") else "NO")
    summary_table.add_row("No Orphan Bundles", "YES" if val.get("no_orphan_bundles") else "NO")
    summary_table.add_row("No Duplicate Bundle Ownership", "YES" if val.get("no_duplicate_bundle_ownership") else "NO")
    summary_table.add_row("Dependency Integrity", "PASSED" if val.get("dependency_integrity") else "FAILED")
    summary_table.add_row("Coverage Percentage", f"{profile_report.coverage.coverage_percent}%")
    summary_table.add_row("Synthesis Confidence", f"{profile_report.confidence * 100:.1f}%")

    console.print(summary_table)


@app.command("deployment")
@mission_app.command("deployment")
def deployment_command(
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Generate deterministic Mission Deployment Plan for Swarm execution."""
    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)

    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    selection_report = discovery_engine.discover_skills(plan)

    ranking_engine = SkillRankingEngine(registry, resolver)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    bundling_engine = SkillBundlingEngine(registry, resolver)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    profile_builder = AgentProfileBuilderEngine(registry, resolver)
    profile_report = profile_builder.build_profiles(bundle_report, plan)

    deployment_planner = MissionDeploymentPlanner()
    deployment_plan = deployment_planner.create_deployment_plan(plan, profile_report)

    if json_output:
        console.print_json(data=deployment_plan.model_dump(mode="json"))
        return

    console.print(
        f"\n[bold cyan]Mission Deployment Plan:[/] {deployment_plan.plan_id} "
        f"(Mission: {deployment_plan.mission_id}, SHA-256 Hash: {deployment_plan.deployment_hash[:16]}...)"
    )

    # 1. Execution Waves Table
    waves_table = Table(title="Execution Waves (Waves 1 to 6)")
    waves_table.add_column("Wave", style="bold yellow")
    waves_table.add_column("Name", style="bold cyan")
    waves_table.add_column("Scheduled Profiles")
    waves_table.add_column("Prerequisites")
    waves_table.add_column("Deliverables")
    waves_table.add_column("Gates")

    for wave in deployment_plan.execution_waves:
        profs_str = ", ".join(wave.profile_ids) if wave.profile_ids else "None"
        prereqs_str = ", ".join(map(str, wave.prerequisite_wave_numbers)) if wave.prerequisite_wave_numbers else "None"
        deliv_str = ", ".join(wave.deliverables[:3]) + ("..." if len(wave.deliverables) > 3 else "") if wave.deliverables else "None"
        gates_str = ", ".join(wave.review_gate_ids + wave.approval_gate_ids) if (wave.review_gate_ids or wave.approval_gate_ids) else "None"
        waves_table.add_row(
            f"Wave {wave.wave_number}",
            wave.name,
            profs_str,
            prereqs_str,
            deliv_str,
            gates_str,
        )
    console.print(waves_table)

    # 2. Parallel Groups & Sequential Dependencies Table
    pg_table = Table(title="Parallel Execution Groups & Sequential Dependencies")
    pg_table.add_column("Group / Profile", style="bold cyan")
    pg_table.add_column("Wave", style="bold yellow")
    pg_table.add_column("Concurrently Executing Profiles / Prerequisites")

    for pg in deployment_plan.parallel_groups:
        pg_table.add_row(
            f"[bold green]Parallel Group: {pg.group_id}[/]",
            f"Wave {pg.wave_number}",
            ", ".join(pg.profile_ids),
        )
    for pid, prereqs in deployment_plan.sequential_dependencies.items():
        if prereqs:
            pg_table.add_row(
                pid,
                "Sequential",
                f"Prerequisites: {', '.join(prereqs)}",
            )
    console.print(pg_table)

    # 3. Review Gates & Approval Gates Table
    gates_table = Table(title="Review Gates & Approval Gates")
    gates_table.add_column("Gate ID", style="bold cyan")
    gates_table.add_column("Type", style="bold yellow")
    gates_table.add_column("Wave")
    gates_table.add_column("Target / Approver")
    gates_table.add_column("Blocking", style="bold red")

    for rg in deployment_plan.review_gates:
        gates_table.add_row(
            rg.gate_id,
            f"Review ({rg.review_type})",
            f"Wave {rg.wave_number}",
            ", ".join(rg.trigger_profiles),
            "YES" if rg.blocking else "NO",
        )
    for ag in deployment_plan.approval_gates:
        gates_table.add_row(
            ag.gate_id,
            "Approval",
            f"Wave {ag.wave_number}",
            ag.required_approver,
            "YES" if ag.blocking else "NO",
        )
    console.print(gates_table)

    # 4. Artifact Routes Table
    routes_table = Table(title="Artifact Flow Routes")
    routes_table.add_column("Route ID", style="bold cyan")
    routes_table.add_column("Source Profile (Wave)")
    routes_table.add_column("Target Profile (Wave)")
    routes_table.add_column("Artifact Deliverable")

    for route in deployment_plan.artifact_routes:
        routes_table.add_row(
            route.route_id,
            f"{route.source_profile_id} (W{route.source_wave})",
            f"{route.target_profile_id} (W{route.target_wave})",
            route.artifact_name,
        )
    console.print(routes_table)

    # 5. Validation & Summary Table
    val_table = Table(title="Deployment Plan Validation & Budget Summary")
    val_table.add_column("Metric", style="bold cyan")
    val_table.add_column("Value")

    val = deployment_plan.evidence.get("validation", {})
    val_table.add_row("No Cyclic Execution", "PASSED" if val.get("no_cyclic_execution") else "FAILED")
    val_table.add_row("Every Profile Scheduled", "PASSED" if val.get("every_profile_scheduled") else "FAILED")
    val_table.add_row("No Orphan Profiles", "PASSED" if val.get("no_orphan_profiles") else "FAILED")
    val_table.add_row("Valid Review Path", "PASSED" if val.get("valid_review_path") else "FAILED")
    val_table.add_row("Valid Approval Path", "PASSED" if val.get("valid_approval_path") else "FAILED")
    val_table.add_row("Valid Artifact Routing", "PASSED" if val.get("valid_artifact_routing") else "FAILED")
    val_table.add_row("Deterministic Order", "PASSED" if val.get("deterministic_execution_order") else "FAILED")
    val_table.add_row("Total USD Budget", f"${deployment_plan.budget_allocation.total_budget_usd:.2f}")
    val_table.add_row("Total Mission Timeout", f"{deployment_plan.timeout_rules.total_mission_timeout_seconds}s")
    val_table.add_row("SHA-256 Deployment Hash", deployment_plan.deployment_hash)

    console.print(val_table)


@app.command("initialize")
@mission_app.command("initialize")
def initialize_command(
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Initialize Swarm execution state and produce RuntimeExecutionSnapshot."""
    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)

    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    selection_report = discovery_engine.discover_skills(plan)

    ranking_engine = SkillRankingEngine(registry, resolver)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    bundling_engine = SkillBundlingEngine(registry, resolver)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    profile_builder = AgentProfileBuilderEngine(registry, resolver)
    profile_report = profile_builder.build_profiles(bundle_report, plan)

    deployment_planner = MissionDeploymentPlanner()
    deployment_plan = deployment_planner.create_deployment_plan(plan, profile_report)

    swarm_engine = SwarmInitializationEngine()
    snapshot = swarm_engine.initialize_swarm(
        deployment_plan, explicit_workspace=workspace, repository_root=repository_root
    )

    if json_output:
        console.print_json(data=snapshot.model_dump(mode="json"))
        return

    console.print(
        f"\n[bold cyan]Runtime Execution Snapshot:[/] {snapshot.snapshot_id} "
        f"(Execution UUID: {snapshot.execution_uuid}, SHA-256 Hash: {snapshot.snapshot_hash[:16]}...)"
    )

    # 1. Swarm Overview & Execution UUID Table
    overview_table = Table(title="Swarm Execution Overview & Status")
    overview_table.add_column("Property", style="bold cyan")
    overview_table.add_column("Value")

    overview_table.add_row("Execution UUID", snapshot.execution_uuid)
    overview_table.add_row("Mission ID", snapshot.mission_id)
    overview_table.add_row("Deployment Plan ID", snapshot.deployment_plan_id)
    overview_table.add_row("Active Wave Number", f"Wave {snapshot.execution_cursor.active_wave_number}")
    overview_table.add_row("Execution State", snapshot.execution_cursor.execution_state)
    overview_table.add_row("Total Agent Sessions", str(len(snapshot.sessions)))
    overview_table.add_row("Initial Session State", "READY (All sessions ready for execution)")
    console.print(overview_table)

    # 2. Initialized Agent Sessions Table
    sessions_table = Table(title="Initialized Agent Sessions (READY State)")
    sessions_table.add_column("Session ID", style="bold cyan")
    sessions_table.add_column("Agent Role", style="bold yellow")
    sessions_table.add_column("Discipline")
    sessions_table.add_column("Wave")
    sessions_table.add_column("State", style="bold green")
    sessions_table.add_column("Allocated Budget", style="bold green")

    for record in snapshot.session_map.values():
        sessions_table.add_row(
            record.session_id,
            record.agent_role,
            record.primary_discipline,
            f"Wave {record.wave_number}",
            record.state.value if hasattr(record.state, "value") else str(record.state),
            f"${record.allocated_budget_usd:.2f}",
        )
    console.print(sessions_table)

    # 3. Wave Execution Status Table
    waves_table = Table(title="Execution Waves Status")
    waves_table.add_column("Wave Number", style="bold yellow")
    waves_table.add_column("Name", style="bold cyan")
    waves_table.add_column("Status", style="bold green")
    waves_table.add_column("Assigned Profile Count")

    for w_num in range(1, 7):
        w_stat = snapshot.wave_status.get(w_num)
        if w_stat:
            waves_table.add_row(
                f"Wave {w_stat.wave_number}",
                w_stat.name,
                w_stat.status,
                str(len(w_stat.profile_ids)),
            )
    console.print(waves_table)

    # 4. Checkpoint Status & Storage Connections Table
    storage_table = Table(title="Checkpoint Status & Workspace Storage Connections")
    storage_table.add_column("Component", style="bold cyan")
    storage_table.add_column("Reference / Target Path")

    storage_table.add_row("Current Checkpoint ID", snapshot.checkpoint_status.current_checkpoint_id)
    storage_table.add_row("Restorable Checkpoint Status", "READY / RESTORABLE" if snapshot.checkpoint_status.is_restorable else "NO")
    storage_table.add_row("Sessions Root", snapshot.storage_references.sessions_root)
    storage_table.add_row("Traces Root", snapshot.storage_references.traces_root)
    storage_table.add_row("Logs Root", snapshot.storage_references.logs_root)
    storage_table.add_row("History Root", snapshot.storage_references.history_root)
    storage_table.add_row("Reports Root", snapshot.storage_references.reports_root)
    storage_table.add_row("Artifacts Root", snapshot.storage_references.artifacts_root)
    console.print(storage_table)

    # 5. Budget Status & Validation Summary Table
    val_table = Table(title="Execution Budget & Snapshot Validation Summary")
    val_table.add_column("Metric", style="bold cyan")
    val_table.add_column("Value")

    val = snapshot.evidence.get("validation", {})
    val_table.add_row("All Profiles Initialized", "PASSED" if val.get("all_profiles_initialized") else "FAILED")
    val_table.add_row("All Sessions Mapped", "PASSED" if val.get("all_sessions_mapped") else "FAILED")
    val_table.add_row("No Orphan Sessions", "PASSED" if val.get("no_orphan_sessions") else "FAILED")
    val_table.add_row("Wave Integrity", "PASSED" if val.get("wave_integrity") else "FAILED")
    val_table.add_row("Budget Initialized", "PASSED" if val.get("budget_initialized") else "FAILED")
    val_table.add_row("Checkpoint Initialized", "PASSED" if val.get("checkpoint_initialized") else "FAILED")
    val_table.add_row("Storage Connected", "PASSED" if val.get("storage_connected") else "FAILED")
    val_table.add_row("Deterministic Snapshot", "PASSED" if val.get("deterministic_snapshot") else "FAILED")
    val_table.add_row("Total USD Budget", f"${snapshot.budget_status.total_budget_usd:.2f}")
    val_table.add_row("Spent USD Budget", f"${snapshot.budget_status.spent_budget_usd:.2f}")
    val_table.add_row("Remaining USD Budget", f"${snapshot.budget_status.remaining_budget_usd:.2f}")
    val_table.add_row("SHA-256 Snapshot Hash", snapshot.snapshot_hash)

    console.print(val_table)


@app.command("execute")
@mission_app.command("execute")
def execute_command(
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Execute Swarm autonomously across Waves 1 to 6 and update RuntimeExecutionSnapshot."""
    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)

    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    selection_report = discovery_engine.discover_skills(plan)

    ranking_engine = SkillRankingEngine(registry, resolver)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    bundling_engine = SkillBundlingEngine(registry, resolver)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    profile_builder = AgentProfileBuilderEngine(registry, resolver)
    profile_report = profile_builder.build_profiles(bundle_report, plan)

    deployment_planner = MissionDeploymentPlanner()
    deployment_plan = deployment_planner.create_deployment_plan(plan, profile_report)

    swarm_init_engine = SwarmInitializationEngine()
    initial_snapshot = swarm_init_engine.initialize_swarm(
        deployment_plan, explicit_workspace=workspace, repository_root=repository_root
    )

    exec_engine = AutonomousExecutionEngine()
    updated_snapshot, results = exec_engine.execute_swarm(
        initial_snapshot, repository_root=repository_root
    )

    if json_output:
        data = {
            "snapshot": updated_snapshot.model_dump(mode="json"),
            "execution_results": [r.model_dump(mode="json") for r in results],
        }
        console.print_json(data=data)
        return

    console.print(
        f"\n[bold cyan]Autonomous Execution Complete:[/] {updated_snapshot.snapshot_id} "
        f"(Execution UUID: {updated_snapshot.execution_uuid}, State: {updated_snapshot.execution_cursor.execution_state})"
    )

    # 1. Swarm Execution Summary Table
    summary_table = Table(title="Autonomous Swarm Execution Overview")
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value")

    total_tokens = sum(r.consumed_tokens for r in results)
    total_cost = sum(r.cost_usd for r in results)
    total_artifacts = sum(len(r.produced_artifacts) for r in results)

    summary_table.add_row("Execution UUID", updated_snapshot.execution_uuid)
    summary_table.add_row("Execution State", updated_snapshot.execution_cursor.execution_state)
    summary_table.add_row("Final Wave Reached", f"Wave {updated_snapshot.execution_cursor.active_wave_number}")
    summary_table.add_row("Total Tasks Executed", str(len(results)))
    summary_table.add_row("Total Tokens Consumed", f"{total_tokens:,}")
    summary_table.add_row("Total USD Cost Spent", f"${total_cost:.4f}")
    summary_table.add_row("Remaining USD Budget", f"${updated_snapshot.budget_status.remaining_budget_usd:.2f}")
    summary_table.add_row("Artifacts Produced", str(total_artifacts))
    summary_table.add_row("Updated Snapshot Hash", updated_snapshot.snapshot_hash)
    console.print(summary_table)

    # 2. Wave Progress & Execution Status Table
    wave_table = Table(title="Execution Waves Progress")
    wave_table.add_column("Wave Number", style="bold yellow")
    wave_table.add_column("Wave Name", style="bold cyan")
    wave_table.add_column("Status", style="bold green")
    wave_table.add_column("Completed Profiles")
    wave_table.add_column("Failed Profiles")

    for w_num in range(1, 7):
        w_stat = updated_snapshot.wave_status.get(w_num)
        if w_stat:
            wave_table.add_row(
                f"Wave {w_stat.wave_number}",
                w_stat.name,
                w_stat.status,
                ", ".join(w_stat.completed_profile_ids) if w_stat.completed_profile_ids else "None",
                ", ".join(w_stat.failed_profile_ids) if w_stat.failed_profile_ids else "None",
            )
    console.print(wave_table)

    # 3. Task Execution Results Table
    results_table = Table(title="Task Execution Results")
    results_table.add_column("Task ID", style="bold cyan")
    results_table.add_column("Wave", style="bold yellow")
    results_table.add_column("Session ID")
    results_table.add_column("Status", style="bold green")
    results_table.add_column("Tokens", style="bold green")
    results_table.add_column("Cost", style="bold green")
    results_table.add_column("Artifacts")

    for res in results:
        art_names = [a.name for a in res.produced_artifacts]
        art_str = ", ".join(art_names[:2]) + ("..." if len(art_names) > 2 else "") if art_names else "None"
        results_table.add_row(
            res.task_id,
            f"Wave {res.wave_number}",
            res.session_id,
            res.execution_status.value if hasattr(res.execution_status, "value") else str(res.execution_status),
            f"{res.consumed_tokens:,}",
            f"${res.cost_usd:.4f}",
            art_str,
        )
    console.print(results_table)

    # 4. Storage Traces & Artifact Locations Table
    storage_table = Table(title="Execution Traces & Storage Locations")
    storage_table.add_column("Resource", style="bold cyan")
    storage_table.add_column("Path / Location")

    storage_table.add_row("Sessions Root", updated_snapshot.storage_references.sessions_root)
    storage_table.add_row("Traces Root", updated_snapshot.storage_references.traces_root)
    storage_table.add_row("Logs Root", updated_snapshot.storage_references.logs_root)
    storage_table.add_row("Artifacts Root", updated_snapshot.storage_references.artifacts_root)
    storage_table.add_row("History Root", updated_snapshot.storage_references.history_root)
    console.print(storage_table)


@app.command("coordinate")
@mission_app.command("coordinate")
def coordinate_command(
    request: list[str] = typer.Argument(None, help="Natural language request or plan prompt."),
    workspace: Path | None = typer.Option(None, "--workspace", "-w", help="Explicit workspace path override."),
    repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON representation."),
) -> None:
    """Coordinate Swarm agent communication, artifact exchange, handoffs, and consensus."""
    raw_prompt = " ".join(request) if request else "Build application"
    if request and "--json" in request:
        json_output = True
        raw_prompt = " ".join([r for r in request if r != "--json"])
        if not raw_prompt.strip():
            raw_prompt = "Build application"

    intent_analyzer = IntentAnalyzer()
    intent_report = intent_analyzer.analyze(raw_prompt, explicit_workspace=workspace)

    ws_intelligence = WorkspaceIntelligence()
    ws_ctx = ws_intelligence.analyze_workspace(cwd=repository_root, explicit_workspace=workspace)

    repo_intelligence = RepositoryIntelligence()
    repo_ctx = repo_intelligence.analyze_repository(ws_ctx)

    generator = EngineeringPlanGenerator()
    plan = generator.generate_plan(intent_report, ws_ctx, repo_ctx)

    loader = RepositoryLoader(repository_root)
    registry = loader.load()
    resolver = Resolver(registry)

    discovery_engine = SkillDiscoveryEngine(registry, resolver)
    selection_report = discovery_engine.discover_skills(plan)

    ranking_engine = SkillRankingEngine(registry, resolver)
    ranked_report = ranking_engine.rank_skills(selection_report, plan)

    bundling_engine = SkillBundlingEngine(registry, resolver)
    bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

    profile_builder = AgentProfileBuilderEngine(registry, resolver)
    profile_report = profile_builder.build_profiles(bundle_report, plan)

    deployment_planner = MissionDeploymentPlanner()
    deployment_plan = deployment_planner.create_deployment_plan(plan, profile_report)

    swarm_init_engine = SwarmInitializationEngine()
    initial_snapshot = swarm_init_engine.initialize_swarm(
        deployment_plan, explicit_workspace=workspace, repository_root=repository_root
    )

    exec_engine = AutonomousExecutionEngine()
    exec_snapshot, results = exec_engine.execute_swarm(
        initial_snapshot, repository_root=repository_root
    )

    coord_engine = SwarmCoordinationEngine()
    coord_snapshot, summary = coord_engine.coordinate_swarm(
        exec_snapshot, results, repository_root=repository_root
    )

    if json_output:
        data = {
            "snapshot": coord_snapshot.model_dump(mode="json"),
            "coordination_summary": summary,
        }
        console.print_json(data=data)
        return

    console.print(
        f"\n[bold cyan]Swarm Coordination Complete:[/] {coord_snapshot.snapshot_id} "
        f"(Execution UUID: {coord_snapshot.execution_uuid}, Context Version: v{summary['shared_context_snapshot']['version_index']})"
    )

    # 1. Swarm Coordination Overview Table
    summary_table = Table(title="Swarm Coordination Overview")
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value")

    summary_table.add_row("Execution UUID", coord_snapshot.execution_uuid)
    summary_table.add_row("Messages Dispatched", str(len(summary["messages"])))
    summary_table.add_row("Artifact Exchanges Registered", str(len(summary["artifact_exchanges"])))
    summary_table.add_row("Wave Task Handoffs", str(len(summary["handoffs"])))
    summary_table.add_row("Consensus Gate Decisions", str(len(summary["consensus"])))
    summary_table.add_row("Context Conflicts Detected", str(len(summary["conflicts"])))
    summary_table.add_row("Shared Context Version", f"v{summary['shared_context_snapshot']['version_index']}")
    summary_table.add_row("Coordination Latency", f"{summary['coordination_latency_ms']} ms")
    summary_table.add_row("Updated Snapshot Hash", coord_snapshot.snapshot_hash)
    console.print(summary_table)

    # 2. Messages & Agent Communication Table
    msg_table = Table(title="Agent Messages & Communication Events")
    msg_table.add_column("Message ID", style="bold cyan")
    msg_table.add_column("Sender Session")
    msg_table.add_column("Recipient")
    msg_table.add_column("Subject", style="bold yellow")
    msg_table.add_column("Timestamp")

    for msg in summary["messages"][:5]:
        msg_table.add_row(
            msg["message_id"],
            msg["sender_id"],
            msg["recipient_id"],
            msg["subject"],
            msg["timestamp"][:19],
        )
    console.print(msg_table)

    # 3. Artifact Exchange & Lineage Table
    art_table = Table(title="Artifact Exchange & Version Lineage")
    art_table.add_column("Exchange ID", style="bold cyan")
    art_table.add_column("Artifact Name", style="bold yellow")
    art_table.add_column("Owner Profile")
    art_table.add_column("Version", style="bold green")
    art_table.add_column("Delivery Status", style="bold green")

    for ex in summary["artifact_exchanges"][:5]:
        art_table.add_row(
            ex["exchange_id"],
            ex["name"],
            ex["owner_profile_id"],
            ex["version"],
            ex["delivery_status"],
        )
    console.print(art_table)

    # 4. Wave Task Handoffs Table
    hdf_table = Table(title="Wave Task Handoffs")
    hdf_table.add_column("Handoff ID", style="bold cyan")
    hdf_table.add_column("Source Profile")
    hdf_table.add_column("Receiving Profile")
    hdf_table.add_column("Wave Transition", style="bold yellow")
    hdf_table.add_column("Status", style="bold green")

    for hdf in summary["handoffs"][:5]:
        hdf_table.add_row(
            hdf["handoff_id"],
            hdf["source_profile_id"],
            hdf["receiving_profile_id"],
            f"Wave {hdf['source_wave']} → Wave {hdf['target_wave']}",
            hdf["status"],
        )
    console.print(hdf_table)

    # 5. Consensus & Approval Gates Table
    csn_table = Table(title="Consensus & Approval Gate Decisions")
    csn_table.add_column("Consensus ID", style="bold cyan")
    csn_table.add_column("Wave", style="bold yellow")
    csn_table.add_column("Gate Name")
    csn_table.add_column("Type")
    csn_table.add_column("Decision", style="bold green")

    for csn in summary["consensus"]:
        csn_table.add_row(
            csn["consensus_id"],
            f"Wave {csn['wave_number']}",
            csn["gate_name"],
            csn["consensus_type"],
            csn["decision"],
        )
    console.print(csn_table)


@app.command("scaffold")
def scaffold_command(
    snapshot_path: Path | None = typer.Option(
        None, "--snapshot", "-s", help="Path to RuntimeExecutionSnapshot JSON file."
    ),
    workspace_path: Path | None = typer.Option(
        None, "--workspace", "-w", help="Target workspace path to scaffold."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output raw JSON WorkspaceScaffoldReport."
    ),
) -> None:
    """Scaffold target project workspace deterministically from a RuntimeExecutionSnapshot."""
    import sys
    try:
        ws_path = (workspace_path or Path.cwd()).resolve()
        snapshot: Optional[RuntimeExecutionSnapshot] = None

        if snapshot_path is not None:
            snap_file = snapshot_path.resolve()
            if not snap_file.exists():
                console.print(f"[red]Snapshot Error:[/] Snapshot file '{snap_file}' does not exist.")
                sys.exit(1)
            raw_data = json.loads(snap_file.read_text(encoding="utf-8"))
            snapshot = RuntimeExecutionSnapshot.model_validate(raw_data)
        else:
            ws_intel = WorkspaceIntelligence()
            ws_context = ws_intel.analyze_workspace(cwd=ws_path, explicit_workspace=ws_path)
            repo_intel = RepositoryIntelligence()
            repo_context = repo_intel.analyze_repository(ws_context)

            intent_report = IntentReport(
                raw_request="Scaffold target project workspace",
                primary_intent="scaffold",
                extracted_domain="engineering",
                confidence_score=1.0,
            )
            plan_gen = EngineeringPlanGenerator()
            exec_plan = plan_gen.generate_plan(intent_report, ws_context, repo_context)

            registry = Resolver().load_registry()
            resolver = Resolver()
            discovery_engine = SkillDiscoveryEngine(registry, resolver)
            ranking_engine = SkillRankingEngine(registry, resolver)
            bundling_engine = SkillBundlingEngine(registry, resolver)
            builder_engine = AgentProfileBuilderEngine(registry, resolver)
            deployment_planner = MissionDeploymentPlanner()

            sel_report = discovery_engine.discover_skills(exec_plan)
            rnk_report = ranking_engine.rank_skills(sel_report, exec_plan)
            bnd_report = bundling_engine.bundle_skills(rnk_report, exec_plan, sel_report)
            prf_report = builder_engine.build_profiles(bnd_report, exec_plan)
            deployment_plan = deployment_planner.create_deployment_plan(exec_plan, prf_report)

            init_engine = SwarmInitializationEngine()
            snapshot = init_engine.initialize_swarm(deployment_plan)

        engine = WorkspaceScaffoldEngine()
        scaffold_report = engine.scaffold_workspace(snapshot, workspace_override=ws_path)

        if json_output:
            console.print_json(data=scaffold_report.model_dump(mode="json"))
            return

        console.print(f"[bold green]✓ Workspace Scaffold Complete[/] ({scaffold_report.scaffold_id})")

        overview_table = Table(title="Workspace Scaffold Summary")
        overview_table.add_column("Property", style="bold cyan")
        overview_table.add_column("Value", style="bold yellow")
        overview_table.add_row("Scaffold ID", scaffold_report.scaffold_id)
        overview_table.add_row("Workspace ID", scaffold_report.workspace_id)
        overview_table.add_row("Workspace Root", scaffold_report.workspace_root)
        overview_table.add_row("Technology Stack", scaffold_report.technology_stack)
        overview_table.add_row("Scaffold Hash", scaffold_report.scaffold_hash[:16] + "...")
        overview_table.add_row("Directories Initialized", str(len(scaffold_report.created_directories)))
        overview_table.add_row("Files Scaffolded", str(len(scaffold_report.created_files)))
        console.print(overview_table)

        dir_table = Table(title="Initialized Workspace Directories")
        dir_table.add_column("Directory Path", style="bold green")
        for d in scaffold_report.created_directories:
            dir_table.add_row(d)
        console.print(dir_table)

        file_table = Table(title="Scaffolded Configuration & Build Files")
        file_table.add_column("File Path", style="bold cyan")
        file_table.add_column("Status", style="bold yellow")
        for f in scaffold_report.created_files:
            status = scaffold_report.configuration_summary.get(f, "created")
            file_table.add_row(f, status)
        console.print(file_table)

    except Exception as exc:
        console.print(f"[red]Scaffold Error:[/] {str(exc)}")
        sys.exit(1)


@app.command("blueprint-project")
def blueprint_project_command(
    scaffold_path: Path | None = typer.Option(
        None, "--scaffold", "-s", help="Path to WorkspaceScaffoldReport JSON file."
    ),
    workspace_path: Path | None = typer.Option(
        None, "--workspace", "-w", help="Target workspace path."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output raw JSON ProjectBlueprintReport."
    ),
) -> None:
    """Generate deterministic Project Blueprint from a WorkspaceScaffoldReport."""
    import sys
    try:
        ws_path = (workspace_path or Path.cwd()).resolve()
        scaffold_report: Optional[WorkspaceScaffoldReport] = None

        if scaffold_path is not None:
            scaf_file = scaffold_path.resolve()
            if not scaf_file.exists():
                console.print(f"[red]Scaffold Error:[/] Scaffold report file '{scaf_file}' does not exist.")
                sys.exit(1)
            raw_data = json.loads(scaf_file.read_text(encoding="utf-8"))
            scaffold_report = WorkspaceScaffoldReport.model_validate(raw_data)
        else:
            ws_intel = WorkspaceIntelligence()
            ws_context = ws_intel.analyze_workspace(cwd=ws_path, explicit_workspace=ws_path)
            repo_intel = RepositoryIntelligence()
            repo_context = repo_intel.analyze_repository(ws_context)

            intent_report = IntentReport(
                raw_request="Scaffold target project workspace for blueprint",
                primary_intent="scaffold",
                extracted_domain="engineering",
                confidence_score=1.0,
            )
            plan_gen = EngineeringPlanGenerator()
            exec_plan = plan_gen.generate_plan(intent_report, ws_context, repo_context)

            registry = Resolver().load_registry()
            resolver = Resolver()
            discovery_engine = SkillDiscoveryEngine(registry, resolver)
            ranking_engine = SkillRankingEngine(registry, resolver)
            bundling_engine = SkillBundlingEngine(registry, resolver)
            builder_engine = AgentProfileBuilderEngine(registry, resolver)
            deployment_planner = MissionDeploymentPlanner()

            sel_report = discovery_engine.discover_skills(exec_plan)
            rnk_report = ranking_engine.rank_skills(sel_report, exec_plan)
            bnd_report = bundling_engine.bundle_skills(rnk_report, exec_plan, sel_report)
            prf_report = builder_engine.build_profiles(bnd_report, exec_plan)
            deployment_plan = deployment_planner.create_deployment_plan(exec_plan, prf_report)

            init_engine = SwarmInitializationEngine()
            snapshot = init_engine.initialize_swarm(deployment_plan)

            scaffold_engine = WorkspaceScaffoldEngine()
            scaffold_report = scaffold_engine.scaffold_workspace(snapshot, workspace_override=ws_path)

        blueprint_engine = ProjectBlueprintEngine()
        blueprint_report = blueprint_engine.generate_blueprint(scaffold_report)

        if json_output:
            console.print_json(data=blueprint_report.model_dump(mode="json"))
            return

        console.print(f"[bold green]✓ Project Blueprint Complete[/] ({blueprint_report.blueprint_id})")

        overview_table = Table(title="Project Blueprint Summary")
        overview_table.add_column("Property", style="bold cyan")
        overview_table.add_column("Value", style="bold yellow")
        overview_table.add_row("Blueprint ID", blueprint_report.blueprint_id)
        overview_table.add_row("Workspace ID", blueprint_report.workspace_id)
        overview_table.add_row("Technology Stack", blueprint_report.technology_stack)
        overview_table.add_row("Blueprint Hash", blueprint_report.blueprint_hash[:16] + "...")
        overview_table.add_row("Project Modules", str(len(blueprint_report.project_modules)))
        overview_table.add_row("Disciplines Covered", str(len(blueprint_report.engineering_discipline_ownership)))
        overview_table.add_row("Expected Files", str(len(blueprint_report.expected_files)))
        console.print(overview_table)

        mod_table = Table(title="Project Module Allocations")
        mod_table.add_column("Module ID", style="bold cyan")
        mod_table.add_column("Name", style="bold white")
        mod_table.add_column("Discipline", style="bold green")
        mod_table.add_column("Relative Path", style="bold yellow")
        for m in blueprint_report.project_modules:
            mod_table.add_row(m.module_id, m.name, m.discipline, m.relative_path)
        console.print(mod_table)

        disc_table = Table(title="Engineering Discipline Ownership")
        disc_table.add_column("Discipline", style="bold green")
        disc_table.add_column("Owned Items", style="bold cyan")
        for disc, items in blueprint_report.engineering_discipline_ownership.items():
            if items:
                disc_table.add_row(disc, ", ".join(items[:4]) + (f" (+{len(items)-4} more)" if len(items) > 4 else ""))
        console.print(disc_table)

    except Exception as exc:
        console.print(f"[red]Blueprint Error:[/] {str(exc)}")
        sys.exit(1)


@app.command("allocate")
def allocate_command(
    blueprint_path: Path | None = typer.Option(
        None, "--blueprint", "-b", help="Path to ProjectBlueprintReport JSON file."
    ),
    workspace_path: Path | None = typer.Option(
        None, "--workspace", "-w", help="Target workspace path."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output raw JSON ImplementationAllocationReport."
    ),
) -> None:
    """Allocate implementation targets to engineering disciplines and agent profiles."""
    import sys
    try:
        ws_path = (workspace_path or Path.cwd()).resolve()
        blueprint_report: Optional[ProjectBlueprintReport] = None

        if blueprint_path is not None:
            blu_file = blueprint_path.resolve()
            if not blu_file.exists():
                console.print(f"[red]Blueprint Error:[/] Blueprint report file '{blu_file}' does not exist.")
                sys.exit(1)
            raw_data = json.loads(blu_file.read_text(encoding="utf-8"))
            blueprint_report = ProjectBlueprintReport.model_validate(raw_data)
        else:
            ws_intel = WorkspaceIntelligence()
            ws_context = ws_intel.analyze_workspace(cwd=ws_path, explicit_workspace=ws_path)
            repo_intel = RepositoryIntelligence()
            repo_context = repo_intel.analyze_repository(ws_context)

            intent_report = IntentReport(
                raw_request="Scaffold and blueprint workspace for allocation",
                primary_intent="scaffold",
                extracted_domain="engineering",
                confidence_score=1.0,
            )
            plan_gen = EngineeringPlanGenerator()
            exec_plan = plan_gen.generate_plan(intent_report, ws_context, repo_context)

            registry = Resolver().load_registry()
            resolver = Resolver()
            discovery_engine = SkillDiscoveryEngine(registry, resolver)
            ranking_engine = SkillRankingEngine(registry, resolver)
            bundling_engine = SkillBundlingEngine(registry, resolver)
            builder_engine = AgentProfileBuilderEngine(registry, resolver)
            deployment_planner = MissionDeploymentPlanner()

            sel_report = discovery_engine.discover_skills(exec_plan)
            rnk_report = ranking_engine.rank_skills(sel_report, exec_plan)
            bnd_report = bundling_engine.bundle_skills(rnk_report, exec_plan, sel_report)
            prf_report = builder_engine.build_profiles(bnd_report, exec_plan)
            deployment_plan = deployment_planner.create_deployment_plan(exec_plan, prf_report)

            init_engine = SwarmInitializationEngine()
            snapshot = init_engine.initialize_swarm(deployment_plan)

            scaffold_engine = WorkspaceScaffoldEngine()
            scaffold_report = scaffold_engine.scaffold_workspace(snapshot, workspace_override=ws_path)

            blueprint_engine = ProjectBlueprintEngine()
            blueprint_report = blueprint_engine.generate_blueprint(scaffold_report)

        allocation_engine = ImplementationAllocationEngine()
        allocation_report = allocation_engine.allocate_implementation(blueprint_report)

        if json_output:
            console.print_json(data=allocation_report.model_dump(mode="json"))
            return

        console.print(f"[bold green]✓ Implementation Allocation Complete[/] ({allocation_report.allocation_id})")

        overview_table = Table(title="Implementation Allocation Summary")
        overview_table.add_column("Property", style="bold cyan")
        overview_table.add_column("Value", style="bold yellow")
        overview_table.add_row("Allocation ID", allocation_report.allocation_id)
        overview_table.add_row("Blueprint ID", allocation_report.blueprint_id)
        overview_table.add_row("Technology Stack", allocation_report.technology_stack)
        overview_table.add_row("Allocation Hash", allocation_report.allocation_hash[:16] + "...")
        overview_table.add_row("Total Allocated Targets", str(len(allocation_report.allocated_targets)))
        overview_table.add_row("Agent Profiles Assigned", str(len(allocation_report.agent_ownership)))
        overview_table.add_row("Disciplines Covered", str(len(allocation_report.discipline_ownership)))
        overview_table.add_row("Execution Order Length", str(len(allocation_report.execution_order)))
        console.print(overview_table)

        agent_table = Table(title="Agent Profile Ownership & Target Allocations")
        agent_table.add_column("Profile ID", style="bold cyan")
        agent_table.add_column("Role Title", style="bold green")
        agent_table.add_column("Assigned Targets Count", style="bold yellow")
        for prof_id, targets_list in allocation_report.agent_ownership.items():
            first_target = next((t for t in allocation_report.allocated_targets if t.owning_profile_id == prof_id), None)
            role_name = first_target.owning_profile_role if first_target else "Engineering Agent"
            agent_table.add_row(prof_id, role_name, str(len(targets_list)))
        console.print(agent_table)

    except Exception as exc:
        console.print(f"[red]Allocation Error:[/] {str(exc)}")
        sys.exit(1)


REGISTERED_CLI_COMMANDS: set[str] = {
    "workspace", "workspace-context", "repository", "doctor", "history", "events", "list", "inspect",
    "context", "run", "plan", "models", "explain", "policy",
    "optimize", "audit", "approvals", "permissions", "budget",
    "providers", "capabilities", "capability", "organization", "blueprint", "session", "execute", "recommend-model", "tools",
    "mcp", "recommend-tool", "invoke", "search", "mission", "intent", "skills", "rank-skills", "bundles", "profiles", "deployment", "initialize", "coordinate",
    "review", "retry", "resume", "recovery", "collaborate", "conversation", "thread", "handoff", "artifact", "scaffold", "blueprint-project", "allocate",
    "--help", "-h", "--version"
}









def main(args: list[str] | None = None) -> None:
    import sys
    raw_args = sys.argv[1:] if args is None else list(args)

    first_cmd = None
    explicit_ws = None
    idx = 0
    cmd_args = []
    while idx < len(raw_args):
        token = raw_args[idx]
        if token in ("--workspace", "-w") and idx + 1 < len(raw_args):
            explicit_ws = Path(raw_args[idx + 1])
            idx += 2
            continue
        if not token.startswith("-"):
            first_cmd = token
            cmd_args = raw_args[idx:]
            break
        idx += 1

    if first_cmd is not None and first_cmd not in REGISTERED_CLI_COMMANDS:
        try:
            raw_prompt = " ".join(cmd_args)
            analyzer = IntentAnalyzer()
            intent_report = analyzer.analyze(raw_prompt, explicit_workspace=explicit_ws)

            ws_intel = WorkspaceIntelligence()
            ws_context = ws_intel.analyze_workspace(cwd=Path.cwd(), explicit_workspace=explicit_ws)

            repo_intel = RepositoryIntelligence()
            repo_context = repo_intel.analyze_repository(ws_context)

            plan_gen = EngineeringPlanGenerator()
            exec_plan = plan_gen.generate_plan(intent_report, ws_context, repo_context)

            if intent_report.confidence_score < 0.80:
                console.print(f"[yellow]Warning:[/] Intent confidence score is low ({intent_report.confidence_score:.2f}).")
                if intent_report.unknown_items:
                    console.print(f"[yellow]Missing or ambiguous information:[/] {', '.join(intent_report.unknown_items)}")

            intake = MissionIntake()
            mission_request = intake.process_intake(
                raw_prompt,
                explicit_workspace=explicit_ws,
                parameters={
                    "intent_report": intent_report.model_dump(mode="json"),
                    "workspace_context": ws_context.model_dump(mode="json"),
                    "repository_context": repo_context.model_dump(mode="json"),
                    "engineering_execution_plan": exec_plan.model_dump(mode="json"),
                },
            )
            resolver = MissionResolver()
            resolved_mission = resolver.resolve_mission(mission_request)
            orchestrator = MissionOrchestrator()
            exec_request = orchestrator.orchestrate_mission(resolved_mission)
            console.print_json(data=exec_request.model_dump(mode="json"))
            sys.exit(0)
        except (IntentAnalysisError, MissionIntakeError, MissionResolutionError, MissionOrchestrationError) as exc:
            console.print(f"[red]Mission Error:[/] {getattr(exc, 'message', str(exc))}")
            sys.exit(1)

    app(args=raw_args)



if __name__ == "__main__":
    main()
