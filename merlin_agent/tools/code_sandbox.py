"""
Python Code Execution Sandbox for Merlin Agent.
Runs Python snippets in a subprocess or in-memory runner with output interception.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

from merlin_agent.tools.base import ToolResult, tool


@tool(
    name="code_execution",
    description="Execute Python code in an isolated runtime environment and capture stdout/stderr.",
    toolset="code_execution",
    is_dangerous=True,
)
async def code_execution(code: str, timeout: float = 30.0) -> ToolResult:
    """Executes Python code via a clean subprocess invocation."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(tmp_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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

        output = "\n".join(combined) if combined else "[Code completed with no output]"
        success = proc.returncode == 0

        return ToolResult(
            success=success,
            output=output,
            error=None if success else f"Execution failed with returncode {proc.returncode}",
            metadata={"returncode": proc.returncode},
        )
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return ToolResult(success=False, output="", error=f"Code execution timed out after {timeout}s.")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Execution error: {e}")
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
