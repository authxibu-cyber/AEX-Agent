"""
Rich Interactive Terminal User Interface (TUI) for EX Agent.
slt-inspired layout: the whole conversation lives inside rounded panels —
header row (◆ Agent name, model badge, provider), a persistent transcript
card showing user prompts, streaming assistant markdown, tool-call cards
with badges, an input box at the bottom, and a colored key-hint bar.

prompt_toolkit still owns the input line (history, completion); rich owns
the transcript above it via a persistent Live view.
"""
from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ex_agent.agent.core import EXAgent
from ex_agent.cli.commands import commands_registry
from ex_agent.config import load_config
from ex_constants import APP_NAME, get_ex_home

console = Console()

ACCENT = "bright_cyan"
GOLD = "gold3"
DIM = "dim"


# ─────────────────────────────────────────────────────────────────────────────
# Renderable builders
# ─────────────────────────────────────────────────────────────────────────────

def build_header(model: str, provider: str) -> Panel:
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
    return Panel(grid, border_style=ACCENT, padding=(0, 1))


class Conversation:
    """Accumulates turn blocks into one Group renderable (the transcript card)."""

    def __init__(self) -> None:
        self.blocks: List[Any] = []

    def user_prompt(self, text: str) -> None:
        self.blocks.append(Text(""))
        row = Table.grid(padding=(0, 1))
        row.add_column()
        row.add_column(ratio=1)
        row.add_row(Text("❯", style=f"bold {GOLD}"), Text(text, style="bold"))
        self.blocks.append(row)

    def assistant_text(self, text: str) -> None:
        self.blocks.append(Text(""))
        self.blocks.append(Markdown(text))

    def thought_hint(self, first_line: str) -> None:
        self.blocks.append(Text(f"  ◆ thought: {first_line}…", style=DIM))

    def tool_card(self, tool_name: str, args_str: str = "") -> None:
        """slt: ui.bordered(Rounded).row( badge('Read'), text(' src/...').dim() )"""
        inner = Table.grid(padding=(0, 1))
        inner.add_column()
        inner.add_column(ratio=1)
        badge = Text(f" {tool_name} ", style=f"bold black on {GOLD}")
        args_txt = Text(args_str[:100] + ("…" if len(args_str) > 100 else ""), style=DIM)
        inner.add_row(badge, args_txt)
        self.blocks.append(Text(""))
        self.blocks.append(Panel(inner, border_style=GOLD, padding=(0, 1)))

    def tool_result(self, ok: bool) -> None:
        mark = Text("  ✓ done", style="green") if ok else Text("  ✗ failed", style="bold red")
        self.blocks.append(mark)

    def error(self, msg: str) -> None:
        self.blocks.append(Text(""))
        self.blocks.append(Text(f"✘ {msg}", style="bold red"))

    def footer_stats(self, tool_calls: int, session_id: str) -> None:
        plural = "s" if tool_calls != 1 else ""
        self.blocks.append(Text(""))
        self.blocks.append(
            Text(f"  {tool_calls} tool call{plural} · session {session_id[:8]}", style=DIM)
        )

    def render(self) -> Group:
        return Group(*self.blocks)


def build_input_panel() -> Panel:
    """slt: ui.bordered(Rounded).row( '> ' | text_input ) — static frame; the
    live input happens on the real prompt line right below the frame."""
    body = Table.grid(padding=(0, 1))
    body.add_column()
    body.add_column(ratio=1)
    body.add_row(Text("❯", style=f"bold {GOLD}"), Text("Ask anything…", style=DIM))
    return Panel(body, border_style=ACCENT, padding=(0, 1))


def build_help_text() -> Text:
    """slt: ui.help_colored([('Enter','send'), ...])"""
    keys = [("Enter", "send"), ("Ctrl+C", "cancel"), ("/help", "commands"), ("/exit", "quit")]
    text = Text("")
    for i, (k, v) in enumerate(keys):
        if i:
            text.append("  ·  ", style=DIM)
        text.append(k, style=f"bold {ACCENT}")
        text.append(f" {v}", style=DIM)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Interactive loop
