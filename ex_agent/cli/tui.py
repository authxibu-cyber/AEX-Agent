"""
Rich Interactive Terminal User Interface (TUI) for EX Agent.
Features prompt_toolkit input with slash-command autocompletion,
streaming markdown rendering, thinking token folding, and real-time tool indicators.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from ex_agent.agent.core import EXAgent
from ex_agent.cli.commands import commands_registry
from ex_agent.config import load_config
from ex_constants import APP_NAME, VERSION, get_ex_home

console = Console()


def render_banner(model_name: str, provider_name: str) -> None:
    banner_lines = [
        r"            \        |        /            ",
        r"             \       |       /             ",
        r"              \      |      /              ",
        r"               \     |     /               ",
        r"                \    |    /                ",
        r"███████╗██╗  ██╗  \  |  /  ██████╗ ███████╗███╗   ██╗████████╗",
        r"██╔════╝╚██╗██╔╝   \ | /   ██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝",
        r"█████╗   ╚███╔╝ ─────X───── ██║  ███╗█████╗  ██╔██╗ ██║   ██║   ",
        r"██╔══╝   ██╔██╗    / | \    ██║   ██║██╔══╝  ██║╚██╗██║   ██║   ",
        r"███████╗██╔╝ ██╗  /  |  \   ╚██████╔╝███████╗██║ ╚████║   ██║   ",
        r"╚══════╝╚═╝  ╚═╝ /   |   \  ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ",
        r"                ⚔───┼───⚔  crossed swords & shield",
        r"               /    |    \              ",
        r"              /     |     \             ",
        r"             /      ⛨      \            ",
        r"                Autonomous Tier-3 AI Agent Harness (v{VERSION})",
    ]
    banner_text = "\n".join(banner_lines).replace("{VERSION}", VERSION)
    console.print(
        Text(banner_text, style="bold cyan"),
        style="bright_blue",
    )
    console.print(
        f"  Model: [bold green]{model_name}[/bold green] | Provider: [bold yellow]{provider_name}[/bold yellow] | Type [bold white]/help[/bold white] for commands"
    )


async def run_interactive_tui(session_id: Optional[str] = None) -> None:
    cfg = load_config()
    render_banner(cfg.model, cfg.provider)

    history_file = get_ex_home() / "cli_history.txt"
    slash_commands = [f"/{c.name}" for c in commands_registry.list_commands()]
    completer = WordCompleter(slash_commands, ignore_case=True, match_middle=False)

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
    )

    agent = EXAgent(config=cfg, session_id=session_id)
    ctx = {"agent": agent, "config": cfg}

    while True:
        try:
            user_input = await prompt_session.prompt_async(
                [("class:prompt", "\n╭─[EX Agent] \n╰─➤ ")],
            )
            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input in ["/exit", "/quit", "exit", "quit"]:
                console.print("[dim]Exiting EX Agent session. Memory preserved.[/dim]")
                break

            # Handle slash commands
            if user_input.startswith("/"):
                handled, output = commands_registry.handle(user_input, ctx)
                if handled:
                    console.print(Panel(Markdown(output), title="[bold cyan]Command Output[/bold cyan]", border_style="blue"))
                    continue

            # Stream Agent Response
            console.print("\n[bold green]EX Agent:[/bold green]")

            accumulated_text = ""
            accumulated_thinking = ""
            current_live: Optional[Live] = None

            def on_stream(kind: str, delta: str):
                nonlocal accumulated_text, accumulated_thinking
                if kind == "thinking":
                    accumulated_thinking += delta
                elif kind == "content":
                    accumulated_text += delta
                    sys.stdout.write(delta)
                    sys.stdout.flush()

            def on_tool_status(event: str, tool_name: str, data: dict):
                if event == "invoking":
                    console.print(f"\n[bold magenta]⚙ Invoking Tool:[/bold magenta] [cyan]{tool_name}[/cyan] ...")
                elif event == "completed":
                    status = "[green]✔ Done[/green]" if data.get("success") else "[red]✘ Failed[/red]"
                    console.print(f"  {status} [dim]({tool_name})[/dim]")

            # Run conversational turn
            res = await agent.run_conversation_async(
                user_message=user_input,
                stream_callback=on_stream,
                tool_status_callback=on_tool_status,
            )

            # Print thinking if reasoning tokens were produced and not displayed yet
            if res.get("reasoning") and not accumulated_thinking:
                console.print(Panel(res["reasoning"], title="[dim]Cognitive Pulse / Thinking[/dim]", border_style="dim"))

            print()  # newline separator

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session terminated by user.[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Session Error:[/bold red] {e}")


def main():
    asyncio.run(run_interactive_tui())


if __name__ == "__main__":
    main()
