"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Message:
    """A single message in the LLM conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


class LLMProvider(ABC):
    """Abstract interface that all LLM providers must implement.

    To add a new provider:

    1. Create a new module in ``nopush/providers/`` (e.g. ``my_provider.py``).
    2. Subclass :class:`LLMProvider` and implement :meth:`complete`.
    3. Register it in :mod:`nopush.providers.registry`.
    """

    @abstractmethod
    def complete(self, messages: list[Message]) -> str:
        """Send messages to the LLM and return the assistant's response.

        Parameters
        ----------
        messages:
            Ordered list of conversation messages (system, user, etc.).

        Returns
        -------
        str
            The model's response text.

        Raises
        ------
        ProviderAuthError
            If the API key is invalid or missing.
        ProviderRateLimitError
            If the rate limit is exceeded.
        ProviderError
            For any other provider-level failure.
        """
        ...


# ---------------------------------------------------------------------------
# Provider exceptions
# ---------------------------------------------------------------------------


class ProviderError(Exception):
    """Base exception for provider-level errors."""


class ProviderAuthError(ProviderError):
    """Raised when authentication fails (invalid or missing API key)."""


class ProviderRateLimitError(ProviderError):
    """Raised when the API rate limit is exceeded."""


class ProviderNetworkError(ProviderError):
    """Raised when a network-level error occurs (timeout, DNS, connection)."""
