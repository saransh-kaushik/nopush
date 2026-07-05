"""Google Gemini provider implementation.

Uses ``httpx`` directly to call the
`Gemini REST API <https://ai.google.dev/api/rest>`_ (``generateContent``).
Supports exponential backoff on rate-limit and server errors.

The Gemini API uses a different message format from OpenAI:

- System instructions go in ``system_instruction``.
- User/assistant messages go in ``contents`` with ``role`` = ``user`` | ``model``.
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

_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_MAX_RETRIES = 3
_INITIAL_BACKOFF_SECONDS = 1.0
_DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider(LLMProvider):
    """LLM provider for the Google Gemini REST API.

    Uses ``httpx`` directly — no dependency on ``google-generativeai``.
    Authenticates via API key passed as a query parameter.
    """

    def __init__(self, config: NoPushConfig) -> None:
        if not config.api_key:
            msg = (
                "Gemini API key is not configured. "
                "Run 'nopush init' or set the NOPUSH_API_KEY environment variable."
            )
            raise ProviderAuthError(msg)

        self._api_key = config.api_key
        self._model = config.model if config.model != "gpt-4.1" else _DEFAULT_MODEL
        self._base_url = (config.api_base or _DEFAULT_BASE_URL).rstrip("/")
        self._timeout = config.timeout

    def complete(self, messages: list[Message]) -> str:
        """Send a generateContent request to the Gemini API.

        Implements exponential backoff for rate-limit (429) and server error
        (5xx) responses.
        """
        payload = self._build_payload(messages)
        url = (
            f"{self._base_url}/models/{self._model}:generateContent"
            f"?key={self._api_key}"
        )

        last_error: Exception | None = None
        backoff = _INITIAL_BACKOFF_SECONDS

        for attempt in range(_MAX_RETRIES):
            try:
                logger.debug(
                    "Gemini request attempt %d/%d (model=%s)",
                    attempt + 1,
                    _MAX_RETRIES,
                    self._model,
                )
                response = httpx.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=self._timeout,
                )

                if response.status_code == 200:
                    return self._extract_content(response.json())

                if response.status_code in (401, 403):
                    error_detail = self._extract_error_message(response)
                    msg = (
                        f"Gemini authentication failed ({response.status_code}). "
                        f"Check your API key. Detail: {error_detail}"
                    )
                    raise ProviderAuthError(msg)

                if response.status_code == 429:
                    last_error = ProviderRateLimitError(
                        "Gemini rate limit exceeded. Retrying…"
                    )
                    logger.warning(
                        "Rate limited (429), backing off %.1fs…", backoff
                    )
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                if response.status_code >= 500:
                    last_error = ProviderError(
                        f"Gemini server error ({response.status_code}). Retrying…"
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
                error_detail = self._extract_error_message(response)
                msg = (
                    f"Gemini API returned {response.status_code}: {error_detail}"
                )
                raise ProviderError(msg)

            except httpx.TimeoutException as exc:
                last_error = ProviderNetworkError(
                    f"Gemini request timed out after {self._timeout}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})."
                )
                logger.warning(str(last_error))
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise ProviderNetworkError(str(last_error)) from exc

            except httpx.HTTPError as exc:
                msg = f"Network error communicating with Gemini: {exc}"
                raise ProviderNetworkError(msg) from exc

        # Exhausted retries
        raise last_error or ProviderError("Failed after multiple retries.")

    # ------------------------------------------------------------------
    # Payload construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_payload(messages: list[Message]) -> dict[str, Any]:
        """Convert our Message list to the Gemini API payload format.

        Gemini separates system instructions from conversation content:

        - ``system_instruction`` → extracted from messages with role "system"
        - ``contents`` → user and assistant messages mapped to "user" / "model"
        """
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                # Gemini uses "model" instead of "assistant"
                role = "model" if msg.role == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}],
                })

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        if system_parts:
            payload["system_instruction"] = {
                "parts": [{"text": "\n\n".join(system_parts)}],
            }

        return payload

    # ------------------------------------------------------------------
    # Response extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_content(response_json: dict[str, Any]) -> str:
        """Extract the generated text from the Gemini API response.

        The response structure is:
        ``{ "candidates": [{ "content": { "parts": [{ "text": "..." }] } }] }``
        """
        try:
            candidates = response_json["candidates"]
            parts = candidates[0]["content"]["parts"]
            # Concatenate all text parts
            texts = [part["text"] for part in parts if "text" in part]
            return "\n".join(texts)
        except (KeyError, IndexError, TypeError) as exc:
            msg = f"Unexpected Gemini response format: {response_json}"
            raise ProviderError(msg) from exc

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Best-effort extraction of the error message from a Gemini error."""
        try:
            body = response.json()
            error = body.get("error", {})
            return error.get("message", response.text[:500])
        except Exception:
            return response.text[:500]
