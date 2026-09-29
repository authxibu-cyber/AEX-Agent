"""
Resilient Tool Call & Reasoning Parser for AEX Agent.
Parses both native OpenAI tool_calls and Hermes XML tags (<tool_call> and <thought> / <think>).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple


class ToolParser:
    @staticmethod
    def extract_thought(text: str) -> Tuple[str, str]:
        """
        Extracts reasoning content from <thought>...</thought> or <think>...</think> blocks.
        Returns: (cleaned_content, reasoning_content)
        """
        thought_pattern = re.compile(r"<(thought|think)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
        thoughts = []

        def replacer(match):
            thoughts.append(match.group(2).strip())
            return ""

        cleaned = thought_pattern.sub(replacer, text).strip()
        reasoning = "\n\n".join(thoughts).strip()
        return cleaned, reasoning

    @staticmethod
    def parse_tool_calls(
        native_calls: Optional[List[Dict[str, Any]]],
        content_text: str,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Combines native API tool calls and prompt-embedded Hermes XML tool calls.
        Returns (parsed_tool_calls, cleaned_text).
        """
        calls: List[Dict[str, Any]] = []

        # 1. Process native OpenAI-style tool calls if present
        if native_calls:
            for idx, call in enumerate(native_calls):
                fn = call.get("function", {})
                name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")

                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {"raw_input": raw_args}
                elif isinstance(raw_args, dict):
                    args = raw_args
                else:
                    args = {}

                calls.append({
                    "id": call.get("id", f"call_{idx}"),
                    "name": name,
                    "arguments": args,
                })

        # 2. Extract Hermes-style XML tool calls: <tool_call>{"name": ..., "arguments": ...}</tool_call>
        xml_pattern = re.compile(r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL)
        matched_chunks = []

        def xml_replacer(match):
            matched_chunks.append(match.group(1))
            return ""

        cleaned_text = xml_pattern.sub(xml_replacer, content_text).strip()

        for idx, chunk in enumerate(matched_chunks):
            try:
                parsed = json.loads(chunk)
                name = parsed.get("name") or parsed.get("tool")
                args = parsed.get("arguments") or parsed.get("args") or {}
                if name:
                    calls.append({
                        "id": f"xml_call_{idx}",
                        "name": name,
                        "arguments": args,
                    })
            except Exception:
                pass

        return calls, cleaned_text
