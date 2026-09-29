"""
Context Engine for AEX Agent.
Discovers hierarchical project-level instructions (AGENTS.md / EX.md),
loads SOUL.md (persona), and formats the persistent memory cabinet for system prompt injection.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from aex_agent.memory.persistent import MemoryManager
from aex_constants import get_aex_home


class ContextEngine:
    def __init__(self, start_dir: Optional[Path] = None, memory_manager: Optional[MemoryManager] = None):
        self.start_dir = Path(start_dir or Path.cwd()).resolve()
        self.memory_manager = memory_manager or MemoryManager()

    def find_project_context(self) -> Tuple[Optional[Path], str]:
        """
        Walks up directory tree from current working directory looking for:
        1. AGENTS.md
        2. EX.md
        Stops at filesystem root or git repository root (.git directory).
        """
        current = self.start_dir
        for parent in [current, *current.parents]:
            for candidate_name in ["AGENTS.md", "EX.md", "HERMES.md"]:
                cand = parent / candidate_name
                if cand.is_file():
                    try:
                        return cand, cand.read_text(encoding="utf-8")
                    except Exception:
                        pass
            if (parent / ".git").is_dir():
                break
        return None, ""

    def load_soul(self) -> str:
        """
        Loads SOUL.md defining AEX Agent's core intellect, tone, and cognitive pulse.
        Prioritizes AEX_HOME/SOUL.md, falling back to repository root SOUL.md or default.
        """
        ex_home_soul = get_aex_home() / "SOUL.md"
        if ex_home_soul.is_file():
            try:
                return ex_home_soul.read_text(encoding="utf-8")
            except Exception:
                pass

        repo_soul = Path(__file__).parent.parent.parent / "SOUL.md"
        if repo_soul.is_file():
            try:
                return repo_soul.read_text(encoding="utf-8")
            except Exception:
                pass

        return (
            "You are AEX Agent, an autonomous, self-improving AI agent harness "
            "adhering to the GodEye Mandate with deep Tier-3 architectures."
        )

    def assemble_system_prompt(
        self,
        skills_summary: str = "",
        extra_instructions: str = "",
        active_skill_protocols: str = "",
    ) -> str:
        """
        Assembles complete system prompt with:
        - SOUL.md (Persona & cognitive stance)
        - Project context (AGENTS.md / EX.md)
        - Persistent Memory Cabinet (MEMORY.md & USER.md)
        - Installed skills catalog
        - Active skill protocols (full instructions for trigger-matched skills this turn)
        - Dynamic runtime instructions
        """
        soul = self.load_soul().strip()
        _, project_context = self.find_project_context()
        memory_content = self.memory_manager.read_memory().strip()
        user_content = self.memory_manager.read_user().strip()

        sections = [soul]

        if project_context:
            sections.append(
                f"\n## Workspace & Project Guidelines (AGENTS.md)\n{project_context.strip()}"
            )

        if memory_content or user_content:
            sections.append(
                "\n## Persistent Memory Cabinet\n"
                f"### World & Project Memory (MEMORY.md)\n{memory_content}\n\n"
                f"### User Profile & Preferences (USER.md)\n{user_content}"
            )

        if skills_summary:
            sections.append(f"\n## Available Skills\n{skills_summary.strip()}")

        if active_skill_protocols:
            sections.append(
                "\n## Active Skill Protocols (triggered by this user message — follow strictly)\n"
                f"{active_skill_protocols.strip()}"
            )

        if extra_instructions:
            sections.append(f"\n## Session Directives\n{extra_instructions.strip()}")

        return "\n\n".join(sections)
