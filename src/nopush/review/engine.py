"""Review engine — orchestrates the full review pipeline."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from nopush.review.models import ReviewComment, ReviewResult, Severity

if TYPE_CHECKING:
    from nopush.config.schema import NoPushConfig
    from nopush.git.models import FileDiff
    from nopush.providers.base import LLMProvider


class ReviewEngine:
    """Orchestrates: diff → prompt → LLM → parse → result.

    This is the central coordinator of NoPush. It does **not** contain
    business logic itself — it delegates to the git parser, prompt builder,
    LLM provider, and response parser.
    """

    def __init__(self, provider: "LLMProvider", config: "NoPushConfig") -> None:
        self._provider = provider
        self._config = config

    def review(self, file_diffs: list["FileDiff"]) -> ReviewResult:
        """Run a full review on the given file diffs.

        Parameters
        ----------
        file_diffs:
            Parsed file diffs to review.

        Returns
        -------
        ReviewResult
            Structured review result with comments.
        """
        from nopush.prompts.builder import PromptBuilder

        if not file_diffs:
            return ReviewResult(
                files_reviewed=0,
                model=self._config.model,
                provider=self._config.provider,
            )

        builder = PromptBuilder(
            review_depth=self._config.review_depth,
        )

        message_chunks = builder.build(file_diffs)
        all_comments: list[ReviewComment] = []

        for messages in message_chunks:
            raw_response = self._provider.complete(messages)
            comments = self._parse_response(raw_response)
            all_comments.extend(comments)

        # Validate that referenced files exist in the diff
        valid_paths = {fd.path for fd in file_diffs}
        validated_comments = [
            c for c in all_comments if c.file_path in valid_paths
        ]

        return ReviewResult(
            comments=validated_comments,
            files_reviewed=len(file_diffs),
            model=self._config.model,
            provider=self._config.provider,
        )

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw: str) -> list[ReviewComment]:
        """Parse the LLM's JSON response into ReviewComment objects.

        Handles common LLM quirks:
        - Markdown code fences wrapping the JSON
        - Trailing commas
        - Single-object responses (not wrapped in an array)
        """
        cleaned = ReviewEngine._clean_json(raw)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Last resort: try to extract JSON array from the text
            match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    return []
            else:
                return []

        # Normalise to a list
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return []

        comments: list[ReviewComment] = []
        for item in data:
            try:
                comment = ReviewComment(**item)
                comments.append(comment)
            except (ValueError, TypeError):
                # Skip malformed entries rather than failing entirely
                continue

        return comments

    @staticmethod
    def _clean_json(raw: str) -> str:
        """Strip markdown fences and trailing commas from raw LLM output."""
        text = raw.strip()

        # Remove ```json ... ``` or ``` ... ``` wrappers
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

        # Remove trailing commas before ] or }
        text = re.sub(r",\s*([}\]])", r"\1", text)

        return text.strip()
