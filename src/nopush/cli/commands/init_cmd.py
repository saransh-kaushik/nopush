"""``nopush init`` — interactive first-time setup."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from nopush.config.constants import (
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_MODELS,
    SUPPORTED_PROVIDERS,
)
from nopush.config.manager import ConfigManager
from nopush.config.schema import ProviderCredentials

console = Console()

_PROVIDER_KEY_HINTS: dict[str, str] = {
    "openai": "sk-...",
    "anthropic": "sk-ant-...",
    "gemini": "AIza...",
}


def _pick_model(provider: str) -> str:
    """Interactively select a model for *provider*.

    Renders a numbered table of known models and lets the user pick by
    number, or choose "other" to type a custom model ID.

    Returns the chosen model identifier string.
    """
    models = PROVIDER_MODELS.get(provider, [])
    default_model = PROVIDER_DEFAULT_MODELS.get(provider, "")

    # Build a pretty table
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("#", style="cyan", width=3)
    table.add_column("Model ID", style="bold white")
    table.add_column("Description", style="dim")

    for i, (model_id, description) in enumerate(models, 1):
        row_style = "bold green" if model_id == default_model else ""
        marker = " ★" if model_id == default_model else ""
        table.add_row(str(i), model_id + marker, description, style=row_style)

    console.print()
    console.print(table)

    default_index = next(
        (i + 1 for i, (mid, _) in enumerate(models) if mid == default_model),
        1,
    )

    while True:
        raw = Prompt.ask(
            f"Select a model [1-{len(models)}]",
            default=str(default_index),
        )
        try:
            choice = int(raw.strip())
        except ValueError:
            console.print(f"[red]Please enter a number between 1 and {len(models)}.[/red]")
            continue

        if not 1 <= choice <= len(models):
            console.print(f"[red]Please enter a number between 1 and {len(models)}.[/red]")
            continue

        selected_id, _ = models[choice - 1]

        if selected_id == "other":
            custom = Prompt.ask("Enter custom model ID").strip()
            if not custom:
                console.print("[red]Model ID cannot be empty.[/red]")
                continue
            return custom

        return selected_id


def init_callback() -> None:
    """Walk the user through first-time NoPush configuration.

    This command collects the AI provider, API key, and preferred model,
    then persists them to ``~/.nopush/credentials.yaml``.
    """
    console.print(
        Panel.fit(
            "[bold cyan]NoPush — First-time Setup[/bold cyan]\n"
            "[dim]Configure your AI provider, API key, and model.[/dim]",
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
    console.print("\n[bold]Step 3 of 3[/bold] — Choose a model")
    console.print(
        f"  [dim]Select from the list below, or choose [bold]Other[/bold] "
        f"to enter a custom model ID.[/dim]"
    )

    model = _pick_model(provider_input)

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
