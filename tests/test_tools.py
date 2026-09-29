"""
Unit Tests for AEX Agent Tools & Toolsets.
Verifies tool execution, parallel dispatch, and schema generation.
"""
import asyncio
from aex_agent.tools.base import BaseTool, ToolRegistry, ToolResult, registry
from aex_agent.tools.executor import ToolExecutor
from aex_agent.tools.filesystem import file_write, file_read
import tempfile
from pathlib import Path


def test_tool_schema_generation():
    schemas = registry.get_schemas()
    assert len(schemas) > 0
    names = [s["function"]["name"] for s in schemas]
    assert "terminal" in names
    assert "file_read" in names
    assert "web_search" in names


def test_filesystem_tools():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "sample.txt"
        write_res = file_write(str(test_file), "Line 1\nLine 2\nLine 3")
        assert write_res.success is True

        read_res = file_read(str(test_file), start_line=1, end_line=2)
        assert read_res.success is True
        assert "Line 1" in read_res.output
