"""
Skill Manager for EX Agent.
Scans and loads skills following the agentskills.io standard.
Parses YAML frontmatter in SKILL.md files across user and bundled directories.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

from ex_constants import get_bundled_skills_dir, get_skills_dir


class Skill(BaseModel):
    name: str
    description: str
    triggers: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    path: Path
    instructions: str
    is_user_skill: bool = False


class SkillManager:
    def __init__(self, user_skills_dir: Optional[Path] = None, bundled_skills_dir: Optional[Path] = None):
        self.user_skills_dir = user_skills_dir or get_skills_dir()
        self.bundled_skills_dir = bundled_skills_dir or get_bundled_skills_dir()
        self.skills: Dict[str, Skill] = {}
        self.reload_skills()

    def reload_skills(self) -> None:
        """Scan both bundled and user skills directories."""
        self.skills.clear()

        # 1. Bundled skills
        if self.bundled_skills_dir.exists():
            self._scan_directory(self.bundled_skills_dir, is_user=False)

        # 2. User skills (overrides bundled skills with the same name)
        if self.user_skills_dir.exists():
            self._scan_directory(self.user_skills_dir, is_user=True)

    def _scan_directory(self, base_dir: Path, is_user: bool) -> None:
        for root, _, files in os.walk(base_dir):
            if "SKILL.md" in files:
                skill_path = Path(root) / "SKILL.md"
                skill = self._parse_skill_file(skill_path, is_user=is_user)
                if skill:
                    self.skills[skill.name.lower()] = skill

    def _parse_skill_file(self, path: Path, is_user: bool) -> Optional[Skill]:
        try:
            content = path.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return None

            parts = content.split("---", 2)
            if len(parts) < 3:
                return None

            frontmatter_raw = parts[1]
            instructions = parts[2].strip()

            meta = yaml.safe_load(frontmatter_raw)
            if not isinstance(meta, dict):
                return None

            name = str(meta.get("name", path.parent.name)).strip()
            description = str(meta.get("description", "")).strip()
            triggers = meta.get("triggers", [])
            tools = meta.get("tools", [])

            if isinstance(triggers, str):
                triggers = [triggers]
            if isinstance(tools, str):
                tools = [tools]

            return Skill(
                name=name,
                description=description,
                triggers=list(triggers),
                tools=list(tools),
                path=path,
                instructions=instructions,
                is_user_skill=is_user,
            )
        except Exception:
            return None

    def get_skill(self, name: str) -> Optional[Skill]:
        return self.skills.get(name.lower())

    def list_skills(self) -> List[Skill]:
        return list(self.skills.values())

    def match_skills(self, text: str) -> List[Skill]:
        """Match skill triggers against user input."""
        lower_text = text.lower()
        matched = []
        for skill in self.skills.values():
            for trigger in skill.triggers:
                if trigger.lower() in lower_text:
                    matched.append(skill)
                    break
        return matched

    def format_skills_summary(self) -> str:
        """Formatted summary table of all loaded skills for the system prompt."""
        if not self.skills:
            return "No skills currently registered."

        lines = []
        for skill in sorted(self.skills.values(), key=lambda s: s.name):
            src = "User" if skill.is_user_skill else "Bundled"
            lines.append(f"- **{skill.name}** ({src}): {skill.description}")
        return "\n".join(lines)
