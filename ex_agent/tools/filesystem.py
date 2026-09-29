"""
Filesystem Tools for EX Agent.
Surgical file reading, writing, patching, directory exploration, and glob search.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from ex_agent.tools.base import ToolResult, tool


@tool(name="file_read", description="Read lines from a file with optional start and end line ranges.", toolset="file")
def file_read(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> ToolResult:
    p = Path(path).resolve()
    if not p.is_file():
        return ToolResult(success=False, output="", error=f"File not found: {p}")

    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        total_lines = len(lines)

        s = (start_line - 1) if (start_line and start_line > 0) else 0
        e = end_line if (end_line and end_line > 0) else total_lines

        selected = lines[s:e]
        numbered = [f"{s + i + 1:5d} | {line}" for i, line in enumerate(selected)]
        output = "".join(numbered)
        return ToolResult(
            success=True,
            output=output,
            metadata={"total_lines": total_lines, "returned_lines": len(selected)},
        )
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to read file: {e}")


@tool(name="file_write", description="Create or overwrite a file with given content.", toolset="file", is_dangerous=True)
def file_write(path: str, content: str) -> ToolResult:
    p = Path(path).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(success=True, output=f"Successfully wrote {len(content)} characters to {p}")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to write file: {e}")


@tool(
    name="file_patch",
    description="Surgically replace a unique target chunk of text in an existing file with replacement text.",
    toolset="file",
    is_dangerous=True,
)
def file_patch(path: str, target: str, replacement: str) -> ToolResult:
    p = Path(path).resolve()
    if not p.is_file():
        return ToolResult(success=False, output="", error=f"File not found: {p}")

    try:
        text = p.read_text(encoding="utf-8")
        occurrences = text.count(target)
        if occurrences == 0:
            return ToolResult(success=False, output="", error="Target string was not found in the file.")
        if occurrences > 1:
            return ToolResult(
                success=False,
                output="",
                error=f"Target string is ambiguous ({occurrences} occurrences). Provide more surrounding context.",
            )

        patched = text.replace(target, replacement, 1)
        p.write_text(patched, encoding="utf-8")
        return ToolResult(success=True, output=f"Successfully patched {p}")
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to patch file: {e}")


@tool(name="list_dir", description="List entries in a directory with file types and sizes.", toolset="file")
def list_dir(path: str = ".") -> ToolResult:
    p = Path(path).resolve()
    if not p.is_dir():
        return ToolResult(success=False, output="", error=f"Directory not found: {p}")

    try:
        entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        lines = []
        for entry in entries:
            kind = "[DIR] " if entry.is_dir() else "[FILE]"
            size = ""
            if entry.is_file():
                try:
                    size = f" ({entry.stat().st_size:,} bytes)"
                except Exception:
                    pass
            lines.append(f"{kind} {entry.name}{size}")
        output = "\n".join(lines) if lines else "[Empty directory]"
        return ToolResult(success=True, output=output, metadata={"count": len(entries)})
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to list directory: {e}")


@tool(name="find_files", description="Search for files matching a glob pattern.", toolset="file")
def find_files(pattern: str, root: str = ".") -> ToolResult:
    p = Path(root).resolve()
    if not p.is_dir():
        return ToolResult(success=False, output="", error=f"Root directory not found: {p}")

    try:
        matches = list(p.rglob(pattern))
        lines = [str(m.relative_to(p)) for m in matches[:100]]
        output = "\n".join(lines) if lines else "No matching files found."
        if len(matches) > 100:
            output += f"\n... and {len(matches) - 100} more matches."
        return ToolResult(success=True, output=output, metadata={"total_matches": len(matches)})
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Failed to find files: {e}")
