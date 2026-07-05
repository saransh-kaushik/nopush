"""Comprehensive tests for the LLM provider layer.

Covers:
- Provider registry (list, get, unknown)
- OpenAI provider:
  - Instantiation (with/without key, with api_base)
  - Successful completion (mocked)
  - Auth errors (401, 403)
  - Rate limiting with retry (429)
  - Server errors with retry (5xx)
  - Timeout handling
  - Network errors
  - Malformed response handling
- Gemini provider:
  - Instantiation (with/without key, model fallback)
  - Payload construction (system_instruction, user/model roles)
  - Successful completion (mocked)
  - Auth errors (401, 403)
  - Rate limiting with retry (429)
  - Server errors with retry (5xx)
  - Timeout handling
  - Network errors
  - Response extraction
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from nopush.config.schema import NoPushConfig
from nopush.providers.base import (
    Message,
    ProviderAuthError,
    ProviderError,
    ProviderNetworkError,
    ProviderRateLimitError,
)
from nopush.providers.gemini import GeminiProvider
from nopush.providers.openai import OpenAIProvider
from nopush.providers.registry import get_provider, list_providers


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _make_config(**kwargs: object) -> NoPushConfig:
    """Create a NoPushConfig with sensible defaults for testing."""
    defaults = {"provider": "openai", "api_key": "sk-test-key-123", "timeout": 30}
    defaults.update(kwargs)
    return NoPushConfig(**defaults)  # type: ignore[arg-type]


def _sample_messages() -> list[Message]:
    """Return a minimal message list for testing."""
    return [
        Message(role="system", content="You are a code reviewer."),
        Message(role="user", content="Review this code."),
    ]


def _mock_httpx_response(
    status_code: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = json_data or {}
    return resp


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Provider Registry
# ═══════════════════════════════════════════════════════════════════════════


class TestProviderRegistry:
    """Tests for provider discovery and instantiation."""

    def test_list_providers(self) -> None:
        """list_providers should return known provider names."""
        providers = list_providers()
        assert "openai" in providers
        assert "gemini" in providers

    def test_get_unknown_provider(self) -> None:
        """Requesting an unknown provider should raise ProviderError."""
        config = _make_config(provider="nonexistent")
        with pytest.raises(ProviderError, match="Unknown provider"):
            get_provider(config)

    def test_get_openai_provider(self) -> None:
        """OpenAI provider should be instantiable with a key."""
        config = _make_config(provider="openai")
        provider = get_provider(config)
        assert isinstance(provider, OpenAIProvider)

    def test_get_gemini_provider(self) -> None:
        """Gemini provider should be instantiable with a key."""
        config = _make_config(provider="gemini")
        provider = get_provider(config)
        assert isinstance(provider, GeminiProvider)

    def test_provider_name_case_insensitive(self) -> None:
        """Provider names should be case-insensitive."""
        config = _make_config(provider="OpenAI")
        provider = get_provider(config)
        assert isinstance(provider, OpenAIProvider)


# ═══════════════════════════════════════════════════════════════════════════
# Tests: OpenAI Provider — Instantiation
# ═══════════════════════════════════════════════════════════════════════════


class TestOpenAIInstantiation:
    """Tests for OpenAI provider construction."""

    def test_missing_api_key_raises(self) -> None:
        """Instantiating without an API key should raise ProviderAuthError."""
        config = _make_config(api_key="")
        with pytest.raises(ProviderAuthError):
            OpenAIProvider(config)

    def test_instantiation_with_key(self) -> None:
        """Should instantiate successfully with a key."""
        config = _make_config()
        provider = OpenAIProvider(config)
        assert provider._model == "gpt-4.1"

    def test_custom_api_base(self) -> None:
        """Custom api_base should be used instead of default."""
        config = _make_config(api_base="https://custom.openai.azure.com/v1/")
        provider = OpenAIProvider(config)
        assert provider._base_url == "https://custom.openai.azure.com/v1"

    def test_default_api_base(self) -> None:
        """Without api_base, the default OpenAI URL should be used."""
        config = _make_config()
        provider = OpenAIProvider(config)
        assert "api.openai.com" in provider._base_url


# ═══════════════════════════════════════════════════════════════════════════
# Tests: OpenAI Provider — API interactions (mocked)
# ═══════════════════════════════════════════════════════════════════════════


class TestOpenAIComplete:
    """Tests for OpenAI complete() with mocked HTTP calls."""

    def test_successful_completion(self) -> None:
        """A 200 response should return the content."""
        config = _make_config()
        provider = OpenAIProvider(config)

        mock_resp = _mock_httpx_response(
            200,
            json_data={
                "choices": [{"message": {"content": "[]"}}]
            },
        )

        with patch("nopush.providers.openai.httpx.post", return_value=mock_resp):
            result = provider.complete(_sample_messages())

        assert result == "[]"

    def test_auth_error_401(self) -> None:
        """A 401 response should raise ProviderAuthError."""
        config = _make_config()
        provider = OpenAIProvider(config)
        mock_resp = _mock_httpx_response(401)

        with patch("nopush.providers.openai.httpx.post", return_value=mock_resp):
            with pytest.raises(ProviderAuthError, match="authentication failed"):
                provider.complete(_sample_messages())

    def test_auth_error_403(self) -> None:
        """A 403 response should raise ProviderAuthError."""
        config = _make_config()
        provider = OpenAIProvider(config)
        mock_resp = _mock_httpx_response(403)

        with patch("nopush.providers.openai.httpx.post", return_value=mock_resp):
            with pytest.raises(ProviderAuthError, match="access denied"):
                provider.complete(_sample_messages())

    @patch("nopush.providers.openai.time.sleep")
    def test_rate_limit_retries(self, mock_sleep: MagicMock) -> None:
        """429 responses should trigger retries with backoff."""
        config = _make_config()
        provider = OpenAIProvider(config)

        rate_limited = _mock_httpx_response(429)
        success = _mock_httpx_response(
            200, json_data={"choices": [{"message": {"content": "[]"}}]}
        )

        with patch(
            "nopush.providers.openai.httpx.post",
            side_effect=[rate_limited, success],
        ):
            result = provider.complete(_sample_messages())

        assert result == "[]"
        mock_sleep.assert_called_once()

    @patch("nopush.providers.openai.time.sleep")
    def test_rate_limit_exhausted(self, mock_sleep: MagicMock) -> None:
        """Exhausted retries after 429 should raise ProviderRateLimitError."""
        config = _make_config()
        provider = OpenAIProvider(config)
        rate_limited = _mock_httpx_response(429)

        with patch(
            "nopush.providers.openai.httpx.post",
            return_value=rate_limited,
        ):
            with pytest.raises(ProviderRateLimitError):
                provider.complete(_sample_messages())

    @patch("nopush.providers.openai.time.sleep")
    def test_server_error_retries(self, mock_sleep: MagicMock) -> None:
        """5xx responses should trigger retries."""
        config = _make_config()
        provider = OpenAIProvider(config)

        server_error = _mock_httpx_response(500)
        success = _mock_httpx_response(
            200, json_data={"choices": [{"message": {"content": "[]"}}]}
        )

        with patch(
            "nopush.providers.openai.httpx.post",
            side_effect=[server_error, success],
        ):
            result = provider.complete(_sample_messages())

        assert result == "[]"

    def test_timeout_raises_network_error(self) -> None:
        """Timeout should raise ProviderNetworkError."""
        config = _make_config()
        provider = OpenAIProvider(config)

        with patch(
            "nopush.providers.openai.httpx.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with patch("nopush.providers.openai.time.sleep"):
                with pytest.raises(ProviderNetworkError, match="timed out"):
                    provider.complete(_sample_messages())

    def test_network_error_raises(self) -> None:
        """Network-level errors should raise ProviderNetworkError."""
        config = _make_config()
        provider = OpenAIProvider(config)

        with patch(
            "nopush.providers.openai.httpx.post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(ProviderNetworkError, match="Network error"):
                provider.complete(_sample_messages())

    def test_malformed_response(self) -> None:
        """A response missing expected fields should raise ProviderError."""
        config = _make_config()
        provider = OpenAIProvider(config)
        mock_resp = _mock_httpx_response(200, json_data={"unexpected": "format"})

        with patch("nopush.providers.openai.httpx.post", return_value=mock_resp):
            with pytest.raises(ProviderError, match="Unexpected"):
                provider.complete(_sample_messages())

    def test_other_http_error_no_retry(self) -> None:
        """Non-retryable HTTP errors (e.g. 400) should not be retried."""
        config = _make_config()
        provider = OpenAIProvider(config)
        mock_resp = _mock_httpx_response(400, text="Bad Request")

        with patch("nopush.providers.openai.httpx.post", return_value=mock_resp) as mock_post:
            with pytest.raises(ProviderError, match="400"):
                provider.complete(_sample_messages())
        # Should be called only once (no retry)
        assert mock_post.call_count == 1


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Gemini Provider — Instantiation
# ═══════════════════════════════════════════════════════════════════════════


class TestGeminiInstantiation:
    """Tests for Gemini provider construction."""

    def test_missing_api_key_raises(self) -> None:
        """Instantiating without an API key should raise ProviderAuthError."""
        config = _make_config(provider="gemini", api_key="")
        with pytest.raises(ProviderAuthError):
            GeminiProvider(config)

    def test_instantiation_with_key(self) -> None:
        """Should instantiate successfully with a key."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)
        # Should fall back from gpt-4.1 to gemini-2.5-flash
        assert "gemini" in provider._model

    def test_explicit_gemini_model_preserved(self) -> None:
        """If a Gemini model is explicitly set, it should be used."""
        config = _make_config(provider="gemini", model="gemini-2.5-pro")
        provider = GeminiProvider(config)
        assert provider._model == "gemini-2.5-pro"

    def test_openai_model_falls_back(self) -> None:
        """If the model is the OpenAI default (gpt-4.1), fall back to Gemini default."""
        config = _make_config(provider="gemini", model="gpt-4.1")
        provider = GeminiProvider(config)
        assert provider._model != "gpt-4.1"
        assert "gemini" in provider._model

    def test_custom_api_base(self) -> None:
        """Custom api_base should be used."""
        config = _make_config(
            provider="gemini",
            api_base="https://custom.googleapis.com/v1/",
        )
        provider = GeminiProvider(config)
        assert provider._base_url == "https://custom.googleapis.com/v1"


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Gemini Provider — Payload construction
# ═══════════════════════════════════════════════════════════════════════════


