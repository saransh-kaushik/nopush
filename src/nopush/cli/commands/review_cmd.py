"""``nopush review`` — run an AI-powered code review.

This command orchestrates the full review pipeline:

1. Load configuration
2. Get staged diffs
3. Build prompts
4. Send to LLM provider
5. Parse response
6. Render results in the terminal
"""

from __future__ import annotations

import typer
from rich.console import Console

from nopush.config.constants import SUPPORTED_REVIEW_DEPTHS

console = Console()


def review_callback(
    depth: str | None = typer.Option(
        None,
        "--depth",
        "-d",
        help=f"Review depth: {', '.join(SUPPORTED_REVIEW_DEPTHS)}.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Override the configured LLM provider.",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Override the configured model.",
    ),
    max_files: int | None = typer.Option(
        None,
        "--max-files",
        help="Maximum number of files to review.",
    ),
) -> None:
    """Analyze staged Git changes and display AI-powered review suggestions.

    This is the main command of NoPush. It reads staged diffs, sends them
    to the configured LLM provider, and renders structured feedback in the
    terminal.
    """
    from nopush.cli.renderer import ReviewRenderer
    from nopush.config.manager import ConfigManager
    from nopush.git.diff_parser import get_staged_diff, parse_diff
    from nopush.providers.base import ProviderAuthError, ProviderError
    from nopush.providers.registry import get_provider
    from nopush.review.engine import ReviewEngine

    # ── Step 1: Load config ──
    overrides: dict[str, object] = {}
    if depth is not None:
        if depth not in SUPPORTED_REVIEW_DEPTHS:
            console.print(
                f"[red]Invalid review depth '{depth}'. "
                f"Choose from: {', '.join(SUPPORTED_REVIEW_DEPTHS)}[/red]"
            )
            raise typer.Exit(code=1)
        overrides["review_depth"] = depth
    if provider is not None:
        overrides["provider"] = provider
    if model is not None:
        overrides["model"] = model
    if max_files is not None:
        overrides["max_files"] = max_files

    try:
        config = ConfigManager.load(overrides=overrides if overrides else None)
    except Exception as exc:
        console.print(f"[red]Failed to load configuration:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    # ── Step 2: Check API key ──
    if not config.api_key:
        console.print(
            "[red]No API key configured.[/red]\n"
            "Run [bold cyan]nopush init[/bold cyan] to set up your provider, "
            "or set the [bold]NOPUSH_API_KEY[/bold] environment variable."
        )
        raise typer.Exit(code=1)

    # ── Step 3: Get staged diffs ──
    with console.status("[bold cyan]Reading staged changes…[/bold cyan]", spinner="dots"):
        try:
            raw_diff = get_staged_diff()
        except RuntimeError as exc:
            console.print(f"[red]Git error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    if not raw_diff.strip():
        console.print(
            "\n[yellow]No staged changes found.[/yellow]\n"
            "[dim]Stage your changes with [bold]git add[/bold] "
            "before running [bold]nopush review[/bold].[/dim]\n"
        )
        raise typer.Exit()

    # ── Step 4: Parse diffs ──
    file_diffs = parse_diff(raw_diff, ignore_patterns=config.ignore)

    if not file_diffs:
        console.print(
            "\n[yellow]All changed files were excluded by ignore patterns.[/yellow]\n"
            "[dim]Check your nopush.yaml ignore configuration.[/dim]\n"
        )
        raise typer.Exit()

    # Apply max_files limit
    if len(file_diffs) > config.max_files:
        console.print(
            f"[yellow]Warning:[/yellow] {len(file_diffs)} files changed, "
            f"but max_files is set to {config.max_files}. "
            f"Reviewing only the first {config.max_files} files.\n"
        )
        file_diffs = file_diffs[: config.max_files]

    # ── Step 5: Instantiate provider ──
    try:
        llm_provider = get_provider(config)
    except ProviderAuthError as exc:
        console.print(f"[red]Authentication error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except ProviderError as exc:
        console.print(f"[red]Provider error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    # ── Step 6: Run review ──
    engine = ReviewEngine(provider=llm_provider, config=config)

    file_count = len(file_diffs)
    total_additions = sum(fd.total_additions for fd in file_diffs)
    total_deletions = sum(fd.total_deletions for fd in file_diffs)

    console.print(
        f"\n[bold cyan]Reviewing {file_count} file(s)[/bold cyan] "
        f"[dim](+{total_additions} / -{total_deletions} lines)[/dim]"
    )
    console.print(
        f"[dim]Provider: {config.provider} • Model: {config.model} "
        f"• Depth: {config.review_depth}[/dim]\n"
    )

    with console.status(
        "[bold cyan]Waiting for AI review…[/bold cyan]",
        spinner="dots",
    ):
        try:
            result = engine.review(file_diffs)
        except ProviderAuthError as exc:
            console.print(f"\n[red]Authentication failed:[/red] {exc}")
            console.print("[dim]Check your API key with [bold]nopush init[/bold].[/dim]")
            raise typer.Exit(code=1) from exc
        except ProviderError as exc:
            console.print(f"\n[red]Provider error:[/red] {exc}")
            raise typer.Exit(code=1) from exc
        except Exception as exc:
            console.print(f"\n[red]Unexpected error during review:[/red] {exc}")
            raise typer.Exit(code=1) from exc

    # ── Step 7: Render results ──
    renderer = ReviewRenderer(console=console)
    renderer.render(result)
