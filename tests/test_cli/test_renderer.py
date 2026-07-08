"""Comprehensive tests for the ReviewRenderer.

Covers:
- Rendering a review with issues (summary, comments, footer)
- Rendering a clean review (no issues)
- Severity styling and colour-coding
- Code suggestion syntax highlighting
- Multiple comments with different severities
- Edge cases (null suggestion, single issue)
- Lexer inference from file paths
"""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from nopush.cli.renderer import ReviewRenderer
from nopush.review.models import ReviewComment, ReviewResult, Severity

# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_renderer() -> tuple[ReviewRenderer, StringIO]:
    """Create a renderer with a captured output stream."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    renderer = ReviewRenderer(console=console)
    return renderer, buffer


def _make_comment(
    severity: Severity = Severity.WARNING,
    file_path: str = "app/utils.py",
    line_number: int = 11,
    title: str = "Test issue",
    explanation: str = "This is a test issue.",
    suggestion: str | None = "    return str(data).strip()",
) -> ReviewComment:
    """Create a review comment with configurable fields."""
    return ReviewComment(
        severity=severity,
        file_path=file_path,
        line_number=line_number,
        title=title,
        explanation=explanation,
        suggestion=suggestion,
    )


def _make_result(
    comments: list[ReviewComment] | None = None,
    files_reviewed: int = 1,
    model: str = "gpt-4.1",
    provider: str = "openai",
) -> ReviewResult:
    """Create a review result."""
    return ReviewResult(
        comments=comments or [],
        files_reviewed=files_reviewed,
        model=model,
        provider=provider,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Clean review (no issues)
# ═══════════════════════════════════════════════════════════════════════════


class TestRenderClean:
    """Test rendering when no issues are found."""

    def test_clean_review_shows_congratulations(self) -> None:
        """A clean review should display a congratulatory message."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[], files_reviewed=3)

        renderer.render(result)
        output = buffer.getvalue()

        assert "No issues were found" in output

    def test_clean_review_shows_file_count(self) -> None:
        """The clean review should mention how many files were reviewed."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[], files_reviewed=5)

        renderer.render(result)
        output = buffer.getvalue()

        assert "5" in output

    def test_clean_review_shows_provider_info(self) -> None:
        """The clean review should show provider and model info."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[], provider="gemini", model="gemini-2.5-pro")

        renderer.render(result)
        output = buffer.getvalue()

        assert "gemini" in output
        assert "gemini-2.5-pro" in output


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Rendering with issues
# ═══════════════════════════════════════════════════════════════════════════


