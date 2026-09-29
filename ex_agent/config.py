"""
EX Agent Configuration Subsystem.
Handles environment variables, YAML config persistence in EX_HOME, and provider credentials.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from ex_constants import (
    DEFAULT_GATEWAY_HOST,
    DEFAULT_GATEWAY_PORT,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    get_config_path,
    get_env_path,
    get_ex_home,
)

# Load environment variables from global EX_HOME .env and current working directory .env
load_dotenv(dotenv_path=get_env_path())
load_dotenv(dotenv_path=Path.cwd() / ".env")


class ChannelConfig(BaseModel):
    enabled: bool = False
    token: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class Config(BaseModel):
    model: str = Field(default=DEFAULT_MODEL, description="Active LLM model name")
    provider: str = Field(default=DEFAULT_PROVIDER, description="Active model provider")
    base_url: Optional[str] = Field(default=None, description="Custom API base URL override")
    api_key: Optional[str] = Field(default=None, description="Direct API key override")
    temperature: float = Field(default=0.7, description="Generation sampling temperature")
    max_tokens: int = Field(default=4096, description="Max generation tokens")
    thinking_budget: int = Field(default=0, description="Reasoning thinking tokens budget (0 = disabled)")
    enabled_toolsets: List[str] = Field(
        default_factory=lambda: [
            "web",
            "terminal",
            "file",
            "memory",
            "skills",
            "code_execution",
            "delegation",
            "cronjob",
        ]
    )
    approval_mode: str = Field(
        default="dangerous",
        description="Approval mode for tool calls: 'none', 'dangerous', or 'all'",
    )
    gateway_host: str = Field(default=DEFAULT_GATEWAY_HOST)
    gateway_port: int = Field(default=DEFAULT_GATEWAY_PORT)
    save_trajectories: bool = Field(default=True, description="Save interaction trajectories for RL/training")

    # Multi-channel gateway configurations
    channels: Dict[str, ChannelConfig] = Field(
        default_factory=lambda: {
            "telegram": ChannelConfig(token=os.environ.get("TELEGRAM_BOT_TOKEN")),
            "discord": ChannelConfig(token=os.environ.get("DISCORD_BOT_TOKEN")),
            "slack": ChannelConfig(token=os.environ.get("SLACK_BOT_TOKEN")),
        }
    )

    def resolve_api_key(self) -> Optional[str]:
        """Resolves the best API key for the configured provider."""
        if self.api_key:
            return self.api_key

        provider = self.provider.lower()
        key_map = {
            "openrouter": "OPENROUTER_API_KEY",
            "nous_portal": "NOUS_PORTAL_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "together": "TOGETHER_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "xai": "XAI_API_KEY",
        }

        env_var = key_map.get(provider)
        if env_var:
            val = os.environ.get(env_var, "").strip()
            if val:
                return val

        # Fallback to general API_KEY if available
        return os.environ.get("EX_API_KEY") or os.environ.get("API_KEY")

    def resolve_base_url(self) -> Optional[str]:
        """Resolves the base URL for the active provider."""
        if self.base_url:
            return self.base_url

        from ex_constants import (
            ANTHROPIC_BASE_URL,
            DEEPSEEK_BASE_URL,
            GEMINI_BASE_URL,
            GROQ_BASE_URL,
            MISTRAL_BASE_URL,
            NOUS_PORTAL_BASE_URL,
            OLLAMA_BASE_URL,
            OPENAI_BASE_URL,
            OPENROUTER_BASE_URL,
            TOGETHER_BASE_URL,
            XAI_BASE_URL,
        )

        provider = self.provider.lower()
        known_urls = {
            "openrouter": OPENROUTER_BASE_URL,
            "nous_portal": NOUS_PORTAL_BASE_URL,
            "openai": OPENAI_BASE_URL,
            "anthropic": ANTHROPIC_BASE_URL,
            "groq": GROQ_BASE_URL,
            "deepseek": DEEPSEEK_BASE_URL,
            "gemini": GEMINI_BASE_URL,
            "together": TOGETHER_BASE_URL,
            "mistral": MISTRAL_BASE_URL,
            "xai": XAI_BASE_URL,
            # Ollama: no /v1 suffix for its native API, but LocalProvider
            # speaks OpenAI-compatible, so keep /v1
            "ollama": os.environ.get("OLLAMA_HOST", OLLAMA_BASE_URL),
            "vllm": os.environ.get("VLLM_HOST", "http://localhost:8000/v1"),
        }
        if provider in known_urls:
            url = known_urls[provider]
            # Normalize local endpoints for OpenAI-compatible clients:
            # - OLLAMA_HOST is often set to the bind address (0.0.0.0) or the
            #   native API root without /v1 — both unusable as a client base URL.
            if provider == "ollama":
                url = url.replace("://0.0.0.0", "://127.0.0.1").rstrip("/")
                if not url.endswith("/v1"):
                    url += "/v1"
            return url
        # Unknown provider: assume generic OpenAI-compatible endpoint via EX_BASE_URL,
        # else raise so misconfiguration is loud instead of silently routing to OpenRouter.
        env_base = os.environ.get("EX_BASE_URL", "").strip()
        if env_base:
            return env_base
        raise ValueError(
            f"No known base URL for provider '{self.provider}'. "
            f"Set `base_url` in {get_config_path()} or EX_BASE_URL in your .env."
        )


def load_config() -> Config:
    """Loads configuration from YAML file in EX_HOME, merged with env vars."""
    config_file = get_config_path()
    data: Dict[str, Any] = {}

    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded
        except Exception:
            pass

    # Environment variable overrides
    if "EX_MODEL" in os.environ:
        data["model"] = os.environ["EX_MODEL"]
    if "EX_PROVIDER" in os.environ:
        data["provider"] = os.environ["EX_PROVIDER"]
    if "EX_BASE_URL" in os.environ:
        data["base_url"] = os.environ["EX_BASE_URL"]
    if "EX_API_KEY" in os.environ:
        data["api_key"] = os.environ["EX_API_KEY"]
    if "EX_GATEWAY_HOST" in os.environ:
        data["gateway_host"] = os.environ["EX_GATEWAY_HOST"]
    if "EX_GATEWAY_PORT" in os.environ:
        try:
            data["gateway_port"] = int(os.environ["EX_GATEWAY_PORT"])
        except ValueError:
            pass

    config = Config(**data)
    return config


def save_config(config: Config) -> None:
    """Persists configuration to YAML in EX_HOME."""
    config_file = get_config_path()
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False)
