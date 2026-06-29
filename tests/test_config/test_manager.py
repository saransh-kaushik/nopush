"""Tests for the ConfigManager."""

from __future__ import annotations

from nopush.config.schema import NoPushConfig


class TestNoPushConfig:
    """Test the NoPushConfig Pydantic model."""

    def test_defaults(self) -> None:
        """Config should have sensible defaults."""
        config = NoPushConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4.1"
        assert config.review_depth == "standard"
        assert config.max_files == 50
        assert config.ignore == []

    def test_custom_values(self) -> None:
        """Config should accept custom values."""
        config = NoPushConfig(
            provider="anthropic",
            model="claude-3",
            review_depth="thorough",
            ignore=["*.md", "tests/"],
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3"
        assert config.review_depth == "thorough"
        assert config.ignore == ["*.md", "tests/"]

    def test_serialization_round_trip(self) -> None:
        """Config should survive a dump/load round trip."""
        original = NoPushConfig(provider="gemini", model="gemini-pro")
        data = original.model_dump()
        restored = NoPushConfig(**data)
        assert restored == original
