"""Rich-based terminal rendering for review results.

Renders :class:`~nopush.review.models.ReviewResult` objects as beautiful,
colour-coded terminal output using the Rich library.

Features:
- Summary header with issue counts by severity
- Colour-coded panels for each review comment
- Syntax-highlighted code suggestions
- Congratulatory message when no issues are found
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

if TYPE_CHECKING:
    from nopush.review.models import ReviewComment, ReviewResult

# ---------------------------------------------------------------------------
# Severity styling
# ---------------------------------------------------------------------------

_SEVERITY_STYLES: dict[str, tuple[str, str]] = {
    "critical": ("bold red", "🔴"),
    "warning": ("bold yellow", "🟡"),
    "suggestion": ("bold blue", "🔵"),
    "nitpick": ("dim", "⚪"),
}

_SEVERITY_BORDER: dict[str, str] = {
    "critical": "red",
    "warning": "yellow",
    "suggestion": "blue",
    "nitpick": "dim",
}

# Map file extensions to Rich Syntax lexer names
_LANGUAGE_LEXER_MAP: dict[str, str] = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "jsx": "jsx",
    "tsx": "tsx",
    "java": "java",
    "go": "go",
    "rust": "rust",
    "ruby": "ruby",
    "php": "php",
    "c": "c",
    "cpp": "cpp",
    "csharp": "csharp",
    "swift": "swift",
    "bash": "bash",
    "yaml": "yaml",
    "json": "json",
    "toml": "toml",
    "html": "html",
    "css": "css",
    "sql": "sql",
    "markdown": "markdown",
    "kotlin": "kotlin",
    "scala": "scala",
    "dart": "dart",
}


class ReviewRenderer:
    """Formats and renders :class:`ReviewResult` objects to the terminal.

    Parameters
    ----------
    console:
        Optional Rich Console instance. If ``None``, a new one is created.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render(self, result: ReviewResult) -> None:
        """Render a full review result to the console.

        Displays a summary header, followed by individual comment panels.
        If no issues are found, shows a congratulatory message.
        """
        self.console.print()

        if result.total_issues == 0:
            self._render_clean(result)
            return

        # Summary panel
        summary = self._render_summary(result)
        self.console.print(summary)
        self.console.print()

        # Individual comments
        for i, comment in enumerate(result.comments, 1):
            panel = self._render_comment(comment, index=i)
            self.console.print(panel)
            self.console.print()

        # Footer
        self._render_footer(result)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _render_summary(self, result: ReviewResult) -> Panel:
        """Render a summary panel with issue counts by severity."""
        from nopush.review.models import Severity

        counts = result.count_by_severity()

        # Build severity counts line
        parts: list[Text] = []
        for severity in Severity:
            count = counts.get(severity, 0)
            style, emoji = _SEVERITY_STYLES.get(severity.value, ("", ""))
            segment = Text(f"{emoji} {count} {severity.value}", style=style)
            parts.append(segment)

        counts_line = Text("  ").join(parts)

        # Build the content
        content = Text()
        content.append("Files reviewed: ", style="bold")
        content.append(str(result.files_reviewed))
        content.append("  •  ")
        content.append("Total issues: ", style="bold")
        content.append(str(result.total_issues))
        content.append("\n")
        content.append(counts_line)
        content.append("\n\n")
        content.append("Provider: ", style="dim")
        content.append(result.provider, style="dim bold")
        content.append("  •  ", style="dim")
        content.append("Model: ", style="dim")
        content.append(result.model, style="dim bold")

        return Panel(
            content,
            title="[bold]NoPush Review Summary[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )

    # ------------------------------------------------------------------
    # Individual comments
    # ------------------------------------------------------------------

    def _render_comment(self, comment: ReviewComment, index: int = 1) -> Panel:
        """Render a single review comment as a styled panel."""
        severity_val = comment.severity.value
        style, emoji = _SEVERITY_STYLES.get(severity_val, ("", ""))
        border = _SEVERITY_BORDER.get(severity_val, "white")

        # Title line
        title_text = Text()
        title_text.append(f"{emoji} ", style=style)
        title_text.append(f"[{severity_val.upper()}] ", style=style)
        title_text.append(comment.title, style="bold")

        # Location line
        location = Text()
        location.append("📁 ", style="dim")
        location.append(comment.file_path, style="cyan")
        location.append(f":{comment.line_number}", style="cyan bold")

        # Explanation
        explanation = Text(comment.explanation, style="")

        # Build content
        content = Text()
        content.append_text(title_text)
        content.append("\n\n")
        content.append_text(location)
        content.append("\n\n")
        content.append_text(explanation)

        # Code suggestion
        if comment.suggestion:
            content.append("\n\n")
            content.append("💡 Suggested fix:", style="bold green")
            content.append("\n")

        panel_content: list[RenderableType] = [content]

        if comment.suggestion:
            # Infer language from file path for syntax highlighting
            lexer = self._infer_lexer(comment.file_path)
            syntax = Syntax(
                comment.suggestion,
                lexer,
                theme="monokai",
                line_numbers=False,
                padding=1,
            )
            panel_content.append(syntax)

        # Build the panel with a group of renderables
        group = Group(*panel_content)

        return Panel(
            group,
            title=f"[{style}]Issue #{index}[/{style}]",
            border_style=border,
            padding=(0, 2),
        )

    # ------------------------------------------------------------------
    # Clean code / no issues
    # ------------------------------------------------------------------

    def _render_clean(self, result: ReviewResult) -> None:
        """Render a congratulatory message when no issues are found."""
        content = Text()
        content.append("✨ ", style="bold green")
        content.append("No issues found!", style="bold green")
        content.append("\n\n")
        content.append(
            "Your code looks great. No critical bugs, warnings, or suggestions were identified.",
            style="",
        )
        content.append("\n\n")
        content.append("Files reviewed: ", style="dim")
        content.append(str(result.files_reviewed), style="dim bold")
        content.append("  •  ", style="dim")
        content.append("Provider: ", style="dim")
        content.append(result.provider, style="dim bold")
        content.append("  •  ", style="dim")
        content.append("Model: ", style="dim")
        content.append(result.model, style="dim bold")

        panel = Panel(
            content,
            title="[bold green]NoPush Review[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    def _render_footer(self, result: ReviewResult) -> None:
        """Render a minimal footer after all comments."""
        from nopush.review.models import Severity

        counts = result.count_by_severity()
        critical = counts.get(Severity.CRITICAL, 0)

        if critical > 0:
            self.console.print(
                f"  [bold red]⚠  {critical} critical issue(s) "
                f"require immediate attention.[/bold red]"
            )
        self.console.print(
            f"  [dim]Review complete — {result.total_issues} issue(s) "
            f"across {result.files_reviewed} file(s).[/dim]\n"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_lexer(file_path: str) -> str:
        """Infer a Rich Syntax lexer name from the file path."""
        from pathlib import PurePosixPath

        suffix = PurePosixPath(file_path).suffix.lower()
        # Simple extension -> lexer mapping
        ext_map: dict[str, str] = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".swift": "swift",
            ".sh": "bash",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".toml": "toml",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".kt": "kotlin",
            ".scala": "scala",
            ".dart": "dart",
        }
        return ext_map.get(suffix, "text")
