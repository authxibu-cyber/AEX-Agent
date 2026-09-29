"""
Core EXAgent Architecture (Matching Nous Research Hermes Agent AIAgent).
Orchestrates the conversation loop, streaming token emission, resilient tool dispatch,
closed learning memory nudges, and trajectory recording.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional
import uuid

from aex_agent.agent.parser import ToolParser
from aex_agent.agent.selective_pulse import CognitivePulseGate
from aex_agent.agent.state import SessionState
from aex_agent.agent.trajectory import TrajectoryLogger
from aex_agent.config import Config, load_config
from aex_agent.memory.context import ContextEngine
from aex_agent.memory.persistent import MemoryManager
from aex_agent.memory.store import SessionStore
from aex_agent.providers.anthropic_provider import AnthropicProvider
from aex_agent.providers.base import BaseProvider, StreamChunk
from aex_agent.providers.local_provider import LocalProvider
from aex_agent.providers.openai_provider import OpenAICompatibleProvider
from aex_agent.skills.manager import SkillManager
from aex_agent.tools.base import ToolRegistry, registry
from aex_agent.tools.executor import ToolExecutor
from aex_agent.tools.toolsets import resolve_tool_names

logger = logging.getLogger("aex_agent.agent")


class EXAgent:
    def __init__(
        self,
        config: Optional[Config] = None,
        model: Optional[str] = None,
        provider_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        enabled_toolsets: Optional[List[str]] = None,
        system_instructions: Optional[str] = None,
        session_id: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.config = config or load_config()
        self.model = model or self.config.model
        self.provider_name = (provider_name or self.config.provider).lower()
        self.base_url = base_url or self.config.resolve_base_url()
        self.api_key = api_key or self.config.resolve_api_key()
        self.enabled_toolsets = enabled_toolsets or self.config.enabled_toolsets
        self.system_instructions = system_instructions or ""

        self.memory_manager = MemoryManager()
        self.session_store = SessionStore()
        self.context_engine = ContextEngine(memory_manager=self.memory_manager)
        self.skill_manager = SkillManager()
        self.trajectory_logger = TrajectoryLogger()
        self.pulse_gate = CognitivePulseGate()

        # Tools & Execution Engine
        self.tool_registry = tool_registry or registry
        self.tool_executor = ToolExecutor(
            tool_registry=self.tool_registry,
            approval_mode=self.config.approval_mode,
        )

        # Active Session
        self.session_id = session_id or str(uuid.uuid4())
        self.state = SessionState(session_id=self.session_id)
        self.session_store.create_or_update_session(self.session_id, title="AEX Agent Session")

        # Provider initialization
        self.provider = self._init_provider()

    def _init_provider(self) -> BaseProvider:
        p_name = self.provider_name
        if p_name in ["anthropic", "claude"]:
            return AnthropicProvider(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                thinking_budget=self.config.thinking_budget,
            )
        elif p_name in ["ollama", "vllm", "local"]:
            return LocalProvider(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                thinking_budget=self.config.thinking_budget,
            )
        else:
            return OpenAICompatibleProvider(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                thinking_budget=self.config.thinking_budget,
            )

    def assemble_system_message(self, user_message: Optional[str] = None) -> str:
        skills_summary = self.skill_manager.format_skills_summary()
        active_skill_protocols = ""
        self.active_skill_names: List[str] = []
        if user_message:
            matched = self.skill_manager.match_skills(user_message)
            if matched:
                self.active_skill_names = [s.name for s in matched]
                blocks = [
                    f"### Skill: {s.name} ({'user' if s.is_user_skill else 'bundled'})\n{s.instructions.strip()}"
                    for s in matched
                ]
                active_skill_protocols = "\n\n".join(blocks)
        return self.context_engine.assemble_system_prompt(
            skills_summary=skills_summary,
            extra_instructions=self.system_instructions,
            active_skill_protocols=active_skill_protocols,
        )

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        active_names = resolve_tool_names(self.enabled_toolsets)
        schemas = []
        for t in self.tool_registry.list_tools():
            if t.name in active_names:
                schemas.append(t.schema)
        return schemas

    async def run_conversation_async(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        stream_callback: Optional[Callable[[str, str], None]] = None,
        tool_status_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        telemetry_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_iterations: int = 20,
    ) -> Dict[str, Any]:
        """
        Core Agentic Loop:
        1. Persists user turn
        2. Streams response and handles tool calls in iterative cycles
        3. Executes tool calls concurrently
        4. Applies self-improving memory learning check
        5. Logs trajectory

        telemetry_callback receives a live snapshot dict after each provider
        round: {prompt_tokens, completion_tokens, total_tokens, context_limit,
        context_pct, turn_latency_s, model, provider}
        """
        # Record user message in SQLite & active memory
        self.state.append_message("user", user_message)
        self.session_store.add_message(self.session_id, "user", user_message)

        # Assemble full message chain (skill protocols activate on user-message triggers)
        system_content = self.assemble_system_message(user_message=user_message)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_content}]

        # Append previous history if supplied
        if conversation_history:
            for h in conversation_history:
                if h.get("role") != "system":
                    messages.append(h)
        else:
            # Load stored messages
            stored = self.session_store.get_messages(self.session_id, limit=50)
            for m in stored:
                messages.append({"role": m["role"], "content": m["content"]})

        iteration = 0
        final_assistant_content = ""
        total_reasoning = ""
        tool_calls_executed = 0
        turn_started = time.time()

        def _emit_telemetry(turn_latency: Optional[float] = None) -> None:
            if telemetry_callback is None:
                return
            limit = self.state.context_limit or 0
            ctx = self.state.prompt_tokens  # last-round prompt size ≈ context in flight
            snapshot = {
                "model": self.model,
                "provider": self.provider_name,
                "prompt_tokens": self.state.prompt_tokens,
                "completion_tokens": self.state.completion_tokens,
                "total_tokens": self.state.total_tokens,
                "context_used": ctx,
                "context_limit": limit,
                "context_pct": (ctx / limit * 100.0) if limit else 0.0,
                "turn_latency_s": turn_latency if turn_latency is not None else (time.time() - turn_started),
                "turn_count": self.state.turn_count,
            }
            try:
                telemetry_callback(snapshot)
            except Exception:
                pass

        while iteration < max_iterations:
            iteration += 1
            round_started = time.time()
            tool_schemas = self.get_tool_schemas()

            accumulated_content = ""
            accumulated_thinking = ""
            raw_tool_calls: List[Dict[str, Any]] = []

            # Stream response from provider
            async for chunk in self.provider.chat_stream(messages, tools=tool_schemas):
                if chunk.usage:
                    self.state.record_usage(chunk.usage)
                if chunk.content:
                    accumulated_content += chunk.content
                    if stream_callback:
                        stream_callback("content", chunk.content)

                if chunk.thinking:
                    accumulated_thinking += chunk.thinking
                    if stream_callback:
                        stream_callback("thinking", chunk.thinking)

                if chunk.tool_calls:
                    raw_tool_calls = chunk.tool_calls

            self.state.turn_count += 1
            _emit_telemetry(turn_latency=time.time() - round_started)

            # Extract thought blocks from content if embedded in text (<thought>...</thought>)
            clean_content, inline_thought = ToolParser.extract_thought(accumulated_content)
            if inline_thought:
                accumulated_thinking += f"\n{inline_thought}".strip()

            # Resiliently parse tool calls (both native OpenAI and Hermes <tool_call> tags)
            parsed_calls, clean_text = ToolParser.parse_tool_calls(raw_tool_calls, clean_content)
            final_assistant_content = clean_text

            if accumulated_thinking:
                total_reasoning += accumulated_thinking + "\n"

            # Check if model invoked tools
            if not parsed_calls:
                # Turn finished without further tool calls
                self.state.append_message("assistant", final_assistant_content)
                self.session_store.add_message(self.session_id, "assistant", final_assistant_content)
                break

            # Append the assistant's message with tool calls to prompt history
            assistant_turn = {
                "role": "assistant",
                "content": final_assistant_content or None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])},
                    }
                    for c in parsed_calls
                ],
            }
            messages.append(assistant_turn)
            self.state.append_message(
                "assistant",
                final_assistant_content,
                tool_calls=assistant_turn["tool_calls"],
            )

            # Inform callback of tool calls
            for call in parsed_calls:
                tool_calls_executed += 1
                if tool_status_callback:
                    tool_status_callback("invoking", call["name"], call["arguments"])

            # Execute tool calls in parallel (Tier-3 async execution pool)
            results = await self.tool_executor.execute_parallel(parsed_calls)

            # Append tool outputs to messages array
            for res_item in results:
                call_id = res_item["id"]
                tool_name = res_item["name"]
                t_result = res_item["result"]
                result_str = t_result.to_string()

                if tool_status_callback:
                    tool_status_callback("completed", tool_name, {"output": result_str, "success": t_result.success})

                tool_message = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": tool_name,
                    "content": result_str,
                }
                messages.append(tool_message)
                self.state.append_message("tool", result_str, tool_call_id=call_id, name=tool_name)
                self.session_store.add_message(self.session_id, "tool", result_str, author=tool_name)

        # Self-Improving Learning Loop: Proactive Memory Nudge
        if tool_calls_executed >= 2:
            self._evaluate_memory_persisting(final_assistant_content)

        # Export Trajectory (ShareGPT / Hermes-RL format)
        if self.config.save_trajectories:
            try:
                self.trajectory_logger.export_sharegpt(
                    self.session_id,
                    self.state.messages,
                    model_name=self.model,
                )
            except Exception:
                pass

        return {
            "session_id": self.session_id,
            "response": final_assistant_content,
            "reasoning": total_reasoning.strip(),
            "tool_calls_count": tool_calls_executed,
            "messages": self.state.messages,
            "usage": {
                "prompt_tokens": self.state.prompt_tokens,
                "completion_tokens": self.state.completion_tokens,
                "total_tokens": self.state.total_tokens,
                "context_limit": self.state.context_limit,
            },
            "turn_latency_s": time.time() - turn_started,
        }

    def _evaluate_memory_persisting(self, assistant_response: str) -> None:
        """
        Nudges persistent storage when high-salience knowledge or configurations are established.
        """
        salience_keywords = ["configured", "installed", "fixed bug", "created skill", "solution:"]
        if any(kw in assistant_response.lower() for kw in salience_keywords):
            # Extract first sentence or key finding for memory
            first_summary = assistant_response.splitlines()[0][:180]
            self.memory_manager.update_memory(f"Completed task: {first_summary}")

    def run_conversation(self, user_message: str, **kwargs) -> Dict[str, Any]:
        """Synchronous wrapper around run_conversation_async."""
        return asyncio.run(self.run_conversation_async(user_message, **kwargs))


def main():
    """CLI entrypoint alias for aex-agent."""
    from aex_agent.cli.main import main as cli_main
    cli_main()
