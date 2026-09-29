"""
Textual TUI pilot test — drives the real ChatApp headless via textual's
run_test pilot. Guards the streaming rewrite: stream pane visibility,
input locking during turns, transcript commit, telemetry status bar,
slash-command handling, and /clear.

The fake agent turn is gated on an asyncio.Event so mid-turn assertions
are deterministic (no timing races): the test observes the running turn,
then releases it.
"""
import asyncio
import pytest

pytest.importorskip("textual.app")

from aex_agent.agent.core import EXAgent
from aex_agent.cli.textual_tui import ChatApp
from textual.widgets import Input, RichLog, Static


@pytest.fixture
def fake_agent_turn(monkeypatch):
    gate = asyncio.Event()

    async def fake_turn(self, user_message, **kwargs):
        stream = kwargs.get("stream_callback")
        tool = kwargs.get("tool_status_callback")
        tel = kwargs.get("telemetry_callback")
        if stream:
            stream("thinking", "Analyzing request carefully")
            # let the thinking tail flush before content starts streaming
            await asyncio.sleep(0.2)
            stream("content", "Hello ")
            # hold mid-stream until the test releases the gate
            await gate.wait()
            stream("content", "**world** from AEX")
        if tool:
            tool("invoking", "terminal", {"command": "echo hi"})
            tool("completed", "terminal", {"success": True})
        if tel:
            tel({
                "model": self.model, "provider": "test", "prompt_tokens": 120,
                "completion_tokens": 3, "total_tokens": 123, "context_used": 120,
                "context_limit": 200000, "context_pct": 0.06,
                "turn_latency_s": 0.15, "turn_count": 1,
            })
        return {
            "session_id": self.session_id,
            "response": "Hello **world** from AEX",
            "reasoning": "",
            "tool_calls_count": 1,
            "messages": [],
            "usage": {},
            "turn_latency_s": 0.2,
        }

    monkeypatch.setattr(EXAgent, "run_conversation_async", fake_turn)
    return gate


def _transcript(app) -> str:
    log = app.query_one("#chat", RichLog)
    return "\n".join(strip.text for strip in log.lines)


async def _await_turn_done(pilot, app, timeout_s: float = 5.0) -> None:
    for _ in range(int(timeout_s / 0.05)):
        await pilot.pause(0.05)
        if not app._turn_active:
            return
    raise AssertionError("turn did not finish in time")


@pytest.mark.asyncio
async def test_textual_tui_full_turn(fake_agent_turn):
    app = ChatApp()
    async with app.run_test(size=(110, 32)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", Input)

        # initial state: input enabled, status bar renders model glyph
        assert not prompt.disabled
        assert "☤" in app._status_markup()

        # submit a turn — fake turn holds mid-stream on the gate
        prompt.value = "test streaming please"
        await pilot.press("enter")
        for _ in range(60):
            await pilot.pause(0.05)
            if app._turn_active:
                break
        assert app._turn_active, "turn never started"

        # during the turn: input locked, stream pane active with in-flight text
        assert prompt.disabled, "input must be disabled during a turn"
        pane = app.query_one("#stream", Static)
        assert "active" in pane.classes, "stream pane should be visible"
        # throttle window (0.12s) must have passed so the content tail flushed
        for _ in range(20):
            await pilot.pause(0.05)
            if "Hello" in str(pane.render()):
                break
        assert "Hello" in str(pane.render()), "stream pane should show in-flight text"

        # release the gate; turn finishes
        fake_agent_turn.set()
        await _await_turn_done(pilot, app)
        await pilot.pause(0.1)

        # post-turn: input unlocked, stream pane hidden, transcript committed
        assert not prompt.disabled
        assert "active" not in pane.classes
        text = _transcript(app)
        assert "❯ test streaming please" in text
        assert "thought" in text
        assert "▐ terminal" in text
        assert "✓ terminal done" in text
        assert "world" in text
        assert "1 tool call" in text

        # telemetry-driven status bar content
        assert "200.0K" in app._status_markup()


@pytest.mark.asyncio
async def test_textual_tui_slash_commands(fake_agent_turn):
    app = ChatApp()
    async with app.run_test(size=(110, 32)) as pilot:
        await pilot.pause()
        prompt = app.query_one("#prompt", Input)

        # /model with no args → prints state, refreshes banner, starts no turn
        prompt.value = "/model"
        await pilot.press("enter")
        await pilot.pause(0.2)
        assert "Active model" in _transcript(app)
        assert not app._turn_active

        # /clear empties the transcript
        prompt.value = "/clear"
        await pilot.press("enter")
        await pilot.pause(0.1)
        assert _transcript(app) == "" or "cleared" in _transcript(app)