"""
Memory Management Tools for AEX Agent.
Enables the agent to proactively manage its 3-layer persistent memory cabinet
and query the SQLite FTS5 session index.
"""
from __future__ import annotations

from typing import Optional

from aex_agent.memory.persistent import MemoryManager
from aex_agent.memory.store import SessionStore
from aex_agent.tools.base import ToolResult, tool

_mem_manager = MemoryManager()
_session_store = SessionStore()


@tool(
    name="update_memory",
    description="Append durable world facts, project context, or architectural learnings to MEMORY.md.",
    toolset="memory",
)
def update_memory(fact: str) -> ToolResult:
    ok, msg = _mem_manager.update_memory(fact)
    return ToolResult(success=ok, output=msg)


@tool(
    name="update_user_model",
    description="Save user preferences, habits, instructions, or communication guidelines to USER.md.",
    toolset="memory",
)
def update_user_model(preference: str) -> ToolResult:
    ok, msg = _mem_manager.update_user(preference)
    return ToolResult(success=ok, output=msg)


@tool(
    name="read_memory_cabinet",
    description="Inspect current contents of MEMORY.md (world) and USER.md (user profile).",
    toolset="memory",
)
def read_memory_cabinet() -> ToolResult:
    summary = _mem_manager.get_summary()
    mem = _mem_manager.read_memory()
    usr = _mem_manager.read_user()
    output = (
        f"=== MEMORY.md ({summary['memory_chars']}/{summary['memory_max']} chars) ===\n{mem}\n\n"
        f"=== USER.md ({summary['user_chars']}/{summary['user_max']} chars) ===\n{usr}"
    )
    return ToolResult(success=True, output=output, metadata=summary)


@tool(
    name="session_search",
    description="Search across past conversation turns and session history using SQLite FTS5 BM25 ranking.",
    toolset="memory",
)
def session_search(query: str, limit: int = 5) -> ToolResult:
    results = _session_store.search_sessions(query, limit=limit)
    if not results:
        return ToolResult(success=True, output=f"No past interactions found matching query: '{query}'")

    lines = []
    for r in results:
        lines.append(
            f"[{r['title']} | Role: {r['role']} | BM25: {r['rank']:.2f}]\n{r['content']}\n---"
        )
    return ToolResult(success=True, output="\n".join(lines), metadata={"matches": len(results)})