# ─────────────────────────────────────────────────────────────────────────────

async def run_interactive_tui(session_id: Optional[str] = None) -> None:
    cfg = load_config()

    history_file = get_ex_home() / "cli_history.txt"
    slash_commands = [f"/{c.name}" for c in commands_registry.list_commands()]
    completer = WordCompleter(slash_commands, ignore_case=True, match_middle=False)

    prompt_session = PromptSession(
        history=FileHistory(str(history_file)),
        completer=completer,
    )

    agent = EXAgent(config=cfg, session_id=session_id)
    ctx = {"agent": agent, "config": cfg}

    conversation = Conversation()
    live = Live(console=console, refresh_per_second=16, auto_refresh=False, transient=True)

    def repaint() -> None:
        live.update(
            Group(
                build_header(cfg.model, cfg.provider),
                Panel(conversation.render(), border_style=DIM, padding=(0, 1)),
                build_input_panel(),
                build_help_text(),
            )
        )
        live.refresh()

    repaint()

    while True:
        try:
            # Pause the persistent view while prompt_toolkit owns the terminal
            live.stop()
            user_input = await prompt_session.prompt_async("❯ ", multiline=False)
            user_input = user_input.strip()

            if not user_input:
                repaint()
                continue

            if user_input in ["/exit", "/quit", "exit", "quit"]:
                conversation.blocks.append(Text(""))
                conversation.blocks.append(Text("Session closed. Memory preserved.", style=DIM))
                repaint()
                break

            # Slash commands → run, show output in transcript card
            if user_input.startswith("/"):
                handled, output = commands_registry.handle(user_input, ctx)
                if handled:
                    conversation.user_prompt(user_input)
                    conversation.assistant_text(output)
                    repaint()
                    continue

            conversation.user_prompt(user_input)
            live.start()
            try:
                # ── Agent turn ────────────────────────────────────────
                accumulated_text = ""
                accumulated_thinking = ""
                thinking_shown = False

                def on_stream(kind: str, delta: str) -> None:
                    nonlocal accumulated_text, accumulated_thinking, thinking_shown
                    if kind == "thinking":
                        accumulated_thinking += delta
                        return
                    if kind == "content":
                        if accumulated_thinking and not thinking_shown:
                            head = accumulated_thinking.strip().splitlines()
                            first = head[0][:70] if head else ""
                            conversation.thought_hint(first)
                            thinking_shown = True
                        accumulated_text += delta
                        conversation.assistant_text(accumulated_text)
                        repaint()

                def on_tool_status(event: str, tool_name: str, data: dict) -> None:
                    if event == "invoking":
                        args_str = ""
                        try:
                            if isinstance(data.get("command"), str):
                                args_str = data["command"]
                            elif isinstance(data.get("path"), str):
                                args_str = data["path"]
                        except Exception:
                            pass
                        conversation.tool_card(tool_name, args_str)
                    elif event == "completed":
                        conversation.tool_result(bool(data.get("success")))
                    repaint()

                try:
                    res = await agent.run_conversation_async(
                        user_message=user_input,
                        stream_callback=on_stream,
                        tool_status_callback=on_tool_status,
                    )
                finally:
                    if not accumulated_text.strip():
                        # transient Live would otherwise swallow failures silently
                        conversation.error(
                            "no assistant output — provider error; run `ex setup` to test connection"
                        )

                if accumulated_text.strip():
                    conversation.assistant_text(accumulated_text)

                turns = res.get("tool_calls_count", 0)
                if turns:
                    conversation.footer_stats(turns, agent.session_id)
                repaint()
            finally:
                live.stop()

        except (KeyboardInterrupt, EOFError):
            console.print(Text("Session terminated by user.", style=DIM))
            break
        except Exception as e:
            console.print(f"[bold red]✘ Session Error:[/bold red] {e}")
            continue


def main():
    asyncio.run(run_interactive_tui())


if __name__ == "__main__":
    main()