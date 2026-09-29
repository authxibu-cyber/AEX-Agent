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
    """Compact Hermes/agy-style header: gold dot + name, dim meta line, rule."""
    console.print()
    console.print(
        f"  [bold gold3]●[/bold gold3] [bold]{APP_NAME}[/bold] [dim]v{VERSION}[/dim]"
    )
    console.print(
        f"  [dim]model:[/dim] [green]{model_name}[/green]  [dim]·[/dim]  "
        f"[dim]provider:[/dim] [yellow]{provider_name}[/yellow]  [dim]·[/dim]  "
        f"[dim]/help for commands  /exit to quit[/dim]"
    )
    console.print(f"  [dim gold3]{'─' * 66}[/dim gold3]")


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

    last_was_tool = False

    while True:
        try:
            # agy-style minimal prompt: dim ❯ with blinking-free clean line
            user_input = await prompt_session.prompt_async(
                [("class:prompt", "\n❯ ")],
                multiline=False,
            )
            user_input = user_input.strip()
            if not user_input:
                continue
            last_was_tool = False

            if user_input in ["/exit", "/quit", "exit", "quit"]:
                console.print("[dim]Session closed. Memory preserved.[/dim]")
                break

            # Handle slash commands (Hermes-style: dim output, no panel box)
            if user_input.startswith("/"):
                handled, output = commands_registry.handle(user_input, ctx)
                if handled:
                    console.print(f"[dim]{output}[/dim]")
                    continue

            # ── Agent turn ────────────────────────────────────────────────
            console.print()

            accumulated_text = ""
            accumulated_thinking = ""
            thinking_shown = False
            live: Optional[Live] = None

            def _close_inline():
                """Flush live-rendered markdown into the transcript."""
                nonlocal live
                if live is not None:
                    live.update(Markdown(accumulated_text))  # final paint
                    live.refresh()
                    live.stop()
                    live = None
                    console.print()
                    # If the turn produced no visible assistant text, surface it —
                    # otherwise provider errors vanish with transient Live.
                    if not accumulated_text.strip():
                        console.print(
                            "[dim red]✘ (no assistant output — provider returned an error; check `ex setup` connection)[/dim red]"
                        )

            def on_stream(kind: str, delta: str):
                nonlocal accumulated_text, accumulated_thinking, live, thinking_shown
                if kind == "thinking":
                    accumulated_thinking += delta
                    return
                if kind == "content":
                    if accumulated_thinking and not thinking_shown:
                        # collapsible reasoning block, Hermes-style
                        head = accumulated_thinking.strip().splitlines()
                        first = head[0][:70] if head else ""
                        console.print(
                            f"[dim]◆ thought:[/dim] [dim italic]{first}[/dim italic] [dim](hidden — use /export to inspect full reasoning)[/dim]"
                        )
                        thinking_shown = True
                    accumulated_text += delta
                    if live is None:
                        live = Live(
                            console=console, refresh_per_second=12, transient=True
                        )
                        live.start()
                    live.update(Markdown(accumulated_text))

            def on_tool_status(event: str, tool_name: str, data: dict):
                nonlocal live
                # close any streaming block first so tool lines stay aligned
                _close_inline()
                if event == "invoking":
                    console.print(
                        f"  [bold gold3]●[/bold gold3] [bold]{tool_name}[/bold] [dim]running…[/dim]"
                    )
                elif event == "completed":
                    ok = data.get("success")
                    dot = "[green]●[/green]" if ok else "[red]●[/red]"
                    console.print(f"  {dot} [dim]{tool_name}[/dim]")

            try:
                res = await agent.run_conversation_async(
                    user_message=user_input,
                    stream_callback=on_stream,
                    tool_status_callback=on_tool_status,
                )
            finally:
                _close_inline()

            # ── Turn footer (Hermes-style stats row) ─────────────────────
            tokens_note = ""
            turns = res.get("tool_calls_count", 0)
            if turns:
                console.print(
                    f"  [dim]{turns} tool call{'s' if turns != 1 else ''} this turn"
                    f" · session {agent.session_id[:8]}[/dim]"
                )
            console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Session terminated by user.[/dim]")
            break
        except Exception as e:
            console.print(f"[bold red]Session Error:[/bold red] {e}")


def main():
    asyncio.run(run_interactive_tui())


if __name__ == "__main__":
    main()
