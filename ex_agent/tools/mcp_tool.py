"""
Model Context Protocol (MCP) Client Adapter for EX Agent.
Connects to standard MCP servers (stdio or SSE), fetches tool schemas,
and dynamically registers them into EX Agent's ToolRegistry under the 'mcp__' namespace.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ex_agent.tools.base import BaseTool, ToolRegistry, ToolResult, registry


class MCPClientAdapter:
    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.registry = tool_registry or registry

    def register_mcp_tool(
        self,
        server_name: str,
        tool_name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Any,
    ) -> BaseTool:
        """Register a dynamic tool exposed by an external MCP server."""
        prefixed_name = f"mcp__{server_name}__{tool_name}"

        async def dynamic_mcp_wrapper(**kwargs) -> ToolResult:
            try:
                res = await handler(tool_name, kwargs)
                return ToolResult(success=True, output=str(res))
            except Exception as e:
                return ToolResult(success=False, output="", error=f"MCP call failed: {e}")

        tool_obj = BaseTool(
            name=prefixed_name,
            description=f"[MCP: {server_name}] {description}",
            func=dynamic_mcp_wrapper,
            toolset="mcp",
            is_dangerous=False,
        )
        tool_obj._schema = {
            "type": "function",
            "function": {
                "name": prefixed_name,
                "description": tool_obj.description,
                "parameters": parameters,
            },
        }

        self.registry.register(tool_obj)
        return tool_obj
