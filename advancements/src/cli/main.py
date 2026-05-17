"""
CLI — Typer-based command-line interface for the Kernel Coding Agent.

Usage:
    kca run --mock profiles/sample_tickets/kern_i2c_null_deref.json
    kca run --ticket KERN-123 --repo /path/to/kernel
    kca history
    kca graph
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

app = typer.Typer(
    name="kca",
    help="🔧 Kernel Coding Agent — LangGraph multi-agent bug fixer",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    mock: str = typer.Option(None, "--mock", "-m", help="Path to mock ticket JSON"),
    ticket: str = typer.Option(None, "--ticket", "-t", help="Jira ticket ID"),
    repo: str = typer.Option(".", "--repo", "-r", help="Path to source tree"),
    arch: str = typer.Option("arm64", "--arch", "-a", help="Target architecture"),
    provider: str = typer.Option(None, "--provider", "-p", help="LLM provider override"),
):
    """Run the full agent pipeline on a Jira ticket."""
    from src.graph.orchestrator import compile_graph
    from src.tools.jira_tools import load_mock_ticket
    from src.memory.evolution_store import query_similar, record_evolution

    console.print(Panel.fit(
        "[bold cyan]🔧 Kernel Coding Agent[/bold cyan]\n"
        "[dim]LangGraph Multi-Agent Pipeline[/dim]",
        border_style="cyan",
    ))

    # ── Load ticket ──
    if mock:
        mock_path = Path(mock)
        if not mock_path.exists():
            console.print(f"[red]Error: mock file not found: {mock}[/red]")
            raise typer.Exit(1)
        ticket_data = load_mock_ticket(mock_path)
        ticket_id = ticket_data["ticket_id"]
        console.print(f"  📋 Loaded mock ticket: [bold]{ticket_id}[/bold]")
    elif ticket:
        ticket_id = ticket
        console.print(f"  📋 Ticket: [bold]{ticket_id}[/bold] (mock mode)")
    else:
        console.print("[red]Error: provide --mock <file> or --ticket <id>[/red]")
        raise typer.Exit(1)

    console.print(f"  📁 Source tree: [bold]{repo}[/bold]")
    console.print(f"  🏗️  Architecture: [bold]{arch}[/bold]")

    # ── Check for past fixes ──
    ticket_data_loaded = ticket_data if mock else {"component": "kernel", "summary": ""}
    evo_context = query_similar(
        subsystem=ticket_data_loaded.get("component", ""),
        symptom=ticket_data_loaded.get("summary", ""),
    )
    if evo_context:
        console.print(f"  🧬 Found [bold]{len(evo_context)}[/bold] similar past fixes in evolution store")

    # ── Build initial state ──
    initial_state = {
        "jira_ticket_id": ticket_id,
        "repo_path": str(Path(repo).resolve()),
        "target_arch": arch,
        "messages": [],
        "evolution_context": evo_context,
    }

    if mock:
        initial_state.update({
            "jira_summary": ticket_data.get("summary", ""),
            "jira_description": ticket_data.get("description", ""),
            "jira_labels": ticket_data.get("labels", []),
            "jira_component": ticket_data.get("component", ""),
            "jira_priority": ticket_data.get("priority", "Medium"),
        })

    # ── Compile and run graph ──
    console.print("\n[bold green]▶ Starting pipeline...[/bold green]\n")

    compiled = compile_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    # Stream through nodes and show progress
    phase_icons = {
        "jira_ingest": "📋", "planner": "🗺️", "analyzer": "🔍",
        "builder": "🔨", "reviewer": "👀", "tester": "🧪",
        "debugger": "🐛", "overseer": "🛡️", "finalize": "✅",
        "escalate": "🚨",
    }

    final_state = None
    for event in compiled.stream(initial_state, config, stream_mode="updates"):
        for node_name, updates in event.items():
            icon = phase_icons.get(node_name, "⚙️")
            phase = updates.get("current_phase", node_name)
            console.print(f"  {icon} [bold]{node_name}[/bold] completed")

            # Show key outputs
            if node_name == "planner" and "plan" in updates:
                console.print(Panel(updates["plan"][:500], title="Investigation Plan", border_style="blue"))
            elif node_name == "builder" and "patch" in updates:
                console.print(Panel(updates["patch"][:500], title="Generated Patch", border_style="yellow"))
            elif node_name == "reviewer":
                v = updates.get("review_verdict", "?")
                color = "green" if v == "APPROVE" else "red"
                console.print(f"    Review: [{color}]{v}[/{color}]")
            elif node_name == "tester":
                s = updates.get("test_status", "?")
                color = "green" if s == "PASS" else "red"
                console.print(f"    Tests: [{color}]{s}[/{color}]")
            elif node_name == "debugger":
                rc = updates.get("retry_count", "?")
                console.print(f"    [yellow]Retry #{rc} — analyzing failure...[/yellow]")
            elif node_name == "escalate":
                console.print(f"    [red bold]⚠ Escalated to human — max retries exceeded[/red bold]")

            final_state = updates

    # ── Summary ──
    console.print("\n" + "─" * 60)
    if final_state and final_state.get("current_phase") == "finalize":
        console.print("[bold green]✅ Pipeline completed successfully![/bold green]")
        # Record in evolution store
        record_evolution(
            ticket_id=ticket_id,
            subsystem=initial_state.get("jira_component", ""),
            symptom=initial_state.get("jira_summary", ""),
            root_cause=final_state.get("root_cause", "")[:500] if final_state.get("root_cause") else "",
            fix_patch=final_state.get("patch", "")[:2000] if final_state.get("patch") else "",
            retries=final_state.get("retry_count", 0),
            success=True,
        )
        console.print("  🧬 Fix recorded in evolution store")
    else:
        console.print("[bold red]❌ Pipeline ended (escalated or error)[/bold red]")
        if final_state and final_state.get("error"):
            console.print(f"  Error: {final_state['error'][:300]}")


@app.command()
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of entries"),
):
    """View the evolution store history."""
    from src.memory.evolution_store import get_history

    entries = get_history(limit=limit)
    if not entries:
        console.print("[dim]No evolution history yet.[/dim]")
        return

    table = Table(title="🧬 Evolution Store", show_lines=True)
    table.add_column("ID", style="dim")
    table.add_column("Ticket", style="cyan")
    table.add_column("Subsystem", style="green")
    table.add_column("Symptom", max_width=40)
    table.add_column("Retries", justify="center")
    table.add_column("Success", justify="center")
    table.add_column("Date", style="dim")

    for e in entries:
        success = "✅" if e.get("success") else "❌"
        table.add_row(
            str(e.get("id", "")),
            e.get("ticket_id", ""),
            e.get("subsystem", ""),
            (e.get("symptom", "") or "")[:40],
            str(e.get("retries", 0)),
            success,
            e.get("created_at", "")[:19],
        )
    console.print(table)


@app.command()
def graph():
    """Print the pipeline graph structure (ASCII art)."""
    console.print(Panel.fit(
        "[cyan]jira_ingest[/cyan] → [blue]planner[/blue] → [blue]analyzer[/blue] → "
        "[yellow]builder[/yellow] → [magenta]reviewer[/magenta]\n"
        "                                                    ↓\n"
        "                        [red]debugger[/red] ← [green]tester[/green] ←──┘ (APPROVE)\n"
        "                            ↓                  ↓\n"
        "                        [dim]overseer[/dim]         [green bold]finalize → END[/green bold]\n"
        "                            ↓\n"
        "                        [yellow]builder[/yellow] (retry)\n"
        "                         or [red]END[/red] (circuit break)",
        title="🔧 Agent Pipeline",
        border_style="cyan",
    ))


if __name__ == "__main__":
    app()
