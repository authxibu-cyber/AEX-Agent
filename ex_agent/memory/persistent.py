"""
Persistent Bounded Memory Engine for EX Agent.
Strictly implements the bounded filing cabinet:
- MEMORY.md: World & project memory (bounded to MEMORY_MD_MAX_CHARS ~2200 chars)
- USER.md: User traits, style, preferences (bounded to USER_MD_MAX_CHARS ~1375 chars)
Features proactive consolidation when bounds are approached.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ex_constants import (
    MEMORY_MD_MAX_CHARS,
    USER_MD_MAX_CHARS,
    get_memory_file,
    get_user_file,
)


class MemoryManager:
    def __init__(self, memory_file: Optional[Path] = None, user_file: Optional[Path] = None):
        self.memory_file = memory_file or get_memory_file()
        self.user_file = user_file or get_user_file()
        self._ensure_files()

    def _ensure_files(self) -> None:
        """Initialize memory files if not present."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_file.exists():
            default_memory = (
                "# World & Project Knowledge Base\n"
                "- System initialized with EX Agent engine.\n"
                "- Persistent memory loop active.\n"
            )
            self.memory_file.write_text(default_memory, encoding="utf-8")

        if not self.user_file.exists():
            default_user = (
                "# User Profile & Preferences\n"
                "- Prefers direct, high-leverage engineering solutions.\n"
                "- Adheres to the GodEye Mandate: Tier 3 deep architectures.\n"
            )
            self.user_file.write_text(default_user, encoding="utf-8")

    def read_memory(self) -> str:
        """Read MEMORY.md."""
        self._ensure_files()
        try:
            return self.memory_file.read_text(encoding="utf-8")
        except Exception:
            return ""

    def read_user(self) -> str:
        """Read USER.md."""
        self._ensure_files()
        try:
            return self.user_file.read_text(encoding="utf-8")
        except Exception:
            return ""

    def update_memory(self, content_to_append: str, consolidate: bool = True) -> Tuple[bool, str]:
        """
        Append new facts to MEMORY.md.
        If size exceeds MEMORY_MD_MAX_CHARS, triggers auto-consolidation/pruning.
        """
        self._ensure_files()
        current = self.read_memory().rstrip()
        new_entry = f"\n- {content_to_append.strip()}"
        combined = current + new_entry

        if len(combined) > MEMORY_MD_MAX_CHARS and consolidate:
            combined = self._consolidate(combined, max_chars=MEMORY_MD_MAX_CHARS, header="# World & Project Knowledge Base")

        self.memory_file.write_text(combined, encoding="utf-8")
        return True, f"Updated MEMORY.md ({len(combined)}/{MEMORY_MD_MAX_CHARS} chars)"

    def update_user(self, content_to_append: str, consolidate: bool = True) -> Tuple[bool, str]:
        """
        Append user preferences to USER.md.
        If size exceeds USER_MD_MAX_CHARS, triggers auto-consolidation/pruning.
        """
        self._ensure_files()
        current = self.read_user().rstrip()
        new_entry = f"\n- {content_to_append.strip()}"
        combined = current + new_entry

        if len(combined) > USER_MD_MAX_CHARS and consolidate:
            combined = self._consolidate(combined, max_chars=USER_MD_MAX_CHARS, header="# User Profile & Preferences")

        self.user_file.write_text(combined, encoding="utf-8")
        return True, f"Updated USER.md ({len(combined)}/{USER_MD_MAX_CHARS} chars)"

    def replace_memory(self, new_content: str) -> Tuple[bool, str]:
        """Completely replace MEMORY.md with curated content."""
        if len(new_content) > MEMORY_MD_MAX_CHARS:
            new_content = new_content[:MEMORY_MD_MAX_CHARS]
        self.memory_file.write_text(new_content, encoding="utf-8")
        return True, f"Replaced MEMORY.md ({len(new_content)} chars)"

    def replace_user(self, new_content: str) -> Tuple[bool, str]:
        """Completely replace USER.md with curated content."""
        if len(new_content) > USER_MD_MAX_CHARS:
            new_content = new_content[:USER_MD_MAX_CHARS]
        self.user_file.write_text(new_content, encoding="utf-8")
        return True, f"Replaced USER.md ({len(new_content)} chars)"

    def _consolidate(self, text: str, max_chars: int, header: str) -> str:
        """
        Algorithmic FIFO consolidation preserving header and most salient recent lines.
        Ensures strict boundary enforcement without loss of structure.
        """
        lines = [line for line in text.splitlines() if line.strip()]
        preserved_header = lines[0] if lines and lines[0].startswith("#") else header
        bullet_lines = [l for l in lines if l.startswith("- ") or l.startswith("* ")]

        # Drop oldest bullet entries until fit
        while bullet_lines and len(preserved_header + "\n" + "\n".join(bullet_lines)) > max_chars:
            bullet_lines.pop(0)

        result = preserved_header + "\n" + "\n".join(bullet_lines)
        if len(result) > max_chars:
            result = result[:max_chars]
        return result

    def get_summary(self) -> Dict[str, Any]:
        """Return memory statistics."""
        mem = self.read_memory()
        usr = self.read_user()
        return {
            "memory_chars": len(mem),
            "memory_max": MEMORY_MD_MAX_CHARS,
            "user_chars": len(usr),
            "user_max": USER_MD_MAX_CHARS,
            "memory_file": str(self.memory_file),
            "user_file": str(self.user_file),
        }
