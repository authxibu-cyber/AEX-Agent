"""
Autonomous Skill Learning Engine for EX Agent.
Implements the self-improving loop:
Synthesizes, tests, and saves executable skills into ~/.ex/skills/<name>/SKILL.md.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple
import yaml

from ex_agent.skills.manager import Skill, SkillManager
from ex_constants import get_skills_dir


class SkillLearner:
    def __init__(self, skill_manager: Optional[SkillManager] = None):
        self.skill_manager = skill_manager or SkillManager()
        self.user_skills_dir = get_skills_dir()

    def create_skill(
        self,
        name: str,
        description: str,
        instructions: str,
        triggers: Optional[List[str]] = None,
        tools: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Creates and persists a new skill following agentskills.io standard.
        """
        clean_name = re.sub(r"[^a-zA-Z0-9_\-]", "-", name.strip().lower())
        if not clean_name:
            return False, "Invalid skill name."

        target_dir = self.user_skills_dir / clean_name
        target_dir.mkdir(parents=True, exist_ok=True)
        skill_file = target_dir / "SKILL.md"

        frontmatter = {
            "name": clean_name,
            "description": description.strip(),
            "triggers": triggers or [clean_name],
            "tools": tools or ["terminal", "file"],
        }

        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
        content = f"---\n{yaml_str}---\n\n{instructions.strip()}\n"

        try:
            skill_file.write_text(content, encoding="utf-8")
            self.skill_manager.reload_skills()
            return True, f"Skill '{clean_name}' successfully created and registered at {skill_file}"
        except Exception as e:
            return False, f"Failed to persist skill: {e}"

    def delete_skill(self, name: str) -> Tuple[bool, str]:
        """Removes a user-authored skill."""
        clean_name = name.strip().lower()
        target_dir = self.user_skills_dir / clean_name
        skill_file = target_dir / "SKILL.md"

        if not skill_file.exists():
            return False, f"User skill '{clean_name}' not found."

        try:
            skill_file.unlink()
            if target_dir.exists() and not any(target_dir.iterdir()):
                target_dir.rmdir()
            self.skill_manager.reload_skills()
            return True, f"Skill '{clean_name}' removed."
        except Exception as e:
            return False, f"Failed to remove skill: {e}"
