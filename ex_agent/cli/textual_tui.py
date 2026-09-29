"""
Full-screen Textual TUI for EX Agent — slt-style layout.

╭─ header: ◆ EX Agent · model badge · provider (docked) ─╮
│ transcript (scrollable): user prompts (gold ❯),       │
│   streaming assistant markdown, tool cards + badges,  │
│   ✓/✗ results, errors                                  │
│                                                        │
╰─ input: ❯ Ask anything… (docked, focus) ──────────────╯
  key hints (docked footer)

The agent turn runs as an asyncio task; provider streaming deltas
arrive via thread-safe post_message from the agent's callbacks.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from ex_agent.agent.core import EXAgent
from ex_agent.config import load_config
from ex_constants import APP_NAME, VERSION

GOLD = "gold1"
ACCENT = "cyan"


class Banner(Static):
    pass


class ChatApp(App):
    """slt-inspired full-screen chat for EX Agent."""

    TITLE = APP_NAME
    BINDINGS = [
        ("ctrl+c", "quit", "quit"),
        ("ctrl+l", "clear", "clear"),
    ]

    def __init__(self, session_id: Optional[str] = None) -> None:
        super().__init__()
        self.session_id = session_id
        cfg = load_config()
        self.cfg = cfg
        self.agent: Optional[EXAgent] = None
        self._turn_lock = asyncio.Lock()

    CSS = """
    Screen { layout: vertical; }
    #banner { dock: top; height: 3; border: round $accent; padding: 0 1;
              background: $surface; color: $text; }
    #banner-line1 { color: $text; }
    #chat { border: round $accent-muted; margin: 0 0; height: 1fr; }
    #chat:focus { border: round $accent; }
    Input { dock: bottom; border: round $accent; }
    Footer { dock: bottom; }
    """

    def compose(self) -> ComposeResult:
        yield Banner(self._banner_markup(), id="banner")
        yield RichLog(highlight=False, markup=True, wrap=True, id="chat")
        yield Input(placeholder="Ask anything…", id="prompt")
        yield Footer()

    def _banner_markup(self) -> str:
        return (
            f"[b {ACCENT}]◆[/b {ACCENT}] [b]{APP_NAME}[/b] [dim]v{VERSION}[/dim]   "
            f"[b {GOLD}]{self.cfg.model}[/b {GOLD}]   "
            f"[dim]{self.cfg.provider}[/dim]"
        )

    def on_mount(self) -> None:
        self.agent = EXAgent(config=self.cfg, session_id=self.session_id)
        log = self.query_one("#chat", RichLog)
        log.write("[dim]◆ session started — type a message, /help for commands, Ctrl+C to quit[/dim]")
        self.query_one("#prompt", Input).focus()

    # ── input handling ──────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        input_widget = event.input
        input_widget.value = ""
        if not text:
            return
        log = self.query_one("#chat", RichLog)
        if text in ("/exit", "/quit", "exit", "quit"):
            log.write("[dim]Session closed. Memory preserved.[/dim]")
            self.call_after_refresh(self.exit)
            return
        if text.startswith("/"):
            from ex_agent.cli.commands import commands_registry
            handled, output = commands_registry.handle(
                text, {"agent": self.agent, "config": self.cfg}
            )
            if handled:
                log.write(f"[b {GOLD}]❯[/b {GOLD}] [b]{text}[/b]")
                log.write(f"[dim]{output}[/dim]")
            return
        # Normal message → agent turn
        asyncio.create_task(self._agent_turn(text))

    async def _agent_turn(self, text: str) -> None:
        if self._turn_lock.locked():
            self.query_one("#chat", RichLog).write(
                "[red]✘ a turn is already running — wait for it to finish[/red]"
            )
            return
        async with self._turn_lock:
            log = self.query_one("#chat", RichLog)
            log.write(f"[b {GOLD}]❯[/b {GOLD}] [b]{text}[/b]")
            log.write("")

            accumulated = {"text": "", "thinking": "", "shown_hint": False}

            def on_stream(kind: str, delta: str) -> None:
                if kind == "thinking":
                    accumulated["thinking"] += delta
                    return
                if kind == "content":
                    if accumulated["thinking"] and not accumulated["shown_hint"]:
                        first = accumulated["thinking"].strip().splitlines()
                        head = first[0][:70] if first else ""
                        log.write(f"[dim]◆ thought: {head}…[/dim]")
                        accumulated["shown_hint"] = True
                    accumulated["text"] += delta

            def on_tool(event: str, tool_name: str, data: dict) -> None:
                if event == "invoking":
                    args_str = ""
                    try:
                        if isinstance(data.get("command"), str):
                            args_str = data["command"]
                        elif isinstance(data.get("path"), str):
                            args_str = data["path"]
                    except Exception:
                        pass
                    short = args_str[:80] + ("…" if len(args_str) > 80 else "")
                    log.write(f"[b {GOLD}]▐[/b {GOLD}] [b]{tool_name}[/b] [dim]{short}[/dim]")
                elif event == "completed":
                    ok = bool(data.get("success"))
                    log.write(f"[green]  ✓ done[/green]" if ok else f"[red]  ✗ failed[/red]")

            try:
                res = await self.agent.run_conversation_async(
                    user_message=text,
                    stream_callback=on_stream,
                    tool_status_callback=on_tool,
                )
            except Exception as e:
                log.write(f"[b red]✘ Session Error: {e}[/b red]")
                return

            body = accumulated["text"].strip()
            if not body:
                log.write(
                    "[b red]✘ no assistant output — provider error. "
                    "Run `ex setup` and use the connection test.[/b red]"
                )
            elif body.startswith("[Provider Error"):
                log.write(f"[b red]{body}[/b red]")
            else:
                # render final markdown via rich inside the log
                from rich.markdown import Markdown
                log.write(Markdown(body))
            calls = res.get("tool_calls_count", 0)
            if calls:
                plural = "s" if calls != 1 else ""
                log.write(
                    f"[dim]  {calls} tool call{plural} · session {self.agent.session_id[:8]}[/dim]"
                )
            log.write("")

    def action_clear(self) -> None:
        self.query_one("#chat", RichLog).clear()


def run_interactive_tui(session_id: Optional[str] = None) -> None:
    ChatApp(session_id=session_id).run()


def run_interactive_tui_async(session_id: Optional[str] = None) -> None:
    run_interactive_tui(session_id)


def main() -> None:
    run_interactive_tui()


if __name__ == "__main__":
    main()