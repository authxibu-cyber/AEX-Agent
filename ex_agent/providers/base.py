"""
Base Provider Interface for EX Agent.
Defines unified async streaming, reasoning extraction, and function call protocol.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field


class StreamChunk(BaseModel):
    content: str = ""
    thinking: str = ""
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        thinking_budget: int = 0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.thinking_budget = thinking_budget

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Yields streaming response tokens and tool calls."""
        pass