class TestRenderWithIssues:
    """Test rendering when issues are found."""

    def test_single_issue_rendered(self) -> None:
        """A single issue should be rendered with its details."""
        renderer, buffer = _make_renderer()
        comment = _make_comment(
            severity=Severity.WARNING,
            title="Potential TypeError",
            file_path="app/utils.py",
            line_number=11,
        )
        result = _make_result(comments=[comment])

        renderer.render(result)
        output = buffer.getvalue()

        assert "Potential TypeError" in output
        assert "app/utils.py" in output
        assert "11" in output

    def test_summary_shows_total_issues(self) -> None:
        """The summary should show the total issue count."""
        renderer, buffer = _make_renderer()
        comments = [
            _make_comment(severity=Severity.CRITICAL, title="Bug 1"),
            _make_comment(severity=Severity.WARNING, title="Bug 2"),
        ]
        result = _make_result(comments=comments, files_reviewed=2)

        renderer.render(result)
        output = buffer.getvalue()

        assert "2" in output  # total issues
        assert "NoPush Review" in output

    def test_summary_shows_files_reviewed(self) -> None:
        """The summary should show how many files were reviewed."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[_make_comment()], files_reviewed=7)

        renderer.render(result)
        output = buffer.getvalue()

        assert "7" in output

    def test_critical_issue_warning_in_footer(self) -> None:
        """Critical issues should trigger a footer warning."""
        renderer, buffer = _make_renderer()
        comment = _make_comment(severity=Severity.CRITICAL, title="Security bug")
        result = _make_result(comments=[comment])

        renderer.render(result)
        output = buffer.getvalue()

        assert "critical" in output.lower()
        assert "immediate attention" in output.lower() or "require" in output.lower()

    def test_multiple_severities_rendered(self) -> None:
        """Comments of different severities should all be rendered."""
        renderer, buffer = _make_renderer()
        comments = [
            _make_comment(severity=Severity.CRITICAL, title="Critical Bug"),
            _make_comment(severity=Severity.WARNING, title="Performance Issue"),
            _make_comment(severity=Severity.SUGGESTION, title="Better Pattern"),
            _make_comment(severity=Severity.NITPICK, title="Naming Convention"),
        ]
        result = _make_result(comments=comments, files_reviewed=1)

        renderer.render(result)
        output = buffer.getvalue()

        assert "Critical Bug" in output
        assert "Performance Issue" in output
        assert "Better Pattern" in output
        assert "Naming Convention" in output

    def test_explanation_rendered(self) -> None:
        """The explanation text should appear in the output."""
        renderer, buffer = _make_renderer()
        comment = _make_comment(explanation="The variable `data` could be None, causing a crash.")
        result = _make_result(comments=[comment])

        renderer.render(result)
        output = buffer.getvalue()

        assert "could be None" in output

    def test_suggestion_rendered(self) -> None:
        """Code suggestions should appear in the output."""
        renderer, buffer = _make_renderer()
        comment = _make_comment(suggestion="    return str(data).strip()")
        result = _make_result(comments=[comment])

        renderer.render(result)
        output = buffer.getvalue()

        assert "Suggested Fix" in output

    def test_null_suggestion_no_crash(self) -> None:
        """A comment with no suggestion should render without crashing."""
        renderer, buffer = _make_renderer()
        comment = _make_comment(suggestion=None)
        result = _make_result(comments=[comment])

        renderer.render(result)
        output = buffer.getvalue()

        assert "Test issue" in output
        # Should NOT show "Suggested Fix" when suggestion is None
        assert "Suggested Fix" not in output

    def test_provider_and_model_in_summary(self) -> None:
        """Provider and model should appear in the summary."""
        renderer, buffer = _make_renderer()
        result = _make_result(
            comments=[_make_comment()],
            provider="openai",
            model="gpt-4.1",
        )

        renderer.render(result)
        output = buffer.getvalue()

        assert "openai" in output
        assert "gpt-4.1" in output


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Lexer inference
# ═══════════════════════════════════════════════════════════════════════════


class TestLexerInference:
    """Test the _infer_lexer helper method."""

    def test_python_file(self) -> None:
        """Python files should use the python lexer."""
        assert ReviewRenderer._infer_lexer("app/utils.py") == "python"

    def test_javascript_file(self) -> None:
        """JavaScript files should use the javascript lexer."""
        assert ReviewRenderer._infer_lexer("src/index.js") == "javascript"

    def test_typescript_file(self) -> None:
        """TypeScript files should use the typescript lexer."""
        assert ReviewRenderer._infer_lexer("src/app.ts") == "typescript"

    def test_go_file(self) -> None:
        """Go files should use the go lexer."""
        assert ReviewRenderer._infer_lexer("main.go") == "go"

    def test_rust_file(self) -> None:
        """Rust files should use the rust lexer."""
        assert ReviewRenderer._infer_lexer("src/lib.rs") == "rust"

    def test_unknown_extension(self) -> None:
        """Unknown extensions should fall back to 'text'."""
        assert ReviewRenderer._infer_lexer("README.txt") == "text"

    def test_no_extension(self) -> None:
        """Files without extensions should fall back to 'text'."""
        assert ReviewRenderer._infer_lexer("Makefile") == "text"

    def test_yaml_file(self) -> None:
        """YAML files should use the yaml lexer."""
        assert ReviewRenderer._infer_lexer("config.yaml") == "yaml"
        assert ReviewRenderer._infer_lexer("config.yml") == "yaml"


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Severity styling
# ═══════════════════════════════════════════════════════════════════════════


class TestSeverityStyling:
    """Test that severity emojis appear in the output."""

    def test_critical_emoji(self) -> None:
        """Critical issues should have the red circle emoji."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[_make_comment(severity=Severity.CRITICAL)])
        renderer.render(result)
        output = buffer.getvalue()
        assert "🔴" in output

    def test_warning_emoji(self) -> None:
        """Warning issues should have the yellow circle emoji."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[_make_comment(severity=Severity.WARNING)])
        renderer.render(result)
        output = buffer.getvalue()
        assert "🟡" in output

    def test_suggestion_emoji(self) -> None:
        """Suggestions should have the blue circle emoji."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[_make_comment(severity=Severity.SUGGESTION)])
        renderer.render(result)
        output = buffer.getvalue()
        assert "🔵" in output

    def test_nitpick_emoji(self) -> None:
        """Nitpicks should have the white circle emoji."""
        renderer, buffer = _make_renderer()
        result = _make_result(comments=[_make_comment(severity=Severity.NITPICK)])
        renderer.render(result)
        output = buffer.getvalue()
        assert "⚪" in output
