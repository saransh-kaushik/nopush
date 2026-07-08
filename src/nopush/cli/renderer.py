"""Rich-based terminal rendering for review results.

Renders :class:`~nopush.review.models.ReviewResult` objects as beautiful,
colour-coded terminal output using the Rich library.

Features:
- Compact summary dashboard with issue counts by severity
- Structured issue panels with clear visual hierarchy
- Syntax-highlighted code suggestions
- Distinct severity styling (critical / warning / suggestion / nitpick)
- Polished footer and empty-state celebration panel
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from nopush.review.models import ReviewComment, ReviewResult

# ---------------------------------------------------------------------------
# Severity configuration
# ---------------------------------------------------------------------------

# (rich_style, icon, label)
_SEVERITY_CONFIG: dict[str, tuple[str, str, str]] = {
    "critical":   ("bold red",    "●", "CRITICAL"),
    "warning":    ("yellow",      "●", "WARNING"),
    "suggestion": ("bold blue",   "●", "SUGGESTION"),
    "nitpick":    ("dim",         "●", "NITPICK"),
}

_SEVERITY_BORDER: dict[str, str] = {
    "critical":   "red",
    "warning":    "yellow",
    "suggestion": "blue",
    "nitpick":    "bright_black",
}

_SEVERITY_EMOJI: dict[str, str] = {
    "critical":   "🔴",
    "warning":    "🟡",
    "suggestion": "🔵",
    "nitpick":    "⚪",
}


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

class ReviewRenderer:
    """Formats and renders :class:`ReviewResult` objects to the terminal.

    Parameters
    ----------
    console:
        Optional Rich Console instance. If ``None``, a new one is created.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render(self, result: ReviewResult, *, copy: bool = True) -> None:
        """Render a full review result to the console.

        Displays a summary dashboard, followed by individual comment panels.
        If no issues are found, shows a congratulatory empty-state message.

        Parameters
        ----------
        result:
            The review result to render.
        copy:
            When *True* (default), attempt to copy a plain-text summary of
            all issues to the system clipboard after rendering.
        """
        self.console.print()

        if result.total_issues == 0:
            self._render_clean(result)
            return

        # Summary dashboard
        self.console.print(self._render_summary(result))
        self.console.print()

        # Individual issue panels
        for comment in result.comments:
            self.console.print(self._render_comment(comment))
            self.console.print()

        # Footer
        self._render_footer(result)

        # Clipboard
        if copy:
            self._maybe_copy_to_clipboard(result)

    # ------------------------------------------------------------------
    # Summary dashboard
    # ------------------------------------------------------------------

    def _render_summary(self, result: ReviewResult) -> Panel:
        """Render a compact summary dashboard with two-column layout."""
        from nopush.review.models import Severity

        counts = result.count_by_severity()

        # --- Left column: high-level stats ---
        stats = Table.grid(padding=(0, 2))
        stats.add_column(style="dim", no_wrap=True)
        stats.add_column(style="bold")

        stats.add_row("Files Reviewed", str(result.files_reviewed))
        stats.add_row("Total Issues",   str(result.total_issues))

        # --- Severity breakdown ---
        severity_table = Table.grid(padding=(0, 2))
        severity_table.add_column(no_wrap=True)   # emoji + label
        severity_table.add_column(style="bold")   # count

        for severity in Severity:
            count = counts.get(severity, 0)
            sev_val = severity.value
            style, dot, label = _SEVERITY_CONFIG.get(sev_val, ("", "●", sev_val.upper()))
            emoji = _SEVERITY_EMOJI.get(sev_val, "")

            label_text = Text()
            label_text.append(f"{emoji} ", style="")
            label_text.append(label, style=style)

            count_text = Text(str(count), style=style if count > 0 else "dim")
            severity_table.add_row(label_text, count_text)

        # --- Right column: provider info ---
        meta = Table.grid(padding=(0, 2))
        meta.add_column(style="dim", no_wrap=True)
        meta.add_column(style="bold dim")

        meta.add_row("Provider", result.provider or "—")
        meta.add_row("Model",    result.model    or "—")

        # Compose the full dashboard grid
        dashboard = Table.grid(padding=(0, 4))
        dashboard.add_column(ratio=2)   # stats + severity
        dashboard.add_column(ratio=1)   # meta

        left = Group(
            stats,
            Text(""),  # spacer
            severity_table,
        )

        dashboard.add_row(left, Padding(meta, (2, 0, 0, 0)))

        return Panel(
            Padding(dashboard, (0, 1)),
            title="[bold]NoPush Review[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )

    # ------------------------------------------------------------------
    # Individual issue panels
    # ------------------------------------------------------------------

    def _render_comment(self, comment: ReviewComment) -> Panel:
        """Render a single review comment as a structured, styled panel."""
        sev_val = comment.severity.value
        style, dot, label = _SEVERITY_CONFIG.get(sev_val, ("", "●", sev_val.upper()))
        border = _SEVERITY_BORDER.get(sev_val, "white")

        # Severity badge
        severity_badge = Text()
        severity_badge.append(f"{dot} {label}", style=style)

        # Title
        title_text = Text(comment.title, style="bold")

        # File location
        location = Text()
        location.append("📁 ", style="dim")
        location.append(comment.file_path, style="cyan")
        if comment.line_number:
            location.append(f":{comment.line_number}", style="cyan dim")

        # Section: why this matters
        why_header = Text("Why this matters", style="bold dim")
        explanation_text = Text(comment.explanation)

        # Assemble the text block
        body = Group(
            severity_badge,
            Text(""),
            title_text,
            Text(""),
            location,
            Text(""),
            why_header,
            explanation_text,
        )

        panel_parts: list[RenderableType] = [body]

        # Code suggestion block
        if comment.suggestion:
            fix_header = Text()
            fix_header.append("💡 Suggested Fix", style="bold green")

            lexer = self._infer_lexer(comment.file_path)
            code_block = Syntax(
                comment.suggestion,
                lexer,
                theme="monokai",
                line_numbers=False,
                padding=(1, 1),
            )

            panel_parts.append(Text(""))
            panel_parts.append(Rule(style="dim"))
            panel_parts.append(Text(""))
            panel_parts.append(fix_header)
            panel_parts.append(code_block)

        return Panel(
            Group(*panel_parts),
            border_style=border,
            padding=(1, 2),
        )

    # ------------------------------------------------------------------
    # Empty state
    # ------------------------------------------------------------------

    def _render_clean(self, result: ReviewResult) -> None:
        """Render a celebratory panel when no issues are found."""
        # Stats row
        meta = Table.grid(padding=(0, 3))
        meta.add_column(style="dim")
        meta.add_column(style="bold dim")

        meta.add_row("Files Reviewed", str(result.files_reviewed))
        meta.add_row("Provider",       result.provider or "—")
        meta.add_row("Model",          result.model    or "—")

        content = Group(
            Text("✨  Excellent!", style="bold green"),
            Text(""),
            Text("No issues were found.", style="bold"),
            Text("Your code looks clean and well-structured.", style="dim"),
            Text(""),
            meta,
        )

        self.console.print(
            Panel(
                Padding(content, (0, 1)),
                title="[bold green]NoPush Review[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    def _render_footer(self, result: ReviewResult) -> None:
        """Render a clean footer rule after all comments."""
        from nopush.review.models import Severity

        counts = result.count_by_severity()
        critical = counts.get(Severity.CRITICAL, 0)

        self.console.print(Rule(style="dim"))
        self.console.print()

        # Centre-aligned summary line
        summary = Text(justify="center")
        summary.append("Review Complete", style="bold")
        summary.append(f"   {result.total_issues} issue(s) found", style="")

        self.console.print(Align.center(summary))

        if critical > 0:
            attention = Text(justify="center")
            attention.append(
                f"{critical} critical issue(s) require immediate attention.",
                style="bold red",
            )
            self.console.print(Align.center(attention))

        self.console.print()
        self.console.print(Rule(style="dim"))
        self.console.print()

    # ------------------------------------------------------------------
    # Clipboard
    # ------------------------------------------------------------------

    def _maybe_copy_to_clipboard(self, result: ReviewResult) -> None:
        """Attempt to copy a plain-text issue summary to the system clipboard.

        Tries the following commands in order, stopping at the first one found:
        - ``xclip`` (Linux/X11)
        - ``xsel`` (Linux/X11)
        - ``wl-copy`` (Linux/Wayland)
        - ``pbcopy`` (macOS)
        - ``clip`` (Windows)

        On success, prints a brief "copied" confirmation.
        On failure (tool not found or subprocess error), prints a dim hint.
        """
        text = _build_plaintext_summary(result)
        cmd = _detect_clipboard_cmd()

        if cmd is None:
            self.console.print(
                Align.center(
                    Text(
                        "📋  Install xclip / xsel / wl-copy to enable auto-copy",
                        style="dim",
                    )
                )
            )
            self.console.print()
            return

        try:
            proc = subprocess.run(
                cmd,
                input=text.encode(),
                check=True,
                capture_output=True,
            )
            _ = proc  # success
            self.console.print(
                Align.center(Text("📋  Review copied to clipboard", style="dim cyan"))
            )
        except (subprocess.CalledProcessError, OSError):
            self.console.print(
                Align.center(
                    Text("📋  Could not copy to clipboard", style="dim")
                )
            )
        finally:
            self.console.print()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _infer_lexer(file_path: str) -> str:
        """Infer a Rich Syntax lexer name from the file path."""
        from pathlib import PurePosixPath

        suffix = PurePosixPath(file_path).suffix.lower()
        ext_map: dict[str, str] = {
            ".py":    "python",
            ".js":    "javascript",
            ".ts":    "typescript",
            ".jsx":   "jsx",
            ".tsx":   "tsx",
            ".java":  "java",
            ".go":    "go",
            ".rs":    "rust",
            ".rb":    "ruby",
            ".php":   "php",
            ".c":     "c",
            ".cpp":   "cpp",
            ".h":     "c",
            ".hpp":   "cpp",
            ".cs":    "csharp",
            ".swift": "swift",
            ".sh":    "bash",
            ".yaml":  "yaml",
            ".yml":   "yaml",
            ".json":  "json",
            ".toml":  "toml",
            ".html":  "html",
            ".css":   "css",
            ".sql":   "sql",
            ".kt":    "kotlin",
            ".scala": "scala",
            ".dart":  "dart",
        }
        return ext_map.get(suffix, "text")


# ---------------------------------------------------------------------------
# Module-level clipboard helpers
# ---------------------------------------------------------------------------


def _detect_clipboard_cmd() -> list[str] | None:
    """Return the first available clipboard command for the current platform.

    Checks (in order):
    - ``xclip`` — X11 (Linux)
    - ``xsel``  — X11 (Linux)
    - ``wl-copy`` — Wayland (Linux)
    - ``pbcopy`` — macOS
    - ``clip``   — Windows

    Returns ``None`` when no suitable tool is found.
    """
    candidates: list[list[str]] = [
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["wl-copy"],
        ["pbcopy"],
        ["clip"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]) is not None:
            return cmd
    return None


def _build_plaintext_summary(result: "ReviewResult") -> str:
    """Serialise *result* as human-readable plain text suitable for pasting.

    Each issue is rendered as a labelled block::

        [CRITICAL] Title (file.py:42)
        Why this matters:
        <explanation>

        Suggested Fix:
        <suggestion>

        ──────────────────────────────────────────

    The output ends with a short summary line.
    """
    lines: list[str] = []
    sep = "─" * 60

    lines.append(f"NoPush Review — {result.total_issues} issue(s) found")
    lines.append(f"Provider: {result.provider or '—'}  |  Model: {result.model or '—'}")
    lines.append(sep)
    lines.append("")

    for comment in result.comments:
        sev = comment.severity.value.upper()
        loc = comment.file_path
        if comment.line_number:
            loc += f":{comment.line_number}"

        lines.append(f"[{sev}] {comment.title}")
        lines.append(f"📁 {loc}")
        lines.append("")
        lines.append("Why this matters:")
        lines.append(comment.explanation)

        if comment.suggestion:
            lines.append("")
            lines.append("Suggested Fix:")
            lines.append(comment.suggestion)

        lines.append("")
        lines.append(sep)
        lines.append("")

    return "\n".join(lines)
