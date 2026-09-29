"""
Rich Interactive Terminal User Interface (TUI) for AEX Agent.
slt-inspired layout: header panel with ◆ name + model badge, transcript
blocks (user prompt with gold ❯, streaming assistant markdown, gold
tool-call badges with ✓/✗ results), an input frame, and a colored key
hint bar — all rendered with rich.

Rendering strategy (fixes blank-screen-on-provider-error):
- The transcript is printed PERMANENTLY with console.print() — everything
  stays in scrollback, nothing vanishes between turns.
- rich Live (transient) is used ONLY during the streaming agent turn for
  live markdown repaint; the final text is printed permanently after.
- prompt_toolkit owns the input line (history, completion) between turns.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aex_agent.agent.core import EXAgent
from aex_agent.cli.commands import commands_registry
from aex_agent.cli.logo import logo_splash
from aex_agent.config import load_config
from aex_constants import APP_NAME, VERSION, get_aex_home

console = Console()

ACCENT = "bright_cyan"
GOLD = "gold3"
DIM = "dim"


# ─────────────────────────────────────────────────────────────────────────────
# Builders (permanent console.print — scrollback-safe)
# ─────────────────────────────────────────────────────────────────────────────

def print_header(model: str, provider: str) -> None:
    """slt: ui.bordered(Rounded).row( ◆ Agent | badge(model) | spacer | stat )"""
    grid = Table.grid(padding=(0, 2))
    grid.add_column(justify="left")
    grid.add_column(justify="left")
    grid.add_column(justify="right", ratio=1)
    grid.add_column(justify="right")
    grid.add_row(
        Text("◆ ", style=f"bold {ACCENT}") + Text(APP_NAME, style="bold white"),
        Text(f" {model}", style=f"bold {GOLD}"),
        Text(""),
        Text(provider, style=DIM),
    )
    console.print(Panel(grid, border_style=ACCENT, padding=(0, 1)))


def print_tool_card(tool_name: str, args_str: str = "") -> None:
    """slt: ui.bordered(Rounded).row( badge('Read'), text(' src/...').dim() )"""
    inner = Table.grid(padding=(0, 1))
    inner.add_column()
    inner.add_column(ratio=1)
    badge = Text(f" {tool_name} ", style=f"bold black on {GOLD}")
    args_txt = Text(args_str[:100] + ("…" if len(args_str) > 100 else ""), style=DIM)
    inner.add_row(badge, args_txt)
    console.print(Panel(inner, border_style=GOLD, padding=(0, 1)))


def print_input_frame() -> None:
    """slt: ui.bordered(Rounded).row( '> ' | text_input placeholder )"""
    body = Table.grid(padding=(0, 1))
    body.add_column()
    body.add_column(ratio=1)
    body.add_row(Text("❯", style=f"bold {GOLD}"), Text("Ask anything…", style=DIM))
    console.print(Panel(body, border_style=ACCENT, padding=(0, 1)))


def print_help_bar() -> None:
    """slt: ui.help_colored([('Enter','send'), ...])"""
    keys = [("Enter", "send"), ("Ctrl+C", "cancel"), ("/help", "commands"), ("/exit", "quit")]
    line = Text("")
    for i, (k, v) in enumerate(keys):
        if i:
            line.append("  ·  ", style=DIM)
        line.append(k, style=f"bold {ACCENT}")
        line.append(f" {v}", style=DIM)
    console.print(line)


def print_user_prompt(text: str) -> None:
    grid = Table.grid(padding=(0, 1))
    grid.add_column()
    grid.add_column(ratio=1)
    grid.add_row(Text("❯", style=f"bold {GOLD}"), Text(text, style="bold"))
    console.print()
    console.print(grid)


def print_thought_hint(first_line: str) -> None:
    console.print(Text(f"◆ thought: {first_line}…", style=DIM))


def print_footer_stats(tool_calls: int, session_id: str) -> None:
    plural = "s" if tool_calls != 1 else ""
    console.print()
    console.print(Text(f"  {tool_calls} tool call{plural} · session {session_id[:8]}", style=DIM))


# ─────────────────────────────────────────────────────────────────────────────
# Interactive loop
# ─────────────────────────────────────────────────────────────────────────────

async def run_interactive_tui(session_id: Optional[str] = None) -> None:
    cfg = load_config()

    history_file = get_aex_home() / "cli_history.txt"
    slash_commands = [f"/{c.name}" for c in commands_registry.list_commands()]
    completer = WordCompleter(slash_commands, ignore_case=True, match_middle=False)

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
    )

    agent = EXAgent(config=cfg, session_id=session_id)
    ctx = {"agent": agent, "config": cfg}

    # Emblem splash, then the compact header
    console.print(logo_splash(
        title=APP_NAME,
        subtitle=f"v{VERSION}  ·  {cfg.model}  ·  {cfg.provider}",
        style="gold3",
        accent="bright_cyan",
    ))
    print_header(cfg.model, cfg.provider)

    while True:
        try:
            user_input = await prompt_session.prompt_async("❯ ", multiline=False)
            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input in ["/exit", "/quit", "exit", "quit"]:
                console.print(Text("Session closed. Memory preserved.", style=DIM))
                break

            # Slash commands → run, print output directly
            if user_input.startswith("/"):
                handled, output = commands_registry.handle(user_input, ctx)
                if handled:
                    console.print()
                    console.print(Markdown(output))
                    continue

            print_user_prompt(user_input)

            # ── Agent turn ────────────────────────────────────────────
            accumulated_text = ""
            accumulated_thinking = ""
            thinking_shown = False
            live: Optional[Live] = None

            def _close_live() -> None:
                nonlocal live
                if live is not None:
                    live.update(Markdown(accumulated_text))
                    live.refresh()
                    live.stop()
                    live = None

            def on_stream(kind: str, delta: str) -> None:
                nonlocal accumulated_text, accumulated_thinking, thinking_shown, live
                if kind == "thinking":
                    accumulated_thinking += delta
                    return
                if kind == "content":
                    if accumulated_thinking and not thinking_shown:
                        head = accumulated_thinking.strip().splitlines()
                        first = head[0][:70] if head else ""
                        print_thought_hint(first)
                        thinking_shown = True
                    if accumulated_text.strip():
                        _close_live()  # first real content ends any error-only block
                    accumulated_text += delta
                    if live is None:
                        live = Live(console=console, refresh_per_second=16, auto_refresh=False, transient=True)
                        live.start()
                    live.update(Markdown(accumulated_text))
                    live.refresh()

            def on_tool_status(event: str, tool_name: str, data: dict) -> None:
                _close_live()
                if event == "invoking":
                    args_str = ""
                    try:
                        if isinstance(data.get("command"), str):
                            args_str = data["command"]
                        elif isinstance(data.get("path"), str):
                            args_str = data["path"]
                    except Exception:
                        pass
                    print_tool_card(tool_name, args_str)
                elif event == "completed":
                    ok = bool(data.get("success"))
                    console.print(
                        Text("  ✓ done", style="green") if ok
                        else Text("  ✗ failed", style="bold red")
                    )

            print()  # gap before response
            try:
                res = await agent.run_conversation_async(
                    user_message=user_input,
                    stream_callback=on_stream,
                    tool_status_callback=on_tool_status,
                )
            finally:
                _close_live()
                if not accumulated_text.strip():
                    console.print(
                        Text(
                            "✘ no assistant output — provider error; run `aex setup` to test connection",
                            style="bold red",
                        )
                    )
                elif accumulated_text.startswith("[Provider Error"):
                    # Render provider errors as a red error card, not markdown
                    console.print(Text(accumulated_text.strip(), style="bold red"))
                else:
                    console.print()

            if accumulated_text.strip() and not accumulated_text.startswith("[Provider Error"):
                # Persist the final markdown (Live is transient — reprint full text)
                console.print(Markdown(accumulated_text))

            turns = res.get("tool_calls_count", 0)
            if turns:
                print_footer_stats(turns, agent.session_id)

        except (KeyboardInterrupt, EOFError):
            console.print(Text("Session terminated by user.", style=DIM))
            break
        except Exception as e:
            console.print(f"[bold red]✘ Session Error:[/bold red] {e}")


def main():
    asyncio.run(run_interactive_tui())


if __name__ == "__main__":
    main()