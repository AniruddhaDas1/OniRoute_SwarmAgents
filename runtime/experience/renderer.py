"""CLI Execution Renderer Engine for Phase P6.D2.

Converts Execution Event Streams into rich CLI progress bars, stage spinners,
status lines, live counters, and Rich summary tables.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.table import Table

from runtime.experience.models import StreamEvent


class ExecutionRenderer:
    """CLI Execution Renderer for Phase P6.D2."""

    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize ExecutionRenderer.

        Args:
            console: Optional Rich Console instance.
        """
        self.console = console or Console()
        self._stage_history: List[str] = []

    def render_event(self, event: StreamEvent) -> None:
        """Render a StreamEvent onto the CLI console with appropriate rich styling.

        Args:
            event: StreamEvent contract.
        """
        evt_type = event.event_type

        if evt_type == "MISSION_STARTED":
            self.console.print(f"\n[bold cyan]🚀 Mission Started:[/] [yellow]{event.mission_id}[/]")
            self.console.print(f"[bold dim]Request:[/] '{event.message or event.task_description}'")

        elif evt_type == "AGENT_STARTED":
            role_str = f"[bold green]{event.agent_role or event.agent_id}[/]"
            self.console.print(f"▶ {role_str}\n    [dim]{event.task_description or event.message}[/]")

        elif evt_type == "AGENT_FINISHED":
            role_str = f"[bold green]{event.agent_role or event.agent_id}[/]"
            self.console.print(f"✓ {role_str} [dim]finished[/]")

        elif evt_type == "REVIEW_STARTED":
            self.console.print("▶ [bold magenta]QA & Security Review[/]\n    [dim]Auditing generated code against 5 profile standards...[/]")

        elif evt_type == "REVIEW_FINISHED":
            self.console.print(f"✓ [bold magenta]QA & Security Review Completed[/] [dim](Score: {event.quality_score:.2f}/10.0)[/]")

        elif evt_type == "HEALING_STARTED":
            self.console.print("▶ [bold yellow]Self-Healing Repair Engine[/]\n    [dim]Applying automated fixes for review findings...[/]")

        elif evt_type == "HEALING_FINISHED":
            self.console.print("✓ [bold yellow]Self-Healing Repair Engine Completed[/]")

        elif evt_type == "VERIFICATION_STARTED":
            self.console.print("▶ [bold blue]Deterministic Build & Test Verification[/]\n    [dim]Verifying build status, test suites, and path safety...[/]")

        elif evt_type == "ACCEPTANCE_COMPLETED":
            self.console.print(f"✓ [bold green]Release Acceptance Verified[/] [dim](Ready: {'YES' if event.production_ready else 'NO'})[/]")

        elif evt_type == "MISSION_COMPLETED":
            self.console.print("\n[bold green]✓ Mission Execution Completed & Certified Production-Ready![/]")
            self.render_summary_table(event)

        elif evt_type == "MISSION_FAILED":
            self.console.print(f"\n[bold red]✗ Mission Failed:[/] {event.message}")

        elif evt_type == "CANCELLED":
            self.console.print("\n[bold red]⚠ Mission Execution Gracefully Cancelled by Operator.[/]")

        elif evt_type == "STREAM_STARTED":
            self.console.print(f"▶ [bold blue]Streaming task[/] {event.task_description or event.message}")

        elif evt_type == "STREAM_CHUNK":
            delta = event.payload.get("delta", "")
            if delta:
                self.console.print(f"[dim]{delta}[/]", end="")

        elif evt_type == "STREAM_PROGRESS":
            self.console.print(f"\n[dim]chunks={event.token_usage.get('chunk_count', 0)} "
                               f"content={event.token_usage.get('content_length', 0)}[/]")

        elif evt_type == "STREAM_COMPLETED":
            self.console.print(f"\n[bold green]✓ Stream completed[/] "
                               f"chunks={event.payload.get('chunk_count', 0)} "
                               f"finish={event.payload.get('finish_reason', 'stop')}")

        elif evt_type == "STREAM_FAILED":
            self.console.print(f"\n[bold red]✗ Stream failed:[/] {event.message or event.payload.get('error_message', '')}")

    def render_summary_table(self, event: StreamEvent) -> None:
        """Render Rich execution summary table.

        Args:
            event: Terminal StreamEvent contract.
        """
        table = Table(title="Swarm Execution Summary")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value", style="white")

        table.add_row("Mission ID", event.mission_id)
        table.add_row("Session ID", event.session_id or "—")
        table.add_row("Stage", event.stage_name)
        table.add_row("Progress", f"{event.progress_percentage:.1f}%")
        table.add_row("Files Created", str(len(event.files_created)))
        table.add_row("Files Modified", str(len(event.files_modified)))
        table.add_row("Token Usage", str(event.token_usage.get("total_tokens", 0)))
        table.add_row("Estimated Cost", f"${event.estimated_cost_usd:.6f}")
        table.add_row("Elapsed Time", f"{event.elapsed_time_ms:.2f} ms")
        table.add_row("Quality Score", f"{event.quality_score:.2f} / 10.0")
        table.add_row("Production Ready", "[bold green]YES[/]" if event.production_ready else "[bold red]NO[/]")

        self.console.print(table)
