"""
Merlin Agent Persistent Memory Subsystem.
Implements the 3-layer memory architecture:
1. Long-term world/project memory (MEMORY.md)
2. User model & preferences (USER.md)
3. FTS5 SQLite cross-session recall and project context injection.
"""
from merlin_agent.memory.persistent import MemoryManager
from merlin_agent.memory.store import SessionStore
from merlin_agent.memory.context import ContextEngine

__all__ = ["MemoryManager", "SessionStore", "ContextEngine"]
