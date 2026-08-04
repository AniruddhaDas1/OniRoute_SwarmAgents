from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from runtime.loader import RepositoryLoader
from runtime.validator import ValidationEngine

app = typer.Typer(help="Local OniRoute repository diagnostics.")
console = Console()


@app.callback()
def main() -> None:
    """OniRoute local runtime commands."""


@app.command()
def doctor(repository_root: Path = typer.Option(Path.cwd(), exists=True, file_okay=False)) -> None:
    """Load and validate the local OniRoute repository."""
    config_path = repository_root / "config/default.yaml"
    if config_path.exists():
        yaml.safe_load(config_path.read_text(encoding="utf-8"))
    registry = RepositoryLoader(repository_root).load()
    report = ValidationEngine(repository_root).validate(registry)
    table = Table(title="OniRoute Repository")
    table.add_column("Record type")
    table.add_column("Count", justify="right")
    for name, count in registry.statistics().items():
        table.add_row(name.replace("_", " ").title(), str(count))
    console.print(table)
    console.print(f"Validation: [{'green' if report.valid else 'red'}]{'PASS' if report.valid else 'FAIL'}[/]")
    console.print(f"Errors: {len(report.errors)}  Warnings: {len(report.warnings)}  Duplicates: {len(registry.duplicates)}")
    for issue in report.issues:
        console.print(f"[{issue.severity}] {issue.code}: {issue.message}")
    if not report.valid:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
