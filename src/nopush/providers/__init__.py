"""LLM provider abstraction layer.

Public API
----------
- :class:`LLMProvider` — abstract base class.
- :class:`Message` — conversation message dataclass.
- :func:`get_provider` — instantiate a provider from config.
- :func:`list_providers` — list registered provider names.
- Exceptions: :class:`ProviderError`, :class:`ProviderAuthError`,
  :class:`ProviderRateLimitError`, :class:`ProviderNetworkError`.
"""

from nopush.providers.base import (
    LLMProvider,
    Message,
    ProviderAuthError,
    ProviderError,
    ProviderNetworkError,
    ProviderRateLimitError,
)
from nopush.providers.registry import get_provider, list_providers

__all__ = [
    "LLMProvider",
    "Message",
    "ProviderAuthError",
    "ProviderError",
    "ProviderNetworkError",
    "ProviderRateLimitError",
    "get_provider",
    "list_providers",
]
