"""
Interactive Setup Wizard for Merlin Agent.
Configures provider, model, custom base URL, and API key - manually.
Credentials are stored in MERLIN_HOME/config.yaml (non-secret) and MERLIN_HOME/.env (secrets).
Includes a live connection test before saving.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from merlin_agent.config import Config, load_config, save_config
from merlin_constants import get_env_path

console = Console()

# (provider, needs_key, default_base_url)
PROVIDERS: list[tuple[str, bool, str]] = [
    ("openrouter", True, "https://openrouter.ai/api/v1"),
    ("nous_portal", True, "https://portal.nousresearch.com/v1"),
    ("openai", True, "https://api.openai.com/v1"),
    ("anthropic", True, "https://api.anthropic.com/v1"),
    ("gemini", True, "https://generativelanguage.googleapis.com/v1beta/openai"),
    ("groq", True, "https://api.groq.com/openai/v1"),
    ("deepseek", True, "https://api.deepseek.com/v1"),
    ("together", True, "https://api.together.xyz/v1"),
    ("mistral", True, "https://api.mistral.ai/v1"),
    ("xai", True, "https://api.x.ai/v1"),
    ("ollama", False, "http://localhost:11434/v1"),
    ("vllm", False, "http://localhost:8000/v1"),
    ("custom", True, ""),  # any OpenAI-compatible endpoint, base URL required
]

KEY_ENV_MAP = {
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
    # Cloud gateways (e.g. ollama.com) need keys too
    "ollama": "OLLAMA_API_KEY",
    "vllm": "VLLM_API_KEY",
    # Custom endpoints store the key under a provider-agnostic var
    "custom": "Merlin_API_KEY",
}

_LOCAL_URL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]", "0.0.0.0"}


def _is_local_url(base_url: str | None) -> bool:
    """True if the endpoint points at the machine itself (no API key expected)."""
    if not base_url:
        return False
    try:
        host = base_url.split("://", 1)[-1].split("/", 1)[0].lower()
        # Bracketed IPv6 like [::1]:11434 - split on ':' breaks it, handle first
        m = re.match(r"^\[(.+)\]", host)
        if m:
            host = m.group(1)
        else:
            host = host.split(":", 1)[0]
    except Exception:
        return False
    if host in _LOCAL_URL_HOSTS:
        return True
    # Private networks (192.168.x.x / 10.x.x.x / 172.16-31.x.x) count as local
    m = re.match(r"^(192\.168|10\.|172\.(1[6-9]|2\d|3[01])\.)", host)
    return bool(m)


def _mask(key: str) -> str:
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}...{key[-4:]}"


def _persist_to_env(env_var: str, value: str) -> None:
    """Write KEY=value into MERLIN_HOME/.env (create or update in place)."""
    env_path: Path = get_env_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^\s*#?\s*{env_var}\s*=.*$")
    replaced = False
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{env_var}={value}"
            replaced = True
            break
    if not replaced:
        lines.append(f"{env_var}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Make it effective immediately in this process
    os.environ[env_var] = value


def _test_connection(cfg: Config) -> tuple[bool, str]:
    """Fire a minimal synchronous chat request to verify credentials/endpoint."""
    try:
        import httpx
    except ImportError:
        return True, "httpx not installed - skipped connection test"

    base_url = (cfg.resolve_base_url() or "").rstrip("/")
    api_key = cfg.resolve_api_key()
    provider = cfg.provider.lower()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload: dict = {
        "model": cfg.model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "stream": False,
    }
    # Anthropic native endpoint uses a distinct wire format and headers
    if provider in ("anthropic", "claude") and "anthropic.com" in base_url:
        url = f"{base_url}/messages"
        headers = {
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
    else:
        url = f"{base_url}/chat/completions"

    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=30.0)
        if resp.status_code == 200:
            return True, "endpoint responded OK"
        detail = resp.text[:300]
        return False, f"HTTP {resp.status_code}: {detail}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _select_provider(current: str) -> str:
    table = Table(title="Available Providers", title_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Provider", style="bold")
    table.add_column("Default Base URL", style="dim")
    for i, (name, _nk, url) in enumerate(PROVIDERS, start=1):
        marker = " <- current" if name == current else ""
        table.add_row(str(i), name + marker, url or "(enter manually)")
    console.print(table)
    while True:
        raw = Prompt.ask("Select provider (number or name)", default=current)
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(PROVIDERS):
                return PROVIDERS[idx - 1][0]
        for name, _nk, _u in PROVIDERS:
            if raw.lower() == name:
                return name
        console.print("[red]Unknown provider - try again.[/red]")


def run_setup_wizard() -> None:
    console.print("[bold cyan]=== Merlin Agent Configuration Wizard ===[/bold cyan]\n")
    cfg = load_config()

    # --- Provider ---
    provider = _select_provider(cfg.provider)
    cfg.provider = provider
    entry = next((p for p in PROVIDERS if p[0] == provider), None)

    # --- Base URL ---
    default_url = (entry[2] if entry else "") or (cfg.base_url or "")
    if provider == "custom" or not default_url:
        base_url = Prompt.ask(
            "Enter base URL (OpenAI-compatible, incl. /v1)",
            default=cfg.base_url or "",
        )
        while not base_url.strip():
            base_url = Prompt.ask("[red]Base URL is required[/red] - enter base URL", default=cfg.base_url or "")
    else:
        base_url = Prompt.ask("Base URL", default=default_url)
        if base_url == default_url:
            base_url = ""  # empty = use built-in default
    cfg.base_url = base_url.strip() or None

    # --- Model ---
    console.print(f"Current Model: [bold green]{cfg.model}[/bold green]")
    cfg.model = Prompt.ask("Enter default model", default=cfg.model)

    # --- API Key (masked, persisted to .env) ---
    resolved_url = cfg.resolve_base_url() or ""
    env_var = KEY_ENV_MAP.get(provider, "Merlin_API_KEY")
    is_local = _is_local_url(resolved_url)
    needs_key = bool(entry and entry[1]) or (provider in ("ollama", "vllm") and not is_local)
    existing = os.environ.get(env_var, "") or cfg.api_key or ""
    if is_local:
        console.print(f"[dim]Local endpoint - no API key needed ({resolved_url})[/dim]")
    elif needs_key:
        console.print(f"Existing key for '{provider}': [bold]{_mask(existing)}[/bold]")
        new_key = Prompt.ask(
            "Paste new API key (Enter to keep existing)",
            password=True,
            default="",
        ).strip()
        if new_key:
            _persist_to_env(env_var, new_key)
            cfg.api_key = None  # prefer env-managed key
            console.print(f"[green]OK Key saved to {get_env_path()} ({env_var})[/green]")
    else:
        console.print(f"[dim]No API key configured for '{provider}' ({resolved_url})[/dim]")

    # --- Extras ---
    cfg.temperature = float(Prompt.ask("Temperature", default=str(cfg.temperature)))
    cfg.max_tokens = int(Prompt.ask("Max tokens", default=str(cfg.max_tokens)))
    cfg.thinking_budget = int(
        Prompt.ask("Thinking budget tokens (0=off)", default=str(cfg.thinking_budget))
    )

    # --- Verify before saving ---
    console.print("\n[bold]Testing connection...[/bold]")
    ok, msg = _test_connection(cfg)
    if ok:
        console.print(f"[bold green]OK Connection OK:[/bold green] {msg}")
    else:
        console.print(f"[bold red]X Connection failed:[/bold red] {msg}")
        retry = Prompt.ask("Save anyway?", choices=["y", "n"], default="n")
        if retry.lower() != "y":
            console.print("[yellow]Configuration NOT saved. Fix and rerun `merlin setup`.[/yellow]")
            return

    save_config(cfg)
    console.print("\n[bold green]OK Configuration saved successfully![/bold green]")
    console.print(f"  Model    : {cfg.model}")
    console.print(f"  Provider : {cfg.provider}")
    console.print(f"  Base URL : {cfg.resolve_base_url()}")
    console.print(f"  API Key  : {_mask(cfg.resolve_api_key() or '')}")
