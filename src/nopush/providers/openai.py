"""OpenAI / Azure OpenAI provider implementation.

Uses ``httpx`` directly (no ``openai`` SDK dependency) to call the
`Chat Completions <https://platform.openai.com/docs/api-reference/chat>`_ API.
Supports exponential backoff on rate-limit and timeout errors.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

from nopush.providers.base import (
    LLMProvider,
    Message,
    ProviderAuthError,
    ProviderError,
    ProviderNetworkError,
    ProviderRateLimitError,
)

if TYPE_CHECKING:
    from nopush.config.schema import NoPushConfig

logger = logging.getLogger(__name__)

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

    def __init__(self, config: NoPushConfig) -> None:
        if not config.api_key:
            msg = (
                "OpenAI API key is not configured. "
                "Run 'nopush init' or set the NOPUSH_API_KEY environment variable."
            )
            raise ProviderAuthError(msg)

        self._api_key = config.api_key
        self._model = config.model
        self._base_url = (config.api_base or _DEFAULT_BASE_URL).rstrip("/")
        self._timeout = config.timeout

    def complete(self, messages: list[Message]) -> str:
        """Send a chat completion request to the OpenAI API.

        Implements exponential backoff for rate-limit (429) and timeout
        responses.
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
                logger.debug(
                    "OpenAI request attempt %d/%d to %s (model=%s)",
                    attempt + 1,
                    _MAX_RETRIES,
                    self._base_url,
                    self._model,
                )
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

                if response.status_code == 403:
                    msg = (
                        "OpenAI access denied (403). Your API key may lack "
                        "permissions for this model or endpoint."
                    )
                    raise ProviderAuthError(msg)

                if response.status_code == 429:
                    last_error = ProviderRateLimitError(
                        "Rate limit exceeded. Retrying…"
                    )
                    logger.warning(
                        "Rate limited (429), backing off %.1fs…", backoff
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                if response.status_code >= 500:
                    last_error = ProviderError(
                        f"OpenAI server error ({response.status_code}). Retrying…"
                    )
                    logger.warning(
                        "Server error %d, backing off %.1fs…",
                        response.status_code,
                        backoff,
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                # Other HTTP errors — don't retry
                msg = (
                    f"OpenAI API returned {response.status_code}: "
                    f"{response.text[:500]}"
                )
                raise ProviderError(msg)

            except httpx.TimeoutException as exc:
                last_error = ProviderNetworkError(
                    f"Request timed out after {self._timeout}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})."
                )
                logger.warning(str(last_error))
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise ProviderNetworkError(str(last_error)) from exc

            except httpx.HTTPError as exc:
                msg = f"Network error communicating with OpenAI: {exc}"
                raise ProviderNetworkError(msg) from exc

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
