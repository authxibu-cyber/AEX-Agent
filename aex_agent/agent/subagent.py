"""
Subagent Delegation Engine for AEX Agent.
Spawns isolated subagent workers for parallel workstreams and pipeline delegation.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from aex_agent.tools.base import ToolResult, tool


@tool(
    name="delegate_task",
    description="Spawn an isolated subagent worker to execute a parallel subtask and return distilled findings.",
    toolset="delegation",
)
async def delegate_task(task_description: str, context_details: str = "") -> ToolResult:
    """Delegates a specialized subtask to an autonomous subagent."""
    from aex_agent.agent.core import EXAgent
    from aex_agent.config import load_config

    cfg = load_config()
    # Scoped subagent configuration
    subagent = EXAgent(
        config=cfg,
        system_instructions=f"You are a specialized subagent executing the following mission:\n{task_description}\nContext:\n{context_details}",
    )

    try:
        res = await subagent.run_conversation_async(
            user_message=f"Execute this task thoroughly and return a structured summary of results: {task_description}",
            max_iterations=8,
        )
        final_text = res.get("response", "[Subagent produced no output]")
        return ToolResult(
            success=True,
            output=final_text,
            metadata={"subagent_session_id": res.get("session_id")},
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Subagent execution failed: {e}")
