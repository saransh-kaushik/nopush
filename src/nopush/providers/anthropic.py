"""Anthropic Claude provider implementation.

Uses ``httpx`` directly (no ``anthropic`` SDK dependency) to call the
`Messages API <https://docs.anthropic.com/en/api/messages>`_.
Supports exponential backoff on rate-limit and server errors.

Anthropic's Messages API differs from OpenAI's Chat Completions:

- System messages are passed as a top-level ``system`` string (not in the
  ``messages`` list).
- Roles are ``user`` / ``assistant`` only (no ``system`` role in messages).
- The response lives under ``content[0].text`` for text blocks.
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

_DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
_ANTHROPIC_VERSION = "2023-06-01"
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0
_DEFAULT_MODEL = "claude-sonnet-5"
_DEFAULT_MAX_TOKENS = 8192


class AnthropicProvider(LLMProvider):
    """LLM provider for the Anthropic Claude Messages API.

    Uses ``httpx`` directly — no dependency on the ``anthropic`` SDK.
    Authenticates via the ``x-api-key`` header.
    """

    def __init__(self, config: NoPushConfig) -> None:
        if not config.api_key:
            msg = (
                "Anthropic API key is not configured. "
                "Run 'nopush init' or set the NOPUSH_API_KEY environment variable."
            )
            raise ProviderAuthError(msg)

        self._api_key = config.api_key
        self._model = config.model if config.model else _DEFAULT_MODEL
        self._base_url = (config.api_base or _DEFAULT_BASE_URL).rstrip("/")
        self._timeout = config.timeout

    def complete(self, messages: list[Message]) -> str:
        """Send a messages request to the Anthropic API.

        Implements exponential backoff for rate-limit (429) and server error
        (5xx) responses.
        """
        system_text, conversation = self._split_messages(messages)

        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": _DEFAULT_MAX_TOKENS,
            "messages": conversation,
        }
        if system_text:
            payload["system"] = system_text

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(_MAX_RETRIES):
            try:
                logger.debug(
                    "Anthropic request attempt %d/%d (model=%s)",
                    attempt + 1,
                    _MAX_RETRIES,
                    self._model,
                )
                response = httpx.post(
                    f"{self._base_url}/messages",
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )

                if response.status_code == 200:
                    return self._extract_content(response.json())

                if response.status_code == 401:
                    msg = "Anthropic authentication failed. Check your API key."
                    raise ProviderAuthError(msg)

                if response.status_code == 403:
                    msg = (
                        "Anthropic access denied (403). Your API key may lack "
                        "permissions for this model or endpoint."
                    )
                    raise ProviderAuthError(msg)

                if response.status_code == 429:
                    last_error = ProviderRateLimitError("Anthropic rate limit exceeded. Retrying…")
                    logger.warning("Rate limited (429), backing off %.1fs…", backoff)
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                if response.status_code >= 500:
                    last_error = ProviderError(
                        f"Anthropic server error ({response.status_code}). Retrying…"
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
                msg = f"Anthropic API returned {response.status_code}: {response.text[:500]}"
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
                msg = f"Network error communicating with Anthropic: {exc}"
                raise ProviderNetworkError(msg) from exc

        # Exhausted retries
        raise last_error or ProviderError("Failed after multiple retries.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _split_messages(
        messages: list[Message],
    ) -> tuple[str, list[dict[str, str]]]:
        """Separate system text from conversation messages.

        Anthropic requires the system prompt as a top-level field, while
        conversation turns use only ``user`` / ``assistant`` roles.

        Returns
        -------
        tuple[str, list[dict[str, str]]]
            ``(system_text, conversation_messages)`` where ``system_text`` may
            be empty if no system messages were present.
        """
        system_parts: list[str] = []
        conversation: list[dict[str, str]] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                conversation.append({"role": msg.role, "content": msg.content})

        return "\n\n".join(system_parts), conversation

    @staticmethod
    def _extract_content(response_json: dict[str, Any]) -> str:
        """Extract the assistant message text from the Anthropic API response.

        The response structure is:
        ``{ "content": [{ "type": "text", "text": "..." }], ... }``
        """
        try:
            content_blocks = response_json["content"]
            texts = [
                block["text"] for block in content_blocks if block.get("type") == "text"
            ]
            if not texts:
                msg = f"No text content in Anthropic response: {response_json}"
                raise ProviderError(msg)
            return "\n".join(texts)
        except (KeyError, TypeError) as exc:
            msg = f"Unexpected Anthropic response format: {response_json}"
            raise ProviderError(msg) from exc