class TestGeminiPayload:
    """Tests for Gemini payload construction."""

    def test_system_instruction_extracted(self) -> None:
        """System messages should be placed in system_instruction."""
        payload = GeminiProvider._build_payload(_sample_messages())
        assert "system_instruction" in payload
        parts = payload["system_instruction"]["parts"]
        assert len(parts) == 1
        assert "code reviewer" in parts[0]["text"]

    def test_user_messages_in_contents(self) -> None:
        """User messages should appear in contents with role 'user'."""
        payload = GeminiProvider._build_payload(_sample_messages())
        contents = payload["contents"]
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "Review this code."

    def test_assistant_mapped_to_model(self) -> None:
        """Assistant messages should be mapped to role 'model'."""
        messages = [
            Message(role="system", content="System."),
            Message(role="user", content="Hello."),
            Message(role="assistant", content="Hi there."),
        ]
        payload = GeminiProvider._build_payload(messages)
        model_msg = [c for c in payload["contents"] if c["role"] == "model"]
        assert len(model_msg) == 1
        assert model_msg[0]["parts"][0]["text"] == "Hi there."

    def test_no_system_messages(self) -> None:
        """If there are no system messages, system_instruction should be absent."""
        messages = [Message(role="user", content="Hello.")]
        payload = GeminiProvider._build_payload(messages)
        assert "system_instruction" not in payload

    def test_response_mime_type(self) -> None:
        """The payload should request JSON response format."""
        payload = GeminiProvider._build_payload(_sample_messages())
        assert payload["generationConfig"]["responseMimeType"] == "application/json"

    def test_temperature_set(self) -> None:
        """Temperature should be set to 0.2."""
        payload = GeminiProvider._build_payload(_sample_messages())
        assert payload["generationConfig"]["temperature"] == 0.2


