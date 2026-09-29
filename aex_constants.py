"""
AEX Agent Constants & Path Resolution Engine.
Persistently mirrors Hermes Agent pathing, home resolutions, and bounds.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

APP_NAME = "AEX Agent"
CLI_NAME = "aex"
PACKAGE_NAME = "aex_agent"
VERSION = "1.0.0"

# Bounded Memory Thresholds (Characters) matching Hermes Agent specification
MEMORY_MD_MAX_CHARS: int = 2200
USER_MD_MAX_CHARS: int = 1375

# Default Gateway Configuration
DEFAULT_GATEWAY_HOST: str = "0.0.0.0"
DEFAULT_GATEWAY_PORT: int = 8642

# Default Models
DEFAULT_MODEL: str = "glm-5.3-flash"
DEFAULT_PROVIDER: str = "ollama"

OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
NOUS_PORTAL_BASE_URL: str = "https://portal.nousresearch.com/v1"
OPENAI_BASE_URL: str = "https://api.openai.com/v1"
OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"
GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
TOGETHER_BASE_URL: str = "https://api.together.xyz/v1"
MISTRAL_BASE_URL: str = "https://api.mistral.ai/v1"
XAI_BASE_URL: str = "https://api.x.ai/v1"

_ex_home_override: Optional[Path] = None


def set_ex_home_override(path: Path | str | None) -> None:
    """Set process-wide override for EX home directory."""
    global _ex_home_override
    if path is None:
        _ex_home_override = None
    else:
        _ex_home_override = Path(path).resolve()


def get_aex_home() -> Path:
    """
    Resolve AEX Agent root directory:
    1. Memory override
    2. AEX_HOME environment variable
    3. Platform default: %LOCALAPPDATA%\\aex on Windows, ~/.ex on POSIX
    """
    global _ex_home_override
    if _ex_home_override is not None:
        p = _ex_home_override
        p.mkdir(parents=True, exist_ok=True)
        return p

    env_home = os.environ.get("AEX_HOME", "").strip()
    if env_home:
        p = Path(env_home).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data) / "aex"
        else:
            base = Path.home() / ".aex"
    else:
        base = Path.home() / ".aex"

    base.mkdir(parents=True, exist_ok=True)
    return base


def get_memories_dir() -> Path:
    """Path to ~/.aex/memories/ containing MEMORY.md and USER.md."""
    p = get_aex_home() / "memories"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_memory_file() -> Path:
    """Path to MEMORY.md (world notes, bounded to ~2200 chars)."""
    return get_memories_dir() / "MEMORY.md"


def get_user_file() -> Path:
    """Path to USER.md (user profile & preferences, bounded to ~1375 chars)."""
    return get_memories_dir() / "USER.md"


def get_skills_dir() -> Path:
    """Path to ~/.aex/skills/ containing user-defined and learned skills."""
    p = get_aex_home() / "skills"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_bundled_skills_dir() -> Path:
    """Path to internal bundled skills packaged within aex_agent."""
    return Path(__file__).parent / "aex_agent" / "skills" / "builtin"


def get_sessions_dir() -> Path:
    """Path to ~/.aex/sessions/ storing session transcripts and state."""
    p = get_aex_home() / "sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_state_db_path() -> Path:
    """Path to SQLite database for FTS5 session search and telemetry."""
    return get_aex_home() / "aex_state.db"


def get_config_path() -> Path:
    """Path to config.yaml."""
    return get_aex_home() / "config.yaml"


def get_env_path() -> Path:
    """Path to .env in AEX_HOME."""
    return get_aex_home() / ".env"


def get_trajectories_dir() -> Path:
    """Path to trajectories directory for training / evaluation."""
    p = get_aex_home() / "trajectories"
    p.mkdir(parents=True, exist_ok=True)
    return p
