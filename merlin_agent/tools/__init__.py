"""
Merlin Agent Pluggable Toolsets Engine.
Registers all core capabilities with OpenAI/Hermes compatible function schemas.
"""
from merlin_agent.tools.base import BaseTool, ToolRegistry, ToolResult, tool
from merlin_agent.tools.executor import ToolExecutor

__all__ = ["BaseTool", "ToolRegistry", "ToolResult", "tool", "ToolExecutor"]
