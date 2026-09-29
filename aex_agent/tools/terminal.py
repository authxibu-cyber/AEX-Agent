"""
Terminal Tool for AEX Agent.
Native Windows PowerShell and cross-platform POSIX execution with timeout and output capture.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from aex_agent.tools.base import ToolResult, tool


@tool(
    name="terminal",
    description="Execute a shell command on the operating system. Runs in PowerShell on Windows, bash on POSIX.",
    toolset="terminal",
    is_dangerous=True,
)
async def terminal(command: str, cwd: Optional[str] = None, timeout: float = 60.0) -> ToolResult:
    """Execute command in native shell."""
    working_dir = Path(cwd).resolve() if cwd else Path.cwd()
    if not working_dir.exists():
        return ToolResult(success=False, output="", error=f"Working directory does not exist: {working_dir}")

    is_windows = sys.platform == "win32"
    if is_windows:
        cmd_args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    else:
        cmd_args = ["/bin/bash", "-c", command]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(working_dir),
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )

        stdout_str = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr_str = stderr_bytes.decode("utf-8", errors="replace").strip()

        combined = []
        if stdout_str:
            combined.append(stdout_str)
        if stderr_str:
            combined.append(f"[STDERR]\n{stderr_str}")

        output = "\n".join(combined) if combined else "[Command produced no output]"
        success = proc.returncode == 0

        return ToolResult(
            success=success,
            output=output,
            error=None if success else f"Command exited with code {proc.returncode}",
            metadata={"returncode": proc.returncode, "cwd": str(working_dir)},
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return ToolResult(success=False, output="", error=f"Command timed out after {timeout} seconds.")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to execute command: {e}")
