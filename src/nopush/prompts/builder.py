"""Assemble LLM messages from diffs and configuration.

The :class:`PromptBuilder` converts a list of :class:`~nopush.git.models.FileDiff`
objects into one or more message lists that can be sent directly to an LLM
provider via its ``complete()`` method.

Large diffs are automatically chunked to stay within the token budget.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nopush.prompts.templates import (
    DEPTH_PROMPTS,
    FILE_DIFF_TEMPLATE,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from nopush.providers.base import Message

if TYPE_CHECKING:
    from nopush.git.models import FileDiff

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rough token estimation (4 chars ≈ 1 token)
# ---------------------------------------------------------------------------

_CHARS_PER_TOKEN = 4
_DEFAULT_MAX_TOKENS = 120_000  # Conservative limit for most models


class PromptBuilder:
    """Builds the message list for an LLM code review request.

    Parameters
    ----------
    review_depth:
        One of ``minimal``, ``standard``, or ``thorough``.
    max_input_tokens:
        Approximate maximum input tokens. Diffs exceeding this are chunked
        into multiple prompt batches.
    """

    def __init__(
        self,
        review_depth: str = "standard",
        max_input_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.review_depth = review_depth
        self.max_input_tokens = max_input_tokens

    def build(self, file_diffs: list[FileDiff]) -> list[list[Message]]:
        """Build one or more message lists from a set of file diffs.

        Parameters
        ----------
        file_diffs:
            Parsed diffs to include in the prompt.

        Returns
        -------
        list[list[Message]]
            Each inner list is a self-contained prompt (system + user message)
            that fits within the token budget.  Usually a single-element list.
        """
        if not file_diffs:
            return []

        # Skip binary files — nothing meaningful to review
        reviewable = [fd for fd in file_diffs if not fd.is_binary]
        if not reviewable:
            logger.info("All files are binary — nothing to review.")
            return []

        system_message = self._build_system_message()
        diff_blocks = [self._format_file_diff(fd) for fd in reviewable]

        # Chunk diff blocks to fit within the token budget
        chunks = self._chunk_blocks(diff_blocks, reviewable, system_message)

        logger.info(
            "Built %d prompt chunk(s) for %d file(s).",
            len(chunks),
            len(reviewable),
        )
        return chunks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_system_message(self) -> Message:
        """Construct the system message with depth modifier."""
        depth_instruction = DEPTH_PROMPTS.get(self.review_depth, DEPTH_PROMPTS["standard"])
        content = f"{SYSTEM_PROMPT}\n\n## Review Depth\n\n{depth_instruction}"
        return Message(role="system", content=content)

    @staticmethod
    def _format_file_diff(file_diff: FileDiff) -> str:
        """Format a single FileDiff into a prompt-ready string."""
        # Reconstruct the raw diff lines from hunks
        diff_lines: list[str] = []
        for hunk in file_diff.hunks:
            diff_lines.append(
                f"@@ -{hunk.old_start},{hunk.old_count} "
                f"+{hunk.new_start},{hunk.new_count} @@ {hunk.header}"
            )
            for line in hunk.lines:
                if line.change_type.value == "added":
                    diff_lines.append(f"+{line.content}")
                elif line.change_type.value == "removed":
                    diff_lines.append(f"-{line.content}")
                else:
                    diff_lines.append(f" {line.content}")

        return FILE_DIFF_TEMPLATE.format(
            file_path=file_diff.path,
            language=file_diff.language or "unknown",
            status=file_diff.status.value,
            additions=file_diff.total_additions,
            deletions=file_diff.total_deletions,
            diff_content="\n".join(diff_lines),
        )

    def _chunk_blocks(
        self,
        diff_blocks: list[str],
        file_diffs: list[FileDiff],
        system_message: Message,
    ) -> list[list[Message]]:
        """Split diff blocks into chunks that fit the token budget.

        Each chunk is a complete prompt with a system message and a user
        message containing one or more file diffs.
        """
        system_tokens = self._estimate_tokens(system_message.content)
        budget = self.max_input_tokens - system_tokens

        chunks: list[list[Message]] = []
        current_blocks: list[str] = []
        current_diffs: list[FileDiff] = []
        current_tokens = 0

        for block, fd in zip(diff_blocks, file_diffs, strict=True):
            block_tokens = self._estimate_tokens(block)

            if current_tokens + block_tokens > budget and current_blocks:
                # Flush current chunk
                user_msg = self._assemble_user_message(current_blocks, current_diffs)
                chunks.append([system_message, user_msg])
                current_blocks = []
                current_diffs = []
                current_tokens = 0

            current_blocks.append(block)
            current_diffs.append(fd)
            current_tokens += block_tokens

        # Flush remaining
        if current_blocks:
            user_msg = self._assemble_user_message(current_blocks, current_diffs)
            chunks.append([system_message, user_msg])

        return chunks

    @staticmethod
    def _assemble_user_message(blocks: list[str], file_diffs: list[FileDiff]) -> Message:
        """Create the user message from accumulated diff blocks."""
        total_additions = sum(fd.total_additions for fd in file_diffs)
        total_deletions = sum(fd.total_deletions for fd in file_diffs)

        content = USER_PROMPT_TEMPLATE.format(
            file_diffs="\n".join(blocks),
            file_count=len(blocks),
            total_additions=total_additions,
            total_deletions=total_deletions,
        )
        return Message(role="user", content=content)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate: 1 token ≈ 4 characters."""
        return len(text) // _CHARS_PER_TOKEN
