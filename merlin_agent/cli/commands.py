"""
Slash Command Registry for Merlin Agent.
Implements universal slash commands across CLI, TUI, and messaging channels.
"""
from __future__ import annotations

import shlex
from typing import Any, Callable, Dict, List, Optional, Tuple

from merlin_agent.config import Config, load_config, save_config
from merlin_agent.memory.persistent import MemoryManager
from merlin_agent.memory.store import SessionStore
from merlin_agent.skills.learner import SkillLearner
from merlin_agent.skills.manager import SkillManager
from merlin_agent.tools.toolsets import TOOLSETS


class Command:
    def __init__(self, name: str, description: str, handler: Callable[..., Any]):
        self.name = name
        self.description = description
        self.handler = handler


class SlashCommandRegistry:
    def __init__(self):
        self._commands: Dict[str, Command] = {}
        self._register_defaults()

    def register(self, name: str, description: str):
        def decorator(fn: Callable[..., Any]):
            self._commands[name.lower()] = Command(name=name.lower(), description=description, handler=fn)
            return fn
        return decorator

    def get(self, name: str) -> Optional[Command]:
        return self._commands.get(name.lower().lstrip("/"))

    def list_commands(self) -> List[Command]:
        return sorted(self._commands.values(), key=lambda c: c.name)

    def handle(self, input_text: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Parses text. If it begins with '/', executes command.
        Returns: (was_command, result_message)
        """
        if not input_text.startswith("/"):
            return False, ""

        parts = shlex.split(input_text)
        cmd_name = parts[0].lstrip("/").lower()
        args = parts[1:]

        cmd = self.get(cmd_name)
        if not cmd:
            return True, f"Unknown command: /{cmd_name}. Type `/help` for available commands."

        try:
            res = cmd.handler(args, context)
            return True, str(res)
        except Exception as e:
            return True, f"Command `/{cmd_name}` error: {e}"

    def _register_defaults(self):
        @self.register("help", "List all available slash commands.")
        def cmd_help(args, ctx):
            lines = ["# Available Slash Commands:"]
            for c in self.list_commands():
                lines.append(f"- **/{c.name}**: {c.description}")
            return "\n".join(lines)

        @self.register("model", "View or switch active model. Usage: `/model [new_model_name]`")
        def cmd_model(args, ctx):
            cfg = load_config()
            if not args:
                return f"Active model: **{cfg.model}** (Provider: `{cfg.provider}`)"
            new_model = args[0]
            cfg.model = new_model
            save_config(cfg)
            if "agent" in ctx:
                ctx["agent"].model = new_model
                ctx["agent"].provider = ctx["agent"]._init_provider()
            return f"Switched model to: **{new_model}**"

        @self.register("provider", "View or switch active provider. Usage: `/provider [openrouter|nous_portal|openai|anthropic|ollama|vllm]`")
        def cmd_provider(args, ctx):
            cfg = load_config()
            if not args:
                return f"Active provider: **{cfg.provider}** (Base URL: `{cfg.resolve_base_url()}`)"
            new_provider = args[0].lower()
            cfg.provider = new_provider
            save_config(cfg)
            if "agent" in ctx:
                ctx["agent"].provider_name = new_provider
                ctx["agent"].base_url = cfg.resolve_base_url()
                ctx["agent"].api_key = cfg.resolve_api_key()
                ctx["agent"].provider = ctx["agent"]._init_provider()
            return f"Switched provider to: **{new_provider}**"

        @self.register("memory", "Inspect persistent MEMORY.md and USER.md.")
        def cmd_memory(args, ctx):
            mgr = MemoryManager()
            summary = mgr.get_summary()
            mem = mgr.read_memory()
            usr = mgr.read_user()
            return (
                f"### Persistent Memory Cabinet\n"
                f"- **MEMORY.md** ({summary['memory_chars']}/{summary['memory_max']} chars):\n{mem}\n\n"
                f"- **USER.md** ({summary['user_chars']}/{summary['user_max']} chars):\n{usr}"
            )

        @self.register("skills", "List all loaded skills.")
        def cmd_skills(args, ctx):
            mgr = SkillManager()
            skills = mgr.list_skills()
            lines = ["# Registered Skills:"]
            for s in skills:
                src = "User" if s.is_user_skill else "Bundled"
                lines.append(f"- **{s.name}** [{src}]: {s.description}")
            return "\n".join(lines)

        @self.register("learn", "Synthesize a new skill. Usage: `/learn <name> <description>`")
        def cmd_learn(args, ctx):
            if len(args) < 2:
                return "Usage: `/learn <name> <description>`"
            name = args[0]
            desc = " ".join(args[1:])
            learner = SkillLearner()
            ok, msg = learner.create_skill(
                name=name,
                description=desc,
                instructions=f"Instructions for {name}:\n1. Implement standard operations for {name}.\n2. Deliver verified outputs.",
            )
            return msg

        @self.register("tools", "List registered toolsets and capabilities.")
        def cmd_tools(args, ctx):
            lines = ["# Registered Toolsets:"]
            for ts, tools in TOOLSETS.items():
                lines.append(f"- **{ts}**: {', '.join(tools)}")
            return "\n".join(lines)

        @self.register("sessions", "List past conversation sessions.")
        def cmd_sessions(args, ctx):
            store = SessionStore()
            sessions = store.list_sessions(limit=15)
            lines = ["# Recent Sessions:"]
            for s in sessions:
                lines.append(f"- **{s['title']}** (ID: `{s['session_id'][:8]}...`) | {s['message_count']} msgs")
            return "\n".join(lines)

        @self.register("search", "Search past sessions with FTS5. Usage: `/search <query>`")
        def cmd_search(args, ctx):
            if not args:
                return "Usage: `/search <query>`"
            q = " ".join(args)
            store = SessionStore()
            matches = store.search_sessions(q, limit=5)
            if not matches:
                return f"No matches found for '{q}'."
            lines = [f"# Search Results for '{q}':"]
            for m in matches:
                lines.append(f"- [{m['title']} | Role: {m['role']}]: {m['content'][:150]}...")
            return "\n".join(lines)

        @self.register("export", "Export current session trajectory to ShareGPT format.")
        def cmd_export(args, ctx):
            agent = ctx.get("agent")
            if not agent:
                return "No active agent session to export."
            path = agent.trajectory_logger.export_sharegpt(
                agent.session_id,
                agent.state.messages,
                model_name=agent.model,
            )
            return f"Trajectory exported to: `{path}`"

        @self.register("copy", "Copy a recent assistant reply's raw text to the clipboard. Usage: `/copy [n]` (default: last reply)")
        def cmd_copy(args, ctx):
            agent = ctx.get("agent")
            if not agent:
                return "No active agent session."
            n = 1
            if args:
                try:
                    n = int(args[0])
                except ValueError:
                    return "Usage: `/copy [n]` — n is the nth-latest assistant reply (default 1)."

            # Collect assistant replies from the session store (chronological)
            replies = [
                m["content"]
                for m in agent.session_store.get_messages(agent.session_id, limit=200)
                if m["role"] == "assistant" and m.get("content")
            ]
            if not replies:
                return "No assistant replies in this session yet."
            if n < 1 or n > len(replies):
                return f"Only {len(replies)} assistant reply/replies available — pick 1..{len(replies)}."
            text = replies[-n]  # n=1 → latest, n=2 → one before, …

            # OSC 52 clipboard escape works in most modern terminals (Windows Terminal included)
            import base64, sys
            payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
            sys.stdout.write(f"\x1b]52;c;{payload}\x07")
            sys.stdout.flush()

            preview = text[:60].replace("\n", " ")
            return f"Copied reply #{n} ({len(text)} chars) to clipboard. Preview: {preview}…"


# Global slash command registry
commands_registry = SlashCommandRegistry()
