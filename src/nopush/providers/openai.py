"""OpenAI / Azure OpenAI provider implementation."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import httpx

from nopush.providers.base import (
    LLMProvider,
    Message,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
)

if TYPE_CHECKING:
    from nopush.config.schema import NoPushConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0


class OpenAIProvider(LLMProvider):
    """LLM provider for the OpenAI Chat Completions API.

    Supports both OpenAI and Azure OpenAI via a configurable base URL.
    Uses ``httpx`` directly to avoid a dependency on the ``openai`` SDK.
    """

    def __init__(self, config: "NoPushConfig") -> None:
        if not config.api_key:
            msg = (
                "OpenAI API key is not configured. "
                "Run 'nopush init' or set the NOPUSH_API_KEY environment variable."
            )
            raise ProviderAuthError(msg)

        self._api_key = config.api_key
        self._model = config.model
        self._base_url = _DEFAULT_BASE_URL
        self._timeout = config.timeout

    def complete(self, messages: list[Message]) -> str:
        """Send a chat completion request to the OpenAI API.

        Implements exponential backoff for rate-limit (429) responses.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": 0.2,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(_MAX_RETRIES):
            try:
                response = httpx.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )

                if response.status_code == 200:
                    return self._extract_content(response.json())

                if response.status_code == 401:
                    msg = "OpenAI authentication failed. Check your API key."
                    raise ProviderAuthError(msg)

                if response.status_code == 429:
                    last_error = ProviderRateLimitError(
                        "Rate limit exceeded. Retrying…"
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                # Other HTTP errors
                msg = (
                    f"OpenAI API returned {response.status_code}: "
                    f"{response.text[:500]}"
                )
                raise ProviderError(msg)

            except httpx.TimeoutException as exc:
                last_error = ProviderError(
                    f"Request timed out after {self._timeout}s (attempt {attempt + 1}/{_MAX_RETRIES})."
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise ProviderError(str(last_error)) from exc

            except httpx.HTTPError as exc:
                msg = f"Network error communicating with OpenAI: {exc}"
                raise ProviderError(msg) from exc

        # Exhausted retries
        raise last_error or ProviderError("Failed after multiple retries.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_content(response_json: dict[str, Any]) -> str:
        """Extract the assistant message content from the API response."""
        try:
            return str(response_json["choices"][0]["message"]["content"])
        except (KeyError, IndexError) as exc:
            msg = f"Unexpected OpenAI response format: {response_json}"
            raise ProviderError(msg) from exc
