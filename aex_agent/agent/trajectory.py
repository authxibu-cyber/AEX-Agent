"""
Trajectory Logger & Compressor for AEX Agent.
Exports multi-turn trajectories to ShareGPT and Hermes-RL formats for post-training/fine-tuning.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aex_constants import get_trajectories_dir


class TrajectoryLogger:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or get_trajectories_dir()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_sharegpt(self, session_id: str, messages: List[Dict[str, Any]], model_name: str = "") -> Path:
        """
        Converts session messages to ShareGPT format:
        {
          "id": "<session_id>",
          "model": "<model>",
          "conversations": [
            {"from": "system", "value": "..."},
            {"from": "human", "value": "..."},
            {"from": "gpt", "value": "..."}
          ]
        }
        """
        conversations = []
        role_map = {"system": "system", "user": "human", "assistant": "gpt", "tool": "tool"}

        for m in messages:
            sender = role_map.get(m.get("role", ""), m.get("role", "human"))
            val = m.get("content", "")
            if m.get("tool_calls"):
                val = f"[Tool Calls: {json.dumps(m['tool_calls'])}\n{val}]".strip()
            conversations.append({"from": sender, "value": val})

        payload = {
            "id": session_id,
            "model": model_name,
            "conversations": conversations,
        }

        target_file = self.output_dir / f"trajectory_{session_id}.json"
        target_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target_file
