"""Tests for the OpenAI provider."""

from __future__ import annotations

import pytest

from nopush.config.schema import NoPushConfig
from nopush.providers.base import ProviderAuthError
from nopush.providers.openai import OpenAIProvider
from nopush.providers.registry import get_provider, list_providers


class TestProviderRegistry:
    """Tests for provider discovery and instantiation."""

    def test_list_providers(self) -> None:
        """list_providers should return known provider names."""
        providers = list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "gemini" in providers

    def test_get_unknown_provider(self) -> None:
        """Requesting an unknown provider should raise ProviderError."""
        from nopush.providers.base import ProviderError

        config = NoPushConfig(provider="nonexistent", api_key="key")
        with pytest.raises(ProviderError, match="Unknown provider"):
            get_provider(config)

    def test_get_openai_provider(self) -> None:
        """OpenAI provider should be instantiable with a key."""
        config = NoPushConfig(provider="openai", api_key="sk-test-123")
        provider = get_provider(config)
        assert isinstance(provider, OpenAIProvider)


class TestOpenAIProvider:
    """Tests for the OpenAI provider (unit-level, no API calls)."""

    def test_missing_api_key_raises(self) -> None:
        """Instantiating without an API key should raise ProviderAuthError."""
        config = NoPushConfig(provider="openai", api_key="")
        with pytest.raises(ProviderAuthError):
            OpenAIProvider(config)

    def test_instantiation_with_key(self) -> None:
        """Should instantiate successfully with a key."""
        config = NoPushConfig(provider="openai", api_key="sk-test-123")
        provider = OpenAIProvider(config)
        assert provider._model == "gpt-4.1"
