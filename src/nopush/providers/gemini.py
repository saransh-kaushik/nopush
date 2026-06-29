"""Google Gemini provider — stub for Phase 1."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nopush.providers.base import LLMProvider, Message, ProviderError

if TYPE_CHECKING:
    from nopush.config.schema import NoPushConfig


class GeminiProvider(LLMProvider):
    """Google Gemini provider.

    .. note::
        This is a stub. Full implementation is planned for a future phase.
    """

    def __init__(self, config: "NoPushConfig") -> None:
        self._config = config

    def complete(self, messages: list[Message]) -> str:
        """Not yet implemented."""
        raise ProviderError(
            "Gemini provider is not yet implemented. "
            "Please use 'openai' for now, or contribute an implementation!"
        )
