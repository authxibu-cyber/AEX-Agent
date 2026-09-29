"""
Interactive Setup Wizard for EX Agent.
Configures provider credentials, default models, and stores configuration in EX_HOME.
"""
from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt
from ex_agent.config import load_config, save_config

console = Console()


def run_setup_wizard() -> None:
    console.print("[bold cyan]=== EX Agent Configuration Wizard ===[/bold cyan]\n")
    cfg = load_config()

    console.print(f"Current Model: [bold green]{cfg.model}[/bold green]")
    new_model = Prompt.ask("Enter default model", default=cfg.model)
    cfg.model = new_model

    console.print(f"Current Provider: [bold yellow]{cfg.provider}[/bold yellow]")
    new_provider = Prompt.ask(
        "Enter provider (openrouter / nous_portal / openai / anthropic / ollama / vllm)",
        default=cfg.provider,
    )
    cfg.provider = new_provider.lower()

    if cfg.provider not in ["ollama", "vllm"]:
        api_key = Prompt.ask("Enter API Key (press Enter to keep existing or use .env)", default=cfg.api_key or "")
        if api_key:
            cfg.api_key = api_key

    save_config(cfg)
    console.print("\n[bold green]✔ Configuration saved successfully![/bold green]")
