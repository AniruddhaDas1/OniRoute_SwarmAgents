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

app = typer.Typer(help="Local OniRoute repository diagnostics.")
list_app = typer.Typer(help="List repository metadata.")
inspect_app = typer.Typer(help="Inspect one metadata record.")
context_app = typer.Typer(help="Inspect deterministic context metadata.")
app.add_typer(list_app, name="list")
app.add_typer(inspect_app, name="inspect")
app.add_typer(context_app, name="context")
console = Console()


def _resolver(root: Path) -> Resolver:
    return Resolver(RepositoryLoader(root).load())


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

if __name__ == "__main__": app()
