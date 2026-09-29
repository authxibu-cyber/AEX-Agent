"""
OpenAI-Compatible Provider for AEX Agent.
Supports OpenRouter, Nous Portal, OpenAI, DeepSeek, Groq, and vLLM.
Streams reasoning tokens, tool calls, and content deltas via SSE.
"""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from aex_agent.providers.base import BaseProvider, StreamChunk


class OpenAICompatibleProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "glm-5.3-flash",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_budget: int = 0,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or "https://openrouter.ai/api/v1",
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
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AEX-Agent/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # OpenRouter app identity headers
        if "openrouter" in self.base_url.lower():
            headers["HTTP-Referer"] = "https://github.com/AEX-Agent/AEX-Agent"
            headers["X-Title"] = "AEX Agent"

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        # Request token accounting in the SSE stream (OpenAI-compatible servers)
        payload["stream_options"] = {"include_usage": True}

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        if self.thinking_budget > 0:
            payload["thinking"] = {"type": "enabled", "budget_tokens": self.thinking_budget}

        payload.update(kwargs)

        # Buffer for accumulating streaming tool call deltas
        tool_call_accumulator: Dict[int, Dict[str, Any]] = {}

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    err_msg = f"HTTP {response.status_code}: {err_body.decode('utf-8', errors='replace')}"
                    yield StreamChunk(content=f"[Provider Error: {err_msg}]", finish_reason="error")
                    return

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk_json = json.loads(data_str)
                    except Exception:
                        continue

                    choices = chunk_json.get("choices", [])
                    if not choices:
                        # Usage-only chunks (include_usage) carry an empty choices list
                        if chunk_json.get("usage"):
                            yield StreamChunk(
                                content="",
                                thinking="",
                                tool_calls=[],
                                finish_reason=None,
                                raw=chunk_json,
                                usage=chunk_json["usage"],
                            )
                        continue

                    choice = choices[0]
                    delta = choice.get("delta", {})
                    finish_reason = choice.get("finish_reason")

                    content_delta = delta.get("content") or ""
                    # Support DeepSeek, Nous Hermes, and OpenAI reasoning fields
                    reasoning_delta = (
                        delta.get("reasoning_content")
                        or delta.get("reasoning")
                        or delta.get("thought")
                        or ""
                    )

                    # Handle partial tool call chunks
                    raw_tool_calls = delta.get("tool_calls", [])
                    active_tool_calls: List[Dict[str, Any]] = []

                    for tc in raw_tool_calls:
                        idx = tc.get("index", 0)
                        if idx not in tool_call_accumulator:
                            tool_call_accumulator[idx] = {
                                "id": tc.get("id", f"call_{idx}"),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }

                        fn = tc.get("function", {})
                        if fn.get("name"):
                            tool_call_accumulator[idx]["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            tool_call_accumulator[idx]["function"]["arguments"] += fn["arguments"]

                    if finish_reason == "tool_calls" or (finish_reason and tool_call_accumulator):
                        active_tool_calls = list(tool_call_accumulator.values())

                    yield StreamChunk(
                        content=content_delta,
                        thinking=reasoning_delta,
                        tool_calls=active_tool_calls,
                        finish_reason=finish_reason,
                        raw=chunk_json,
                        usage=chunk_json.get("usage"),
                    )
