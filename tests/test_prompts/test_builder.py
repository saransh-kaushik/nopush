"""Tests for the PromptBuilder."""

from __future__ import annotations

from nopush.git.models import FileDiff
from nopush.prompts.builder import PromptBuilder


class TestPromptBuilder:
    """Tests for the prompt builder."""

    def test_empty_diffs(self) -> None:
        """An empty diff list should produce no messages."""
        builder = PromptBuilder()
        result = builder.build([])
        assert result == []

    def test_single_file_produces_one_chunk(self, sample_file_diff: FileDiff) -> None:
        """A single file diff should produce exactly one message chunk."""
        builder = PromptBuilder()
        chunks = builder.build([sample_file_diff])
        assert len(chunks) == 1
        messages = chunks[0]
        assert len(messages) == 2  # system + user
        assert messages[0].role == "system"
        assert messages[1].role == "user"

    def test_file_path_in_prompt(self, sample_file_diff: FileDiff) -> None:
        """The user prompt should contain the file path."""
        builder = PromptBuilder()
        chunks = builder.build([sample_file_diff])
        user_content = chunks[0][1].content
        assert "app/utils.py" in user_content

    def test_depth_in_system_prompt(self, sample_file_diff: FileDiff) -> None:
        """The system prompt should reflect the configured review depth."""
        builder = PromptBuilder(review_depth="thorough")
        chunks = builder.build([sample_file_diff])
        system_content = chunks[0][0].content
        assert "comprehensive" in system_content.lower()

    def test_minimal_depth(self, sample_file_diff: FileDiff) -> None:
        """Minimal depth should focus on critical issues only."""
        builder = PromptBuilder(review_depth="minimal")
        chunks = builder.build([sample_file_diff])
        system_content = chunks[0][0].content
        assert "critical" in system_content.lower()
