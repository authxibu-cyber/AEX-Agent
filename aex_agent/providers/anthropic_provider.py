"""
Anthropic Provider for AEX Agent.
Streams Claude responses, thinking tokens, and tool use blocks via SSE.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from aex_agent.providers.base import BaseProvider, StreamChunk


class AnthropicProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_budget: int = 0,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://api.anthropic.com/v1",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_budget=thinking_budget,
        )

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        url = f"{self.base_url.rstrip('/')}/messages"
        headers = {
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Separate system message if present
        system_text = ""
        filtered_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_text += m.get("content", "") + "\n\n"
            else:
                filtered_messages.append(m)

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": filtered_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        if system_text:
            payload["system"] = system_text.strip()

        # Convert tool schemas to Anthropic format
        if tools:
            anthropic_tools = []
            for t in tools:
                fn = t.get("function", {})
                anthropic_tools.append({
                    "name": fn.get("name"),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object"}),
                })
            payload["tools"] = anthropic_tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    yield StreamChunk(content=f"[Anthropic Error: {err.decode('utf-8', errors='replace')}]", finish_reason="error")
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    try:
                        event = json.loads(data_str)
                    except Exception:
                        continue

                    evt_type = event.get("type")
                    if evt_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield StreamChunk(content=delta.get("text", ""))
                        elif delta.get("type") == "thinking_delta":
                            yield StreamChunk(thinking=delta.get("thinking", ""))
                    elif evt_type == "message_stop":
                        yield StreamChunk(finish_reason="stop")
