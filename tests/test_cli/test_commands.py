"""Tests for the NoPush CLI commands.

Covers:
- Top-level app (help, version)
- Init command registration
- Review command registration and error handling
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from nopush.cli.app import app

runner = CliRunner()


class TestCLIApp:
    """Test the top-level CLI application."""

    def test_help(self) -> None:
        """``nopush --help`` should exit 0 and show usage."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "nopush" in result.output.lower()

    def test_version(self) -> None:
        """``nopush --version`` should print the version."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_init_help(self) -> None:
        """``nopush init --help`` should show init-specific help."""
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "configure" in result.output.lower() or "api" in result.output.lower()

    def test_unknown_command(self) -> None:
        """An unknown command should produce an error."""
        result = runner.invoke(app, ["foobar"])
        assert result.exit_code != 0


class TestReviewCommand:
    """Tests for the review command."""

    def test_review_no_api_key(self) -> None:
        """Review without an API key should exit with an error."""
        from nopush.config.schema import NoPushConfig

        with patch(
            "nopush.config.manager.ConfigManager.load",
            return_value=NoPushConfig(),
        ):
            result = runner.invoke(app, ["review"])
            assert result.exit_code == 1
            assert "no api key" in result.output.lower() or "nopush init" in result.output.lower()

    def test_review_no_staged_changes(self) -> None:
        """Review with no staged changes should exit gracefully."""
        from nopush.config.schema import NoPushConfig

        with patch(
            "nopush.config.manager.ConfigManager.load",
            return_value=NoPushConfig(api_key="sk-test"),
        ), patch(
            "nopush.git.diff_parser.get_staged_diff",
            return_value="",
        ):
            result = runner.invoke(app, ["review"])
            assert result.exit_code == 0
            assert "no staged changes" in result.output.lower()

    def test_review_git_error(self) -> None:
        """Review with git error should exit with error code."""
        from nopush.config.schema import NoPushConfig

        with patch(
            "nopush.config.manager.ConfigManager.load",
            return_value=NoPushConfig(api_key="sk-test"),
        ), patch(
            "nopush.git.diff_parser.get_staged_diff",
            side_effect=RuntimeError("not a git repository"),
        ):
            result = runner.invoke(app, ["review"])
            assert result.exit_code == 1
            assert "git error" in result.output.lower()

    def test_review_invalid_depth(self) -> None:
        """Review with invalid depth should exit with error."""
        from nopush.config.schema import NoPushConfig

        with patch(
            "nopush.config.manager.ConfigManager.load",
            return_value=NoPushConfig(api_key="sk-test"),
        ):
            result = runner.invoke(app, ["review", "--depth", "invalid"])
            assert result.exit_code == 1
            assert "invalid" in result.output.lower()

    def test_review_help(self) -> None:
        """``nopush review --help`` should show review-specific options."""
        result = runner.invoke(app, ["review", "--help"])
        assert result.exit_code == 0
        assert "--depth" in result.output
        assert "--provider" in result.output
        assert "--model" in result.output
