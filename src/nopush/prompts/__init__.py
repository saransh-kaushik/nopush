"""Prompt construction for LLM code reviews.

Public API
----------
- :class:`PromptBuilder` — assembles message lists from diffs and config.
- Templates: :data:`SYSTEM_PROMPT`, :data:`DEPTH_PROMPTS`, etc.
"""

from nopush.prompts.builder import PromptBuilder
from nopush.prompts.templates import (
    DEPTH_PROMPTS,
    FILE_DIFF_TEMPLATE,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)

__all__ = [
    "DEPTH_PROMPTS",
    "FILE_DIFF_TEMPLATE",
    "SYSTEM_PROMPT",
    "USER_PROMPT_TEMPLATE",
    "PromptBuilder",
]
