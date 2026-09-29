"""
Conversation State & Telemetry for AEX Agent.
Tracks messages, active turn metrics, tokens, and execution flags.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TurnMessage(BaseModel):
    role: str
    content: str
    thinking: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "New Session"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    context_limit: int = 0  # 0 = unknown
    turn_count: int = 0
    active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def record_usage(self, usage: Dict[str, Any]) -> None:
        """Merge a provider usage payload into cumulative session counters."""
        p = int(usage.get("prompt_tokens") or 0)
        c = int(usage.get("completion_tokens") or 0)
        self.prompt_tokens += p
        self.completion_tokens += c
        self.total_tokens += p + c

    def append_message(self, role: str, content: str, **kwargs) -> Dict[str, Any]:
        msg: Dict[str, Any] = {"role": role, "content": content}
        msg.update(kwargs)
        self.messages.append(msg)
        self.updated_at = time.time()
        return msg