# ═══════════════════════════════════════════════════════════════════════════
# Tests: Gemini Provider — API interactions (mocked)
# ═══════════════════════════════════════════════════════════════════════════


class TestGeminiComplete:
    """Tests for Gemini complete() with mocked HTTP calls."""

    def test_successful_completion(self) -> None:
        """A 200 response should return the extracted text."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)

        mock_resp = _mock_httpx_response(
            200,
            json_data={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "[]"}],
                            "role": "model",
                        }
                    }
                ]
            },
        )

        with patch("nopush.providers.gemini.httpx.post", return_value=mock_resp):
            result = provider.complete(_sample_messages())

        assert result == "[]"

    def test_multi_part_response(self) -> None:
        """Multiple text parts should be concatenated."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)

        mock_resp = _mock_httpx_response(
            200,
            json_data={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Part 1"},
                                {"text": "Part 2"},
                            ],
                            "role": "model",
                        }
                    }
                ]
            },
        )

        with patch("nopush.providers.gemini.httpx.post", return_value=mock_resp):
            result = provider.complete(_sample_messages())

        assert result == "Part 1\nPart 2"

    def test_auth_error_401(self) -> None:
        """A 401 response should raise ProviderAuthError."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)
        mock_resp = _mock_httpx_response(
            401,
            json_data={"error": {"message": "API key not valid"}},
        )

        with patch("nopush.providers.gemini.httpx.post", return_value=mock_resp):
            with pytest.raises(ProviderAuthError, match="authentication failed"):
                provider.complete(_sample_messages())

    def test_auth_error_403(self) -> None:
        """A 403 response should raise ProviderAuthError."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)
        mock_resp = _mock_httpx_response(403, json_data={"error": {"message": "Forbidden"}})

        with patch("nopush.providers.gemini.httpx.post", return_value=mock_resp):
            with pytest.raises(ProviderAuthError, match="authentication failed"):
                provider.complete(_sample_messages())

    @patch("nopush.providers.gemini.time.sleep")
    def test_rate_limit_retries(self, mock_sleep: MagicMock) -> None:
        """429 responses should trigger retries."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)

        rate_limited = _mock_httpx_response(429)
        success = _mock_httpx_response(
            200,
            json_data={
                "candidates": [
                    {"content": {"parts": [{"text": "[]"}], "role": "model"}}
                ]
            },
        )

        with patch(
            "nopush.providers.gemini.httpx.post",
            side_effect=[rate_limited, success],
        ):
            result = provider.complete(_sample_messages())

        assert result == "[]"
        mock_sleep.assert_called_once()

    @patch("nopush.providers.gemini.time.sleep")
    def test_rate_limit_exhausted(self, mock_sleep: MagicMock) -> None:
        """Exhausted retries should raise ProviderRateLimitError."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)
        rate_limited = _mock_httpx_response(429)

        with patch(
            "nopush.providers.gemini.httpx.post",
            return_value=rate_limited,
        ):
            with pytest.raises(ProviderRateLimitError):
                provider.complete(_sample_messages())

    @patch("nopush.providers.gemini.time.sleep")
    def test_server_error_retries(self, mock_sleep: MagicMock) -> None:
        """5xx responses should trigger retries."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)

        server_error = _mock_httpx_response(503)
        success = _mock_httpx_response(
            200,
            json_data={
                "candidates": [
                    {"content": {"parts": [{"text": "ok"}], "role": "model"}}
                ]
            },
        )

        with patch(
            "nopush.providers.gemini.httpx.post",
            side_effect=[server_error, success],
        ):
            result = provider.complete(_sample_messages())

        assert result == "ok"

    def test_timeout_raises_network_error(self) -> None:
        """Timeout should raise ProviderNetworkError."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)

        with patch(
            "nopush.providers.gemini.httpx.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with patch("nopush.providers.gemini.time.sleep"):
                with pytest.raises(ProviderNetworkError, match="timed out"):
                    provider.complete(_sample_messages())

    def test_network_error_raises(self) -> None:
        """Network-level errors should raise ProviderNetworkError."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)

        with patch(
            "nopush.providers.gemini.httpx.post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(ProviderNetworkError, match="Network error"):
                provider.complete(_sample_messages())

    def test_malformed_response(self) -> None:
        """A response missing expected fields should raise ProviderError."""
        config = _make_config(provider="gemini")
        provider = GeminiProvider(config)
        mock_resp = _mock_httpx_response(200, json_data={"unexpected": "format"})

        with patch("nopush.providers.gemini.httpx.post", return_value=mock_resp):
            with pytest.raises(ProviderError, match="Unexpected"):
                provider.complete(_sample_messages())

    def test_api_key_in_url(self) -> None:
        """The API key should be passed as a query parameter."""
        config = _make_config(provider="gemini", api_key="test-gemini-key")
        provider = GeminiProvider(config)

        mock_resp = _mock_httpx_response(
            200,
            json_data={
                "candidates": [
                    {"content": {"parts": [{"text": "[]"}], "role": "model"}}
                ]
            },
        )

        with patch("nopush.providers.gemini.httpx.post", return_value=mock_resp) as mock_post:
            provider.complete(_sample_messages())

        url = mock_post.call_args[0][0]
        assert "key=test-gemini-key" in url
