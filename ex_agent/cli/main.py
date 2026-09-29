"""
Main CLI Dispatcher for EX Agent.
Entrypoint for `ex` command across Windows, macOS, and Linux.
"""
from __future__ import annotations

import asyncio
import click
from rich.console import Console
from rich.table import Table

from ex_agent.cli.setup_wizard import run_setup_wizard
from ex_agent.cli.tui import run_interactive_tui
from ex_agent.config import load_config, save_config
from ex_agent.gateway.scheduler import CronScheduler
from ex_agent.gateway.server import run_gateway
from ex_agent.memory.persistent import MemoryManager
from ex_agent.skills.manager import SkillManager
from ex_agent.tools.toolsets import TOOLSETS
from ex_constants import APP_NAME, VERSION

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context):
    """EX Agent: Autonomous, self-improving AI agent harness."""
    if ctx.invoked_subcommand is None:
        from ex_agent.cli.textual_tui import run_interactive_tui
        run_interactive_tui()


@main.command("chat")
@click.option("--model", "-m", help="Override active model for this session")
@click.option("--provider", "-p", help="Override active provider for this session")
@click.option("--session", "-s", help="Resume or specify a session ID")
@click.option("--classic", "-c", is_flag=True, help="Use the classic prompt_toolkit TUI instead of the full-screen app")
def cmd_chat(model: str, provider: str, session: str, classic: bool):
    """Start an interactive chat session in the terminal TUI."""
    cfg = load_config()
    if model:
        cfg.model = model
    if provider:
        cfg.provider = provider
    if classic:
        from ex_agent.cli.tui import run_interactive_tui
        asyncio.run(run_interactive_tui(session_id=session))
    else:
        from ex_agent.cli.textual_tui import run_interactive_tui
        run_interactive_tui(session_id=session)


@main.command("gateway")
@click.option("--host", "-h", default=None, help="Host address to bind the gateway server")
@click.option("--port", "-p", default=None, type=int, help="Port to bind the gateway server (default: 8642)")
def cmd_gateway(host: str, port: int):
    """Start the OpenAI-compatible API server and background cron scheduler."""
    run_gateway(host=host, port=port)


@main.command("model")
@click.argument("new_model", required=False)
@click.option("--provider", "-p", help="Provider name")
def cmd_model(new_model: str, provider: str):
    """View or switch active model and provider."""
    cfg = load_config()
    if not new_model and not provider:
        console.print(f"[bold cyan]Active Model:[/bold cyan] {cfg.model}")
        console.print(f"[bold yellow]Active Provider:[/bold yellow] {cfg.provider}")
        console.print(f"[dim]Base URL:[/dim] {cfg.resolve_base_url()}")
        return

    if new_model:
        cfg.model = new_model
    if provider:
        cfg.provider = provider
    save_config(cfg)
    console.print(f"[bold green]✔ Model updated to:[/bold green] {cfg.model} ({cfg.provider})")


@main.command("memory")
@click.option("--clear", is_flag=True, help="Reset persistent memories")
def cmd_memory(clear: bool):
    """Inspect or manage persistent MEMORY.md and USER.md."""
    mgr = MemoryManager()
    if clear:
        mgr.replace_memory("# World & Project Knowledge Base\n")
        mgr.replace_user("# User Profile & Preferences\n")
        console.print("[bold yellow]Persistent memories reset.[/bold yellow]")
        return

    summary = mgr.get_summary()
    console.print(f"[bold cyan]=== MEMORY.md ({summary['memory_chars']}/{summary['memory_max']} chars) ===[/bold cyan]")
    console.print(mgr.read_memory())
    console.print(f"\n[bold yellow]=== USER.md ({summary['user_chars']}/{summary['user_max']} chars) ===[/bold yellow]")
    console.print(mgr.read_user())


@main.command("skills")
def cmd_skills():
    """List all available skills (bundled and learned)."""
    mgr = SkillManager()
    skills = mgr.list_skills()
    table = Table(title="EX Agent Skills Catalog")
    table.add_column("Name", style="bold cyan")
    table.add_column("Origin", style="yellow")
    table.add_column("Description", style="white")

    for s in skills:
        origin = "User (~/.ex/skills)" if s.is_user_skill else "Bundled"
        table.add_row(s.name, origin, s.description)

    console.print(table)


@main.command("tools")
def cmd_tools():
    """List all registered toolsets and capabilities."""
    table = Table(title="EX Agent Registered Toolsets")
    table.add_column("Toolset", style="bold magenta")
    table.add_column("Tools", style="white")

    for ts, tools in TOOLSETS.items():
        table.add_row(ts, ", ".join(tools))

    console.print(table)


@main.command("cron")
def cmd_cron():
    """List all scheduled background automations."""
    sched = CronScheduler()
    jobs = sched.list_jobs()
    if not jobs:
        console.print("[dim]No active cron jobs scheduled.[/dim]")
        return

    table = Table(title="Scheduled Automations")
    table.add_column("Job ID", style="bold cyan")
    table.add_column("Expression", style="yellow")
    table.add_column("Prompt", style="white")

    for j in jobs:
        table.add_row(j.job_id, j.expression, j.prompt)

    console.print(table)


@main.command("setup")
def cmd_setup():
    """Run interactive onboarding setup wizard."""
    run_setup_wizard()


@main.command("version")
def cmd_version():
    """Display EX Agent version."""
    console.print(f"[bold cyan]{APP_NAME}[/bold cyan] version [bold green]{VERSION}[/bold green]")


if __name__ == "__main__":
    main()
