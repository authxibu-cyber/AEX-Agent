"""
Tool Execution Pool & Security Dispatcher for EX Agent.
Handles concurrent execution via asyncio.gather, output budgeting, and approval gates.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from ex_agent.tools.base import BaseTool, ToolRegistry, ToolResult, registry


class ToolExecutor:
    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        approval_mode: str = "dangerous",
        max_output_chars: int = 15000,
        timeout_seconds: float = 60.0,
        approval_callback: Optional[Callable[[BaseTool, Dict[str, Any]], bool]] = None,
    ):
        self.registry = tool_registry or registry
        self.approval_mode = approval_mode
        self.max_output_chars = max_output_chars
        self.timeout_seconds = timeout_seconds
        self.approval_callback = approval_callback

    async def execute_call(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        tool_obj = self.registry.get(name)
        if not tool_obj:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' is not registered or not permitted.",
            )

        # Security Approval Gate
        if self._requires_approval(tool_obj):
            if self.approval_callback:
                approved = self.approval_callback(tool_obj, arguments)
                if not approved:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Execution of dangerous tool '{name}' was rejected by user.",
                    )

        # Execution with timeout
        try:
            result = await asyncio.wait_for(
                tool_obj.execute(**arguments),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' timed out after {self.timeout_seconds}s.",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' unhandled execution error: {e}",
            )

        # Output Budgeting
        if len(result.output) > self.max_output_chars:
            head = result.output[: self.max_output_chars // 2]
            tail = result.output[-self.max_output_chars // 2 :]
            truncated = f"{head}\n\n[... Truncated {len(result.output) - self.max_output_chars} chars by EX Agent output governor ...]\n\n{tail}"
            result.output = truncated

        return result

    async def execute_parallel(self, calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Executes multiple tool calls concurrently via asyncio.gather.
        Collapses multi-tool latency into a single roundtrip.
        """
        tasks = []
        for call in calls:
            name = call.get("name", "")
            args = call.get("arguments", {})
            call_id = call.get("id", f"call_{name}")
            tasks.append(self._wrapped_call(call_id, name, args))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = []
        for r in results:
            if isinstance(r, Exception):
                out.append({
                    "id": "unknown",
                    "name": "error",
                    "result": ToolResult(success=False, output="", error=str(r)),
                })
            else:
                out.append(r)
        return out

    async def _wrapped_call(self, call_id: str, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        res = await self.execute_call(name, args)
        return {"id": call_id, "name": name, "result": res}

    def _requires_approval(self, tool_obj: BaseTool) -> bool:
        if self.approval_mode == "none":
            return False
        if self.approval_mode == "all":
            return True
        if self.approval_mode == "dangerous" and tool_obj.is_dangerous:
            return True
        return False
