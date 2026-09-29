"""
Toolset Definitions & Preset Bundles for EX Agent.
Organizes tools into logical domains matching Hermes Agent.
"""
from __future__ import annotations

from typing import Dict, List, Set

# Import all tool modules so the @tool decorator registers them
import ex_agent.tools.terminal
import ex_agent.tools.filesystem
import ex_agent.tools.web
import ex_agent.tools.memory_tools
import ex_agent.tools.skill_tools
import ex_agent.tools.code_sandbox
import ex_agent.tools.mcp_tool

TOOLSETS: Dict[str, List[str]] = {
    "terminal": ["terminal"],
    "file": ["file_read", "file_write", "file_patch", "list_dir", "find_files"],
    "web": ["web_search", "fetch_web_page"],
    "memory": ["update_memory", "update_user_model", "read_memory_cabinet", "session_search"],
    "skills": ["learn_skill", "list_skills", "read_skill"],
    "code_execution": ["code_execution"],
    "delegation": ["delegate_task"],
    "cronjob": ["schedule_cron", "list_cron_jobs", "cancel_cron_job"],
    "safe": [
        "file_read",
        "list_dir",
        "find_files",
        "web_search",
        "fetch_web_page",
        "read_memory_cabinet",
        "session_search",
        "list_skills",
        "read_skill",
    ],
}


def resolve_tool_names(enabled_toolsets: List[str]) -> Set[str]:
    """Resolve active tool names from a list of requested toolsets."""
    selected = set()
    for ts in enabled_toolsets:
        ts_lower = ts.lower().strip()
        if ts_lower == "all":
            for tool_list in TOOLSETS.values():
                selected.update(tool_list)
            break
        elif ts_lower in TOOLSETS:
            selected.update(TOOLSETS[ts_lower])
    return selected
