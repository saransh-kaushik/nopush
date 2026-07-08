"""Provider registry — maps provider names to their implementations.

Providers are lazily imported to avoid pulling in ``httpx`` at module load
time unless a provider is actually instantiated.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from nopush.providers.base import LLMProvider, ProviderError

if TYPE_CHECKING:
    from nopush.config.schema import NoPushConfig

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

# Maps lowercase provider names to their fully-qualified class paths.
_PROVIDER_MAP: dict[str, str] = {
    "openai": "nopush.providers.openai.OpenAIProvider",
    "gemini": "nopush.providers.gemini.GeminiProvider",
    "anthropic": "nopush.providers.anthropic.AnthropicProvider",
}


def get_provider(config: NoPushConfig) -> LLMProvider:
    """Instantiate and return the configured LLM provider.

    Parameters
    ----------
    config:
        Resolved NoPush configuration containing provider name, API key, etc.

    Returns
    -------
    LLMProvider
        An instance of the requested provider.

    Raises
    ------
    ProviderError
        If the provider name is not recognised.
    """
    name = config.provider.lower()
    class_path = _PROVIDER_MAP.get(name)

    if class_path is None:
        available = ", ".join(sorted(_PROVIDER_MAP))
        msg = f"Unknown provider '{name}'. Available providers: {available}"
        raise ProviderError(msg)

    # Lazy import the class
    module_path, class_name = class_path.rsplit(".", maxsplit=1)
    module = importlib.import_module(module_path)
    provider_class: type[LLMProvider] = getattr(module, class_name)

    return provider_class(config)  # type: ignore[call-arg]


def list_providers() -> list[str]:
    """Return a sorted list of registered provider names."""
    return sorted(_PROVIDER_MAP)
