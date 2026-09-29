"""
Base Tool Abstractions & Registry for EX Agent.
Generates strict OpenAI / Hermes 3 function calling schemas.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_string(self) -> str:
        if not self.success and self.error:
            return f"Error: {self.error}\nOutput: {self.output}".strip()
        return self.output


class BaseTool:
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable[..., Any],
        toolset: str = "general",
        is_dangerous: bool = False,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.toolset = toolset
        self.is_dangerous = is_dangerous
        self._schema = self._build_schema()

    def _build_schema(self) -> Dict[str, Any]:
        """Build standard OpenAI / Hermes function schema from python type annotations."""
        sig = inspect.signature(self.func)
        properties = {}
        required = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                param_type = type_map.get(param.annotation, "string")

            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter `{param_name}`",
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    @property
    def schema(self) -> Dict[str, Any]:
        return self._schema

    async def execute(self, **kwargs) -> ToolResult:
        try:
            if inspect.iscoroutinefunction(self.func):
                res = await self.func(**kwargs)
            else:
                res = self.func(**kwargs)

            if isinstance(res, ToolResult):
                return res
            return ToolResult(success=True, output=str(res))
        except Exception as e:
            return ToolResult(success=False, output="", error=f"Tool '{self.name}' failed: {e}")


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self, enabled_toolsets: Optional[List[str]] = None) -> List[BaseTool]:
        if enabled_toolsets is None:
            return list(self._tools.values())
        return [t for t in self._tools.values() if t.toolset in enabled_toolsets]

    def get_schemas(self, enabled_toolsets: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        return [t.schema for t in self.list_tools(enabled_toolsets)]


# Global tool registry
registry = ToolRegistry()


def tool(name: Optional[str] = None, description: Optional[str] = None, toolset: str = "general", is_dangerous: bool = False):
    """Decorator to easily register functions as EX Agent tools."""
    def decorator(fn: Callable[..., Any]):
        t_name = name or fn.__name__
        t_desc = description or (fn.__doc__ or "").strip() or f"Execute {t_name}"
        t = BaseTool(name=t_name, description=t_desc, func=fn, toolset=toolset, is_dangerous=is_dangerous)
        registry.register(t)
        return fn
    return decorator
