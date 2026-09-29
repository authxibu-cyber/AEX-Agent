"""
EX Agent Persistent Memory Subsystem.
Implements the 3-layer memory architecture:
1. Long-term world/project memory (MEMORY.md)
2. User model & preferences (USER.md)
3. FTS5 SQLite cross-session recall and project context injection.
"""
from ex_agent.memory.persistent import MemoryManager
from ex_agent.memory.store import SessionStore
from ex_agent.memory.context import ContextEngine

__all__ = ["MemoryManager", "SessionStore", "ContextEngine"]
