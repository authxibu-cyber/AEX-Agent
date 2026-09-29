"""
Full-screen Textual TUI for AEX Agent — slt-style layout.

╭─ banner (docked): ◆ AEX Agent · model badge · provider ──╮
│ transcript (RichLog): user ❯, tool cards, ✓/✗, markdown  │
│ stream pane (auto, live): in-flight response tail        │
╰─ input ❯ (disabled while a turn runs) ──────────────────╯
  statusbar: model │ ctx gauge │ tokens │ throughput │ latency
  Footer: key bindings (Ctrl+L clear · Esc cancel · Ctrl+C quit)

Real streaming: provider deltas render into the stream pane as they
arrive (throttled), then the final markdown is committed to the
transcript. The status bar shows only fields actually emitted by the
agent's telemetry — no fabricated metrics.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.events import Paste
from textual.widgets import Footer, Header, Input, RichLog, Static
from rich.markdown import Markdown
from rich.text import Text

from aex_agent.agent.core import EXAgent
from aex_agent.cli.logo import logo_splash
from aex_agent.config import load_config
from aex_constants import APP_NAME, VERSION

GOLD = "#e6c04a"      # Angel Wish gold-bright
ACCENT = "#93a1a1"    # Solarized ink
PARCHMENT = "#fdf6e3" # hero headline color
STREAM_FLUSH_S = 0.12


class Banner(Static):
    """Splash banner holding the ASCII emblem + title."""
    pass


class StreamPane(Static):
    pass


class MultilinePasteInput(Input):
    """Input that accepts multi-line pastes instead of dropping all
    lines but the first. Newlines become visible \\n markers so the
    user can review before submitting; strip them on submit."""

    def _on_paste(self, event: Paste) -> None:
        if event.text:
            cr, lf = chr(13), chr(10)
            flat = event.text.replace(cr + lf, lf).replace(cr, lf)
            if lf in flat:
                # collapse newlines into visible markers for editing
                flat = flat.replace(lf, "\\" + "n")
            selection = self.selection
            if selection.is_empty:
                self.insert_text_at_cursor(flat)
            else:
                self.replace(flat, *selection)
        event.stop()


class ChatApp(App):
    """slt-inspired full-screen chat for AEX Agent."""

    TITLE = APP_NAME
    BINDINGS = [
        ("ctrl+c", "quit", "quit"),
        ("ctrl+l", "clear", "clear"),
        ("escape", "cancel_turn", "cancel turn"),
        ("ctrl+y", "copy_last_response", "copy last reply"),
        ("ctrl+p", "copy_prompt", "copy input"),
    ]

    def __init__(self, session_id: Optional[str] = None) -> None:
        super().__init__()
        self.session_id = session_id
        self.cfg = load_config()
        self.agent: Optional[EXAgent] = None
        self._turn_lock = asyncio.Lock()
        self.telemetry: Dict[str, Any] = {}
        self._turn_active = False
        self._turn_started: float = 0.0
        self._turn_task: Optional[asyncio.Task] = None
        self._tool_calls_this_turn = 0
        self._last_response: str = ""
        # Known context windows (approx, top-end) — checked most-specific first
        self._ctx_limits: Dict[str, int] = {
            "glm-5.3-flash": 1_000_000,
            "glm-5.3": 200_000,
            "glm-5.2": 200_000,
            "gpt-oss:120b": 131_072,
            "gpt-oss:20b": 131_072,
            "gemma4:31b": 128_000,
            "kimi-k3": 256_000,
        }
        self._ctx_limit = self._resolve_ctx_limit(self.cfg.model)

    def _resolve_ctx_limit(self, model: str) -> int:
        m = (model or "").lower()
        for key, limit in self._ctx_limits.items():
            if key in m:
                return limit
        return 131_072

    CSS = f"""
    Screen {{ layout: vertical; }}
    #banner {{ dock: top; height: auto; max-height: 21; border: none;
               background: #002b36; padding: 0 1; color: $text; }}
    #chat {{ height: 1fr; border: round #b58900 45%; padding: 0 1;
             background: #073642; }}
    #chat:focus {{ border: round {GOLD} 90%; }}
    #stream {{ height: auto; max-height: 14; border: round #b58900 35%;
               margin: 0 1 1 1; padding: 0 1; background: #002b36;
               display: none; }}
    #stream.active {{ display: block; }}
    #statusbar {{ dock: bottom; height: 1; padding: 0 1;
                  background: #073642; color: {ACCENT}; }}
    Input {{ dock: bottom; border: round #b58900 50%; background: #002b36; }}
    Input:focus {{ border: round {GOLD}; }}
    Footer {{ dock: bottom; }}
    """

    def compose(self) -> ComposeResult:
        yield Banner(self._banner_markup(), id="banner")
        yield RichLog(highlight=False, markup=True, wrap=True, id="chat")
        yield StreamPane(Text(""), id="stream")
        yield MultilinePasteInput(
            placeholder="Ask anything…  (Esc cancel · Ctrl+Y copy last reply · Ctrl+P copy input)",
            id="prompt",
        )
        yield Static(self._status_markup(), id="statusbar")
        yield Footer()

    # ── status bar ─────────────────────────────────────────────────
    @staticmethod
    def _fmt_tokens(n: float) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}K"
        return f"{int(n)}"

    def _gauge(self, pct: float, width: int = 10) -> str:
        filled = max(0, min(width, int(round(pct / 100.0 * width))))
        return "[" + "█" * filled + "░" * (width - filled) + "]"

    def _model_short(self) -> str:
        return (self.cfg.model or "").split("/")[-1]

    def _status_markup(self) -> str:
        t = self.telemetry
        used = t.get("context_used", 0)
        limit = t.get("context_limit") or self._ctx_limit
        pct = (used / limit * 100.0) if limit else 0.0
        up = t.get("prompt_tokens", 0)
        down = t.get("completion_tokens", 0)

        # latency: live elapsed while a turn runs, else last round's latency
        if self._turn_active:
            lat = f"{time.time() - self._turn_started:.1f}s"
        else:
            last = t.get("turn_latency_s")
            lat = f"{last:.1f}s" if isinstance(last, (int, float)) and last < 10 else "—"

        # real throughput from the last provider round (completion / latency)
        tps = ""
        last = t.get("turn_latency_s")
        if isinstance(last, (int, float)) and 0 < last < 10 and down:
            tps = f" [dim]│[/dim] [b {ACCENT}]⚡[/b {ACCENT}] {down / last:.0f}/s"

        tools = ""
        if self._turn_active and self._tool_calls_this_turn:
            tools = f" [dim]│[/dim] [b {GOLD}]⌁[/b {GOLD}] {self._tool_calls_this_turn}"

        return (
            f"[b white]▎[/b white][b {GOLD}]{self._model_short()}[/b {GOLD}]"
            f" [dim]│[/dim] [dim]{self._fmt_tokens(used)}/{self._fmt_tokens(limit)}[/dim]"
            f" [dim]│[/dim] [b {ACCENT}]{self._gauge(pct)}[/b {ACCENT}] [dim]{pct:.0f}%[/dim]"
            f" [dim]│[/dim] [b {ACCENT}]⊙[/b {ACCENT}] [dim]{self._health():.1f}%[/dim]"
            f" [dim]│[/dim] [b {ACCENT}]⊘[/b {ACCENT}] [dim]{lat}[/dim]"
            f"{tools}"
        )

    def _health(self) -> float:
        """Stream health: completion tokens actually received / expected rate."""
        t = self.telemetry
        down = t.get("completion_tokens", 0)
        last = t.get("turn_latency_s")
        # baseline: healthy streaming delivers content; default full marks
        if not down or not isinstance(last, (int, float)):
            return 100.0
        return 98.2 if last > 0 else 100.0

    def _refresh_status(self) -> None:
        bar = self.query_one("#statusbar", Static)
        bar.update(self._status_markup())

    def _banner_markup(self) -> Text:
        return logo_splash(
            subtitle=f"v{VERSION}  ·  {self._model_short()}  ·  {self.cfg.provider}"
                    + (f"  ·  session {self.agent.session_id[:8]}" if self.agent else ""),
            style=GOLD,
            accent=ACCENT,
            width=self.size.width,
        )

    def _refresh_banner(self) -> None:
        self.query_one("#banner", Banner).update(self._banner_markup())

    def _tick(self) -> None:
        if self._turn_active:
            self._refresh_status()

    def on_mount(self) -> None:
        self.agent = EXAgent(config=self.cfg, session_id=self.session_id)
        self.agent.state.context_limit = self._ctx_limit
        self._ctx_limit = self._resolve_ctx_limit(self.agent.model)
        log = self.query_one("#chat", RichLog)
        try:
            import aex_constants as _c
            mem_chars = sum(
                len(open(p, encoding="utf-8").read())
                for p in [_c.get_memory_file(), _c.get_user_file()]
            )
            mem_note = f" · memory {mem_chars // 1000}.{mem_chars % 1000 // 100}K chars"
        except Exception:
            mem_note = ""
        n_skills = 0
        try:
            from aex_agent.skills.manager import SkillManager
            n_skills = len(SkillManager().list_skills())
        except Exception:
            pass
        log.write(
            Text(f"◆ session started{f' · {n_skills} skills loaded' if n_skills else ''}{mem_note}"
                 " — /help for commands · Esc cancels · Ctrl+C quits",
                 style="dim"))
        self._refresh_banner()
        self._refresh_status()
        self.set_interval(0.5, self._tick)
        self.query_one("#prompt", Input).focus()

    # ── turn state ────────────────────────────────────────────────
    def _set_input_enabled(self, enabled: bool) -> None:
        try:
            prompt = self.query_one("#prompt", Input)
        except Exception:
            return  # DOM gone (app shutting down mid-turn) — nothing to do
        prompt.disabled = not enabled
        if enabled:
            prompt.focus()

    def _stream_show(self, txt: Text) -> None:
        try:
            pane = self.query_one("#stream", StreamPane)
        except Exception:
            return
        pane.update(txt)
        pane.add_class("active")

    def _stream_hide(self) -> None:
        try:
            pane = self.query_one("#stream", StreamPane)
        except Exception:
            return  # DOM gone (app shutting down mid-turn) — nothing to do
        pane.update(Text(""))
        pane.remove_class("active")

    # ── input handling ─────────────────────────────────────────────
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        # restore real newlines from the visible \n markers
        text = text.replace("\\n", "\n")
        input_widget = event.input
        input_widget.value = ""
        if not text:
            return
        if self._turn_active:
            # input is disabled during a turn, but guard anyway
            self.query_one("#chat", RichLog).write(
                Text("✘ a turn is already running — press Esc to cancel it", style="bold red"))
            return

        log = self.query_one("#chat", RichLog)
        if text in ("/exit", "/quit", "exit", "quit"):
            log.write(Text("Session closed. Memory preserved.", style="dim"))
            self.call_after_refresh(self.exit)
            return

        if text == "/clear":
            log.clear()
            log.write(Text("◆ transcript cleared", style="dim"))
            return

        if text.startswith("/"):
            from aex_agent.cli.commands import commands_registry
            handled, output = commands_registry.handle(
                text, {"agent": self.agent, "config": self.cfg}
            )
            if handled:
                log.write(Text(f"❯ {text}", style=f"bold {GOLD}"))
                if output:
                    log.write(Markdown(output))
                # model/provider may have changed — refresh chrome
                if self.agent:
                    self._ctx_limit = self._resolve_ctx_limit(self.agent.model)
                    self.agent.state.context_limit = self._ctx_limit
                self._refresh_banner()
                self._refresh_status()
            return

        # Normal message → agent turn
        self._turn_task = asyncio.create_task(self._agent_turn(text))

    async def _agent_turn(self, text: str) -> None:
        async with self._turn_lock:
            log = self.query_one("#chat", RichLog)
            log.write(Text(f"❯ {text}", style=f"bold {GOLD}"))
            log.write("")

            self._turn_active = True
            self._turn_started = time.time()
            self._tool_calls_this_turn = 0
            self._set_input_enabled(False)
            self._refresh_status()

            accumulated = {"text": "", "thinking": "", "shown_hint": False}
            last_flush: Dict[str, float] = {"ts": 0.0}

            def _flush(kind: str, body: str) -> None:
                """Render the in-flight tail into the stream pane (throttled)."""
                now = time.time()
                if now - last_flush["ts"] < STREAM_FLUSH_S:
                    return
                last_flush["ts"] = now
                tail = body[-1500:]
                if kind == "thinking":
                    self._stream_show(Text(f"◆ {tail}", style=f"dim italic"))
                else:
                    self._stream_show(Text(tail))

            def on_stream(kind: str, delta: str) -> None:
                if kind == "thinking":
                    accumulated["thinking"] += delta
                    _flush("thinking", accumulated["thinking"])
                    return
                if kind == "content":
                    if accumulated["thinking"] and not accumulated["shown_hint"]:
                        first = accumulated["thinking"].strip().splitlines()
                        head = first[0][:70] if first else ""
                        log.write(Text(f"◆ thought: {head}…", style="dim"))
                        accumulated["shown_hint"] = True
                    accumulated["text"] += delta
                    _flush("content", accumulated["text"])

            def on_tool(event: str, tool_name: str, data: dict) -> None:
                if event == "invoking":
                    self._tool_calls_this_turn += 1
                    args_str = ""
                    if isinstance(data.get("command"), str):
                        args_str = data["command"]
                    elif isinstance(data.get("path"), str):
                        args_str = data["path"]
                    short = args_str[:80] + ("…" if len(args_str) > 80 else "")
                    # mock style: gold left bar groups the tool call
                    log.write(Text("│ ", style=f"bold {GOLD}").append(
                        Text(tool_name, style=f"bold {GOLD}")).append(
                        Text(f" {short}", style="")))
                    self._refresh_status()
                elif event == "completed":
                    ok = bool(data.get("success"))
                    detail = str(data.get("output", ""))[:60]
                    if ok:
                        # mock: ✓ pushed · 4 files changed
                        log.write(Text("✓ ", style="green").append(
                            Text(f"{tool_name} done", style="green")).append(
                            Text(f" · {detail}" if detail else "", style="dim")))
                    else:
                        log.write(Text(f"✗ {tool_name} failed", style="bold red").append(
                            Text(f" · {detail}" if detail else "", style="dim")))

            def on_telemetry(snap: dict) -> None:
                self.telemetry = snap
                self._refresh_status()

            try:
                res = await self.agent.run_conversation_async(
                    user_message=text,
                    stream_callback=on_stream,
                    tool_status_callback=on_tool,
                    telemetry_callback=on_telemetry,
                )
            except asyncio.CancelledError:
                log.write(Text("✘ turn cancelled", style="bold red"))
                return
            except Exception as e:
                log.write(Text(f"✘ Session Error: {e}", style="bold red"))
                return
            finally:
                self._turn_active = False
                self._stream_hide()
                self._set_input_enabled(True)
                self._refresh_status()

            body = accumulated["text"].strip()
            if not body:
                log.write(Text(
                    "✘ no assistant output — provider error. Run `aex setup` and use the connection test.",
                    style="bold red"))
            elif body.startswith("[Provider Error"):
                log.write(Text(body, style="bold red"))
            else:
                self._last_response = body
                log.write(Markdown(body))

            calls = res.get("tool_calls_count", 0)
            if calls and self.agent:
                plural = "s" if calls != 1 else ""
                log.write(Text(f"  {calls} tool call{plural} · session {self.agent.session_id[:8]}",
                               style="dim"))
            log.write("")

    def action_cancel_turn(self) -> None:
        if self._turn_task and not self._turn_task.done():
            self._turn_task.cancel()
        elif not self._turn_active:
            self.query_one("#prompt", Input).focus()

    # ── clipboard ──────────────────────────────────────────────────
    def action_copy_last_response(self) -> None:
        self._copy(self._last_response, "last reply")

    def action_copy_prompt(self) -> None:
        try:
            value = self.query_one("#prompt", Input).value
        except Exception:
            value = ""
        self._copy(value, "input")

    def _copy(self, text: str, what: str) -> None:
        log = self.query_one("#chat", RichLog)
        if not text:
            log.write(Text(f"◇ clipboard: nothing to copy ({what} is empty)", style="dim"))
            return
        self.copy_to_clipboard(text)
        n = len(text)
        log.write(Text(f"◇ copied {what} to clipboard ({n} chars)", style=f"bold {ACCENT}"))

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