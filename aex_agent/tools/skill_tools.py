"""
Skill Management & Learning Tools for AEX Agent.
Enables AEX Agent to author new skills and dynamically inspect the skill catalog.
"""
from __future__ import annotations

from typing import List, Optional

from aex_agent.skills.learner import SkillLearner
from aex_agent.skills.manager import SkillManager
from aex_agent.tools.base import ToolResult, tool

_skill_manager = SkillManager()
_skill_learner = SkillLearner(_skill_manager)


@tool(
    name="learn_skill",
    description="Synthesize and save a new reusable skill into ~/.ex/skills/<name>/SKILL.md following agentskills.io standard.",
    toolset="skills",
)
def learn_skill(
    name: str,
    description: str,
    instructions: str,
    triggers: Optional[List[str]] = None,
    tools: Optional[List[str]] = None,
) -> ToolResult:
    ok, msg = _skill_learner.create_skill(
        name=name,
        description=description,
        instructions=instructions,
        triggers=triggers,
        tools=tools,
    )
    return ToolResult(success=ok, output=msg)


@tool(name="list_skills", description="List all registered bundled and user skills.", toolset="skills")
def list_skills() -> ToolResult:
    skills = _skill_manager.list_skills()
    if not skills:
        return ToolResult(success=True, output="No skills registered.")

    lines = []
    for s in skills:
        origin = "User" if s.is_user_skill else "Bundled"
        triggers_str = ", ".join(s.triggers) if s.triggers else "none"
        lines.append(f"- **{s.name}** [{origin}]: {s.description}\n  Triggers: {triggers_str}")
    return ToolResult(success=True, output="\n".join(lines))


@tool(name="read_skill", description="Read the full instructions and metadata of a specific skill.", toolset="skills")
def read_skill(name: str) -> ToolResult:
    skill = _skill_manager.get_skill(name)
    if not skill:
        return ToolResult(success=False, output="", error=f"Skill '{name}' not found.")

    output = (
        f"# Skill: {skill.name}\n"
        f"**Description:** {skill.description}\n"
        f"**Triggers:** {skill.triggers}\n"
        f"**Tools:** {skill.tools}\n\n"
        f"## Instructions:\n{skill.instructions}"
    )
    return ToolResult(success=True, output=output)
