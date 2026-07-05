"""``nopush init`` — interactive first-time setup."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from nopush.config.constants import (
    DEFAULT_MODEL,
    SUPPORTED_PROVIDERS,
)
from nopush.config.manager import ConfigManager
from nopush.config.schema import ProviderCredentials

console = Console()

# Default models per provider
_PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4.1",
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.0-flash",
}

_PROVIDER_KEY_HINTS: dict[str, str] = {
    "openai": "sk-...",
    "anthropic": "sk-ant-...",
    "gemini": "AIza...",
}


def init_callback() -> None:
    """Walk the user through first-time NoPush configuration.

    This command collects the AI provider, API key, and preferred model,
    then persists them to ``~/.nopush/credentials.yaml``.
    """
    console.print(
        Panel.fit(
            "[bold cyan]NoPush — First-time Setup[/bold cyan]\n"
            "[dim]Configure your AI provider and API key.[/dim]",
            border_style="cyan",
        )
    )

    # If credentials already exist, ask before overwriting
    existing = ConfigManager.load_credentials()
    if existing.api_key:
        overwrite = Confirm.ask(
            f"\n[yellow]Existing credentials found for provider "
            f"[bold]{existing.provider}[/bold] (model: {existing.model}). Overwrite?[/yellow]",
            default=False,
        )
        if not overwrite:
            console.print("[dim]Setup cancelled. Existing credentials kept.[/dim]")
            raise typer.Exit()

    # --- Step 1: Choose provider ---
    console.print("\n[bold]Step 1 of 3[/bold] — Choose your AI provider")
    for i, p in enumerate(SUPPORTED_PROVIDERS, 1):
        console.print(f"  [cyan]{i}[/cyan]. {p}")

    provider_input = Prompt.ask(
        "Provider",
        choices=SUPPORTED_PROVIDERS,
        default="openai",
    )

    # --- Step 2: API key ---
    key_hint = _PROVIDER_KEY_HINTS.get(provider_input, "")
    console.print(f"\n[bold]Step 2 of 3[/bold] — Enter your {provider_input} API key")
    if key_hint:
        console.print(f"  [dim]Expected format: {key_hint}[/dim]")

    api_key = Prompt.ask("API key", password=True)
    if not api_key.strip():
        console.print("[red]API key cannot be empty. Setup aborted.[/red]")
        raise typer.Exit(code=1)

    # --- Step 3: Model ---
    default_model = _PROVIDER_DEFAULT_MODELS.get(provider_input, DEFAULT_MODEL)
    console.print("\n[bold]Step 3 of 3[/bold] — Choose a model")
    console.print(f"  [dim]Default for {provider_input}: {default_model}[/dim]")

    model = Prompt.ask("Model", default=default_model)
    if not model.strip():
        model = default_model

    # --- Save credentials ---
    credentials = ProviderCredentials(
        provider=provider_input,
        api_key=api_key.strip(),
        model=model.strip(),
    )
    saved_path = ConfigManager.save_credentials(credentials)

    console.print(
        f"\n[bold green]✓ Setup complete![/bold green] "
        f"Credentials saved to [cyan]{saved_path}[/cyan]\n"
        f"  Provider : [bold]{credentials.provider}[/bold]\n"
        f"  Model    : [bold]{credentials.model}[/bold]\n"
        f"  API key  : [dim]{credentials.api_key[:8]}{'*' * 8}[/dim]\n"
    )
    console.print(
        "[dim]Run [bold]nopush review[/bold] to start reviewing your staged changes.[/dim]"
    )
