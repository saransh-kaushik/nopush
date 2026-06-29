"""Tests for the NoPush CLI commands."""

from __future__ import annotations

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

    def test_init_command_exists(self) -> None:
        """``nopush init`` should be a registered command."""
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0

    def test_review_command_exists(self) -> None:
        """``nopush review`` should be a registered command."""
        result = runner.invoke(app, ["review"])
        assert result.exit_code == 0

    def test_unknown_command(self) -> None:
        """An unknown command should produce an error."""
        result = runner.invoke(app, ["foobar"])
        assert result.exit_code != 0
